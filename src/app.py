"""
Application Bootstrap

This module provides the main application class that ties together
all services, plugins, and configuration.
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from src.container import ApplicationContext
from src.models.book import Book
from src.models.character import CharacterAnalysis
from src.models.transformation import TransformType
from src.parsers.book_converter import BookConverter
from src.plugins.base import PluginManager


def _cast_summary(characters, transform_type: TransformType) -> dict:
    """Who this transform actually regenders, and into what.

    A run reported the size of the cast it analysed, which is a fact about
    the book rather than about the transformation. The number that says what
    happened is how many of those characters changed, and in which direction.
    """
    from src.services.name_engine import target_gender

    counts: dict[tuple, int] = {}
    for char in characters:
        target = target_gender(char.gender, transform_type)
        if target is None:
            continue
        counts[(char.gender.value, target.value)] = (
            counts.get((char.gender.value, target.value), 0) + 1
        )
    return {
        "total": len(characters),
        "regendered": sum(counts.values()),
        "changes": [
            {"from": source, "to": dest, "count": n}
            for (source, dest), n in sorted(counts.items(), key=lambda kv: -kv[1])
        ],
    }


class Application:
    """
    Main application class for regender-xyz.

    This class:
    - Manages application lifecycle
    - Configures services and plugins
    - Provides high-level API for book processing
    - Handles configuration loading
    """

    def __init__(
        self, config_path: Optional[str] = None, context: Optional[ApplicationContext] = None
    ):
        """
        Initialize the application.

        Args:
            config_path: Optional path to configuration file
            context: Optional pre-configured ApplicationContext (useful for testing)
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        # Use provided context or create new one
        if context:
            self.context = context
            self._owns_context = False
        else:
            self.context = ApplicationContext(config_path=config_path, environment="application")
            self._owns_context = True

        self.plugin_manager = PluginManager()

        # Load configuration
        if config_path:
            self.config = self._load_config(config_path)
        else:
            self.config = self._get_default_config()

        # Initialize components
        self._initialize()

    def _load_config(self, path: str) -> dict[str, Any]:
        """
        Load application configuration from file.

        Args:
            path: Path to configuration file

        Returns:
            Configuration dictionary
        """
        config_path = Path(path)

        if not config_path.exists():
            self.logger.warning(f"Config file not found: {config_path}")
            return self._get_default_config()

        try:
            with open(config_path) as f:
                config = json.load(f)
            self.logger.info(f"Loaded configuration from {config_path}")
            return config
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        """
        Get default application configuration.

        Returns:
            Default configuration dictionary
        """
        return {
            "providers": [
                {"type": "unified", "module": "src.providers.unified_provider", "config": {}}
            ],
            "services": {
                "parser": {
                    "class": "src.services.parser_service.ParserService",
                    "config": {"cache_enabled": True},
                },
                "character": {
                    "class": "src.services.character_service.CharacterService",
                    "config": {"cache_enabled": True, "max_concurrent": 5},
                    "dependencies": {"provider": "llm_provider"},
                },
                "transform": {
                    "class": "src.services.transform_service.TransformService",
                    "config": {"cache_enabled": True, "max_concurrent": 5},
                    "dependencies": {"provider": "llm_provider", "character_service": "character"},
                },
            },
        }

    def _initialize(self):
        """Initialize application components."""
        self.logger.info("Initializing application...")

        # Initialize context if we own it
        if self._owns_context:
            self.context.initialize()

        # Load provider plugins
        self._load_providers()

        # Register services
        self._register_services()

        self.logger.info("Application initialized successfully")

    def _load_providers(self):
        """Load and initialize provider plugins."""
        import os
        from pathlib import Path

        # Auto-discover provider plugins in src/providers/
        providers_dir = Path(__file__).parent / "providers"

        # List of provider files to try loading (excluding base classes)
        provider_modules = {
            "openai": "src.providers.openai",
            "anthropic": "src.providers.anthropic",
            "ollama": "src.providers.ollama",
        }

        # Load all available provider plugins
        for name, module_path in provider_modules.items():
            try:
                self.plugin_manager.load_plugin(module_path)
                self.logger.info(f"Loaded provider plugin: {name}")
            except Exception as e:
                self.logger.debug(f"Could not load {name} provider: {e}")

        # Determine which provider to use
        default_provider = os.getenv("DEFAULT_PROVIDER", "openai")

        # Get and initialize the selected provider
        provider = self.plugin_manager.get(default_provider)
        if not provider:
            # Fallback to OpenAI if specific one not found
            self.logger.warning(f"Provider '{default_provider}' not found, trying openai")
            provider = self.plugin_manager.get("openai")

        if provider:
            try:
                # Initialize provider (it will read API keys from environment)
                provider.initialize({})

                # Register as service for dependency injection
                self.context.register_instance("llm_provider", provider)
                self.logger.info(f"Registered provider: {provider.name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize provider: {e}")
        else:
            self.logger.error("No LLM provider could be loaded")

    def _register_services(self):
        """Register services with the container."""
        for service_name, service_config in self.config.get("services", {}).items():
            try:
                class_path = service_config.get("class")
                if not class_path:
                    continue

                # Import service class
                parts = class_path.split(".")
                module_path = ".".join(parts[:-1])
                class_name = parts[-1]

                import importlib

                module = importlib.import_module(module_path)
                service_class = getattr(module, class_name)

                # Register with container
                self.context.register_service(
                    name=service_name,
                    service_class=service_class,
                    config=service_config.get("config"),
                    dependencies=service_config.get("dependencies"),
                )

            except Exception as e:
                self.logger.error(f"Failed to register service {service_name}: {e}")

    def _run_quality_control(
        self,
        book,
        transformation,
        transform_type,
        output_path,
        partial,
        name_map=None,
        characters=None,
    ) -> Optional[dict]:
        """Check the transformed book against its source, and say what it found.

        Reports everything, blocks on nothing but structural findings. Those
        mean the book is broken -- a chapter or paragraph count that no longer
        matches the source -- rather than merely arguable. needs_review is
        expected in normal work and must never gate: the nonbinary edition
        legitimately produces dozens.

        A PASS here means no gendered word survived unchanged, the structure
        holds, and nothing looks like a repetition loop. It does not mean the
        transformation is right, and the summary says so.
        """
        try:
            from src.services.qc_service import STRUCTURAL, QCService

            source = book.to_dict() if hasattr(book, "to_dict") else book
            if not hasattr(transformation, "get_transformed_book"):
                return None
            transformed = transformation.get_transformed_book().to_dict()

            # QCService wants the enum; process_book carries the string. Passing
            # the string raises inside the try below and reports as "QC did not
            # run", which is exactly the kind of quiet skip this gate exists to
            # stop happening.
            key = (
                transform_type
                if isinstance(transform_type, TransformType)
                else TransformType(transform_type)
            )
            # Without the map QC cannot see renaming at all: it has no idea
            # what any character was supposed to be called, so a book naming
            # its protagonist two different ways scored 99.7% and passed.
            cast = [c.name for c in getattr(characters, "characters", [])]
            report = QCService(key, name_map=name_map, cast=cast).check_book(source, transformed)
            summary = report.to_dict()

            path = Path(output_path).with_name(Path(output_path).stem + "_qc.json")
            path.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

            totals = summary.get("totals", {})
            structural = totals.get(STRUCTURAL, 0)
            self.logger.info(
                f"QC: {structural} structural, "
                f"{totals.get('auto_fixable', 0)} auto-fixable, "
                f"{totals.get('needs_review', 0)} needing review -> {path.name}"
            )
            if structural:
                self.logger.error(
                    f"QC found {structural} structural problem(s): the book does not match "
                    "its source in shape. Do not print this until they are understood."
                )
            if partial:
                self.logger.error(
                    "QC cannot vouch for chapters that kept their original text: "
                    + ", ".join(str(n) for n in partial)
                )
            # How many gendered words actually changed, measured against the
            # source. QC already counts this per chapter to compute coverage,
            # and then only the coverage fraction survived -- which hides the
            # scale of what a run did behind a percentage.
            chapters = summary.get("chapters", [])
            # Both kinds say the same thing to a reader -- a character is being
            # called something the engine never chose -- and they are found two
            # different ways, so they are counted together.
            naming = [
                f
                for f in summary.get("book_findings", [])
                if f.get("kind") in ("invented_name", "rename_lost")
            ]
            if naming:
                self.logger.error(
                    f"{len(naming)} character(s) are called a name the map never chose: "
                    + "; ".join(f["detail"] for f in naming[:5])
                )
            return {
                "naming_problems": len(naming),
                "structural": structural,
                "auto_fixable": totals.get("auto_fixable", 0),
                "needs_review": totals.get("needs_review", 0),
                "gendered_words": sum(c.get("gendered_words", 0) for c in chapters),
                "transformed_words": sum(c.get("transformed_words", 0) for c in chapters),
                # The findings a person can actually settle, carried up so the
                # interface can put them in front of one. Reporting a count and
                # then offering no way to act on it leaves the last few percent
                # to whoever happens to read the book.
                "reviewable": [
                    f
                    for c in chapters
                    for f in c.get("findings", [])
                    if f.get("severity") == "needs_review" and f.get("term")
                ],
                "report": str(path),
                "blocked": bool(structural),
            }
        except Exception as error:  # QC must never be the reason a run is lost
            self.logger.warning(f"Quality control did not run: {error}")
            return None

    def get_service(self, name: str):
        """
        Get a service from the container.

        Args:
            name: Service name

        Returns:
            Service instance
        """
        return self.context.get_service(name)

    async def _get_or_analyze_characters(
        self, book: Book, output_dir: Optional[Path] = None
    ) -> CharacterAnalysis:
        """
        The cast for this run, analysed fresh unless this exact run already has one.

        It used to search every previous run folder for the book and load the
        first characters.json it found. That looked like thrift and behaved like
        a cache with no key: the cast was pinned to whichever folder sorted last,
        so a run could show the reader eighty-two characters, take their renames,
        and then transform the book against a ninety-entry cast from three days
        earlier. Whatever the analysis had learned since -- merged duplicates,
        corrected genders -- was silently discarded.

        A run is now self-contained. The only file consulted is the one in this
        run's own output folder, which exists just when the same output path is
        being rebuilt; a sibling run's cast is never borrowed.

        Args:
            book: Parsed book object
            output_dir: This run's output folder, if it has one

        Returns:
            Character analysis
        """
        if output_dir:
            char_file = Path(output_dir) / "characters.json"
            if char_file.exists():
                self.logger.info(f"Reusing this run's own character analysis: {char_file}")
                try:
                    with open(char_file) as f:
                        return CharacterAnalysis.from_dict(json.load(f))
                except Exception as e:
                    self.logger.warning(f"Failed to load character file: {e}")

        self.logger.info("Analyzing characters for this run...")
        character_service = self.get_service("character")
        return await character_service.process(book)

    async def process_book(
        self,
        file_path: str,
        transform_type: str,
        output_path: Optional[str] = None,
        selected_characters: Optional[list[str]] = None,
        name_map: Optional[dict[str, str]] = None,
        custom_title: Optional[str] = None,
        on_chapter_complete: Optional[Any] = None,
        characters: Optional[CharacterAnalysis] = None,
    ) -> dict[str, Any]:
        """
        Process a book through the full pipeline.

        Args:
            file_path: Path to input file
            transform_type: Type of transformation
            output_path: Optional output path
            quality_control: Whether to apply quality control
            selected_characters: Optional list of character names to transform
            name_map: Optional mapping of original character names to replacement names
            characters: The cast this run already analysed. Passing it is how a
                caller that has shown the reader a cast guarantees the book is
                transformed against that same cast and no other.

        Returns:
            Processing results
        """
        self.logger.info(f"Processing book: {file_path}")

        try:
            # Parse the book
            parser = self.get_service("parser")
            book = await parser.process(file_path)
            if custom_title:
                book.title = custom_title
            self.logger.info(f"Parsed book: {book.title}")

            # Determine output directory early if we have an output path
            output_dir = None
            if output_path:
                output_dir = Path(output_path).parent
                output_dir.mkdir(parents=True, exist_ok=True)

            # The cast. A caller that already analysed one -- the interface does,
            # and shows the reader the count -- hands it over; otherwise this run
            # analyses its own.
            if characters is None:
                characters = await self._get_or_analyze_characters(book, output_dir)
            else:
                self.logger.info("Using the cast supplied by the caller")
            self.logger.info(f"Using {len(characters.characters)} characters")

            # Decide every character rename ONCE, before any chapter is
            # transformed. Renames used to be improvised by the LLM chunk by
            # chunk, so one character could end up with several targets in the
            # same book (Elizabeth -> Elliot in one chapter, Edward in another).
            # User-supplied entries win; the engine fills in the rest.
            from src.services.name_engine import NameEngine

            engine = NameEngine(provider=self.get_service("transform").provider, logger=self.logger)
            name_map, name_report = await engine.build_name_map(
                characters,
                TransformType(transform_type),
                base_map=name_map,
                selected_characters=selected_characters,
            )
            self.logger.info(
                f"Name map: {name_report['entries']} entries "
                f"({name_report['accepted']} characters renamed)"
            )

            # Save character analysis immediately if we have output path and it's not already saved
            if output_dir:
                # Written every time, not just when absent: the file beside an
                # edition is the record of what produced it, and a stale one is
                # worse than none.
                char_file = output_dir / "characters.json"
                with open(char_file, "w") as f:
                    json.dump(characters.to_dict(), f, indent=2, default=str)
                self.logger.info(f"Saved character analysis to {char_file}")

                # Persist the name map alongside the output. Without it there is
                # no way to check afterwards that every rename actually landed.
                if name_map:
                    map_file = output_dir / "name_map.json"
                    with open(map_file, "w") as f:
                        json.dump(name_map, f, indent=2)
                    self.logger.info(f"Saved name map to {map_file}")
                with open(output_dir / "name_report.json", "w") as f:
                    json.dump(name_report, f, indent=2)

            # Transform the book
            transformer = self.get_service("transform")

            # A surname that is also a gendered noun gets swapped like the noun:
            # "Miss King" became "Miss Queen" and Mary King, a real character,
            # was renamed Mary Queen in the printed edition. The cast is the only
            # thing that knows the difference, so hand it over before starting.
            # Capitalised forms only — the monarch "king" still swaps.
            surnames = set()
            for char in characters.characters:
                for form in [char.name, *char.aliases]:
                    surnames.update(
                        token for token in re.split(r"\s+", form.strip()) if token[:1].isupper()
                    )
            transformer.protect_names(surnames, TransformType(transform_type))

            # Marital status is not a fixed property. Darcy is unmarried for
            # sixty chapters and married in the sixty-first; Collins marries in
            # twenty-eight. A swap has to know, because English women's titles
            # encode it and men's do not, and the answer changes mid-book --
            # sometimes mid-chapter, so the marker is the paragraph.
            if TransformType(transform_type) == TransformType.GENDER_SWAP:
                from src.services.character_state import (
                    detect_marital_changes,
                    initial_marital_state,
                    marital_title_maps,
                )

                book_dict = book.to_dict() if hasattr(book, "to_dict") else book
                changes = detect_marital_changes(book_dict, characters.characters)
                opening = initial_marital_state(characters.characters)
                title_base, title_timeline = marital_title_maps(
                    characters.characters, changes, opening
                )
                # The engine's own entries win: a rename decided for a character
                # is more specific than a title derived from their status.
                name_map = {**title_base, **(name_map or {})}
                transformer.set_title_timeline(title_timeline)
                name_report["state_changes"] = [c.to_dict() for c in changes]
                if changes:
                    self.logger.info(
                        "Marital status changes: "
                        + ", ".join(
                            f"{c.character} at ch{c.chapter} p{c.paragraph}" for c in changes
                        )
                    )
            protected = getattr(transformer, "_protected_names", None)
            if protected:
                self.logger.info(f"Protecting cast surnames from the term map: {protected.pattern}")

            # Log selected characters if specified
            if selected_characters:
                self.logger.info(f"Selective transformation for: {', '.join(selected_characters)}")

            # Record what the safety net changes, so its decisions can be read
            # afterwards. The change log keeps whole-paragraph diffs, which
            # buried "pages -> handmaids" inside a paragraph where nobody saw it.
            transformer.start_substitution_log()

            transformation = await transformer.transform_book(
                book,
                TransformType(transform_type),
                characters,
                selected_characters,
                name_map=name_map,
                on_chapter_complete=on_chapter_complete,
            )
            self.logger.info(f"Applied {len(transformation.changes)} transformations")

            # A chapter that raised kept its source text so the book stays whole
            # and the counts line up. That is a partial book, and it must not
            # read as a complete one.
            qc_summary = None
            partial = list(getattr(transformer, "failed_chapters", []) or [])
            if partial:
                self.logger.error(
                    f"{len(partial)} chapter(s) kept their original, untransformed text: "
                    + ", ".join(str(n) for n in partial)
                )

            # What the safety net decided, and which of those decisions want a
            # second look. A capitalised word that does not open a sentence is
            # capitalised because it is a name, and names have no business
            # being swapped -- that is how Mary King became Mary Queen.
            substitutions = getattr(transformer, "_substitution_log", None) or []
            flagged = transformer.suspicious_substitutions(substitutions)
            if output_dir and substitutions:
                with open(output_dir / "substitutions.json", "w") as f:
                    json.dump({"total": len(substitutions), "entries": substitutions}, f, indent=1)
                with open(output_dir / "substitutions_to_review.json", "w") as f:
                    json.dump({"pairs": flagged}, f, indent=1)
            if flagged:
                preview = ", ".join(
                    f"{p['before']}->{p['after']} x{p['count']}" for p in flagged[:8]
                )
                self.logger.info(
                    f"{len(substitutions)} substitutions recorded; "
                    f"{len(flagged)} distinct pairs to review: {preview}"
                )

            # Save output if requested
            if output_path:
                # Save JSON transformation immediately
                await self._save_output(transformation, output_path)
                self.logger.info(f"Saved transformation JSON to {output_path}")

                # Quality control. It used to be skipped entirely, so the only
                # QC these books ever had was somebody running the script by
                # hand -- which is how a book containing "Mary Queen" and "read
                # three handmaids" was called clean.
                #
                # It reports everything and blocks on nothing except structural
                # findings. Those are unambiguous corruption: a chapter or
                # paragraph count that no longer matches the source means the
                # book is broken, not merely arguable. needs_review must never
                # block -- the nonbinary book legitimately produces dozens, and
                # a gate that cries wolf gets switched off.
                qc_summary = self._run_quality_control(
                    book,
                    transformation,
                    transform_type,
                    output_path,
                    partial,
                    getattr(transformer, "effective_name_map", None) or name_map,
                    characters,
                )

                # Export as text file (this could fail, but JSON is already saved)
                output_dir = Path(output_path).parent
                text_output = output_dir / f"{TransformType(transform_type).value}.txt"
                try:
                    await self._save_output(transformation, str(text_output))
                    self.logger.info(f"Exported text to {text_output}")
                except Exception as e:
                    self.logger.warning(f"Failed to export text: {e}, but JSON is saved")

            return {
                "success": True,
                "book_title": book.title,
                "characters": len(characters.characters),
                "cast": _cast_summary(characters.characters, TransformType(transform_type)),
                "changes": len(transformation.changes),
                "output_path": output_path,
                "untransformed_chapters": partial,
                "quality_control": qc_summary,
                "substitutions_to_review": len(flagged),
            }

        except Exception as e:
            self.logger.error(f"Failed to process book: {e}")
            return {"success": False, "error": str(e)}

    async def _save_output(self, transformation, output_path: str):
        """Save transformation output."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get transformed book
        transformed_book = transformation.get_transformed_book()

        # Save based on extension
        if output_path.suffix == ".json":
            # Save as JSON
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(transformed_book.to_dict(), f, indent=2, ensure_ascii=False)
        else:
            # Save as text using TextExportService for proper Unicode handling
            from src.services.base import ServiceConfig
            from src.services.text_export_service import TextExportService

            config = ServiceConfig(
                extra_config={
                    "preserve_unicode": False,
                    "normalize_method": "unidecode",  # Use unidecode for clean ASCII
                }
            )

            text_export_service = TextExportService(config)
            text_export_service.logger = self.logger
            text_content = await text_export_service.process(transformed_book)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text_content)

        self.logger.info(f"Saved output to {output_path}")

    async def parse_book(self, file_path: str, output_path: Optional[str] = None) -> dict[str, Any]:
        """
        Parse a book to canonical JSON format without transformation.

        Args:
            file_path: Path to input file
            output_path: Optional output path

        Returns:
            Parsing results
        """
        self.logger.info(f"Parsing book: {file_path}")

        try:
            # Parse the book using the integrated parser
            from src.parsers.parser import IntegratedParser

            parser = IntegratedParser()

            # Read the file
            input_path = Path(file_path)
            with open(input_path, encoding="utf-8", errors="ignore") as f:
                text = f.read()

            # Parse to ParsedBook format
            parsed_book = parser.parse(text)

            # Convert to canonical Book format with sentences
            converter = BookConverter()
            book = converter.convert(parsed_book)
            book.source_file = str(input_path)

            self.logger.info(f"Parsed book: {book.title}")

            # Calculate statistics
            total_paragraphs = sum(len(ch.paragraphs) for ch in book.chapters)
            total_sentences = sum(len(p.sentences) for ch in book.chapters for p in ch.paragraphs)

            # Save output if requested
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Save as JSON
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(book.to_dict(), f, indent=2, ensure_ascii=False)

                self.logger.info(f"Saved canonical JSON to {output_path}")

            return {
                "success": True,
                "book_title": book.title,
                "author": book.author,
                "chapters": len(book.chapters),
                "paragraphs": total_paragraphs,
                "sentences": total_sentences,
                "output_path": str(output_path) if output_path else None,
            }

        except Exception as e:
            self.logger.error(f"Failed to parse book: {e}")
            return {"success": False, "error": str(e)}

    def parse_book_sync(self, file_path: str, output_path: Optional[str] = None) -> dict[str, Any]:
        """
        Synchronous wrapper for book parsing.

        Args:
            file_path: Path to input file
            output_path: Optional output path

        Returns:
            Parsing results
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.parse_book(file_path, output_path))
        finally:
            loop.close()

    async def analyze_characters(
        self, file_path: str, output_path: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Analyze characters in a book and save to separate character file.

        Args:
            file_path: Path to input file (text or JSON)
            output_path: Optional output path for character analysis JSON

        Returns:
            Character analysis results
        """
        self.logger.info(f"Analyzing characters in: {file_path}")

        try:
            input_path = Path(file_path)

            # Load the book (from JSON if available, otherwise parse)
            if input_path.suffix == ".json":
                # Load from JSON
                with open(input_path, encoding="utf-8") as f:
                    book_data = json.load(f)
                from src.models.book import Book

                book = Book.from_dict(book_data)
                self.logger.info(f"Loaded book from JSON: {book.title}")
            else:
                # Parse from text
                parser = self.get_service("parser")
                book = await parser.process(file_path)
                self.logger.info(f"Parsed book: {book.title}")

            # Analyze characters
            character_service = self.get_service("character")
            characters = await character_service.process(book)
            self.logger.info(f"Found {len(characters.characters)} characters")

            # Save output if requested
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Save just the character analysis
                character_data = characters.to_dict()
                character_data["book_metadata"] = {
                    "title": book.title,
                    "author": book.author,
                    "source_file": str(input_path),
                }

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(character_data, f, indent=2, ensure_ascii=False)

                self.logger.info(f"Saved character analysis to {output_path}")

            # Get character statistics
            stats = characters.get_statistics()

            return {
                "success": True,
                "book_title": book.title,
                "total_characters": stats["total"],
                "by_gender": stats["by_gender"],
                "by_importance": stats["by_importance"],
                "main_characters": stats["main_characters"],
                "output_path": str(output_path) if output_path else None,
            }

        except Exception as e:
            self.logger.error(f"Failed to analyze characters: {e}")
            return {"success": False, "error": str(e)}

    def analyze_characters_sync(
        self, file_path: str, output_path: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Synchronous wrapper for character analysis.

        Args:
            file_path: Path to input file
            output_path: Optional output path

        Returns:
            Character analysis results
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.analyze_characters(file_path, output_path))
        finally:
            loop.close()

    def process_book_sync(
        self,
        file_path: str,
        transform_type: str,
        output_path: Optional[str] = None,
        selected_characters: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Synchronous wrapper for book processing.

        Args:
            file_path: Path to input file
            transform_type: Type of transformation
            output_path: Optional output path
            quality_control: Whether to apply quality control

        Returns:
            Processing results
        """
        return asyncio.run(
            self.process_book(file_path, transform_type, output_path, selected_characters)
        )

    def get_metrics(self) -> dict[str, Any]:
        """
        Get application metrics.

        Returns:
            Metrics dictionary
        """
        return {
            "container": self.context.container.get_metrics(),
            "plugins": self.plugin_manager.list_plugins(),
        }

    def shutdown(self):
        """Shutdown the application."""
        self.logger.info("Shutting down application...")

        # Shutdown plugins
        self.plugin_manager.shutdown_all()

        # Shutdown context if we own it
        if self._owns_context:
            self.context.shutdown()

        self.logger.info("Application shutdown complete")
