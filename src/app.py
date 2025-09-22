"""
Application Bootstrap

This module provides the main application class that ties together
all services, plugins, and configuration.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional

from src.container import ApplicationContext
from src.models.book import Book
from src.models.character import CharacterAnalysis
from src.models.transformation import TransformType
from src.parsers.book_converter import BookConverter
from src.plugins.base import PluginManager


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
            "anthropic": "src.providers.anthropic"
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

    def get_service(self, name: str):
        """
        Get a service from the container.

        Args:
            name: Service name

        Returns:
            Service instance
        """
        return self.context.get_service(name)

    async def _get_or_analyze_characters(self, file_path: str, book: Book) -> CharacterAnalysis:
        """
        Get existing character analysis or analyze characters.

        Args:
            file_path: Path to the book file
            book: Parsed book object

        Returns:
            Character analysis
        """
        # Check for existing character analysis file
        input_path = Path(file_path)

        # Determine book name for output folder
        book_name = input_path.stem
        # Remove common prefixes like pg12- or pg43-
        if book_name.startswith("pg") and "-" in book_name:
            book_name = book_name.split("-", 1)[1]
        # Convert to lowercase and replace spaces/underscores with hyphens
        book_folder = book_name.lower().replace("_", "-").replace(" ", "-")

        # Check for most recent character analysis in timestamped folders
        output_base = Path("books/output")
        matching_folders = sorted(output_base.glob(f"{book_folder}-*"))

        for folder in reversed(matching_folders):  # Check newest first
            char_file = folder / "characters.json"
            if char_file.exists():
                self.logger.info(f"Loading existing character analysis from {char_file}")
                try:
                    with open(char_file) as f:
                        char_data = json.load(f)
                    return CharacterAnalysis.from_dict(char_data)
                except Exception as e:
                    self.logger.warning(f"Failed to load character file: {e}")

        # No existing analysis, analyze the book
        self.logger.info("No existing character analysis found, analyzing book...")
        character_service = self.get_service("character")
        characters = await character_service.process(book)

        # Note: Character analysis will be saved by the CLI with a timestamp
        return characters

    async def process_book(
        self,
        file_path: str,
        transform_type: str,
        output_path: Optional[str] = None,
        selected_characters: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Process a book through the full pipeline.

        Args:
            file_path: Path to input file
            transform_type: Type of transformation
            output_path: Optional output path
            quality_control: Whether to apply quality control
            selected_characters: Optional list of character names to transform

        Returns:
            Processing results
        """
        self.logger.info(f"Processing book: {file_path}")

        try:
            # Parse the book
            parser = self.get_service("parser")
            book = await parser.process(file_path)
            self.logger.info(f"Parsed book: {book.title}")

            # Determine output directory early if we have an output path
            output_dir = None
            if output_path:
                output_dir = Path(output_path).parent
                output_dir.mkdir(parents=True, exist_ok=True)

            # Check for existing character analysis or analyze characters
            characters = await self._get_or_analyze_characters(file_path, book)
            self.logger.info(f"Using {len(characters.characters)} characters")

            # Save character analysis immediately if we have output path and it's not already saved
            if output_dir:
                char_file = output_dir / "characters.json"
                if not char_file.exists():
                    with open(char_file, 'w') as f:
                        json.dump(characters.to_dict(), f, indent=2, default=str)
                    self.logger.info(f"Saved character analysis to {char_file}")

            # Transform the book
            transformer = self.get_service("transform")

            # Log selected characters if specified
            if selected_characters:
                self.logger.info(f"Selective transformation for: {', '.join(selected_characters)}")

            transformation = await transformer.transform_book(
                book, TransformType(transform_type), characters, selected_characters
            )
            self.logger.info(f"Applied {len(transformation.changes)} transformations")

            # Quality control removed - transformations are applied directly

            # Save output if requested
            if output_path:
                # Save JSON transformation immediately
                await self._save_output(transformation, output_path)
                self.logger.info(f"Saved transformation JSON to {output_path}")

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
                "changes": len(transformation.changes),
                "output_path": output_path,
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
                    "normalize_method": "unidecode"  # Use unidecode for clean ASCII
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
