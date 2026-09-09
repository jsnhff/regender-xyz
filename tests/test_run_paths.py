"""Each run owns a folder, and its artifacts stay together.

A name map describes exactly one transformed book; beside a different one it is
worse than nothing. The CLI wrote to "<book>-<timestamp>" and the TUI to
"<book>" with the timestamp in the filename, so two runs of the same book
overwrote each other's name_map.json and name_report.json while the books sat
side by side looking fine.
"""

from datetime import datetime
from pathlib import Path

import pytest

from src.utils.paths import book_slug, keep_source, run_directory


class TestBookSlug:
    @pytest.mark.parametrize(
        "given,expected",
        [
            ("pg1342-pride-and-prejudice.txt", "pride-and-prejudice"),
            ("pg84_Frankenstein.txt", "frankenstein"),
            ("Pride Prejudice Sample.txt", "pride-prejudice-sample"),
            ("wuthering_heights.txt", "wuthering-heights"),
        ],
    )
    def test_the_gutenberg_id_is_dropped(self, given, expected):
        assert book_slug(given) == expected

    def test_a_nameless_file_still_gets_a_folder(self):
        assert book_slug("---.txt") == "book"


class TestRunDirectory:
    def test_it_is_grouped_under_the_book(self, tmp_path):
        directory = run_directory("pg1342-pride.txt", "gender_swap", root=tmp_path)
        assert directory.parent.name == "pride"
        assert directory.name.startswith("gender_swap_")

    def test_two_transforms_do_not_share_a_folder(self, tmp_path):
        when = datetime(2026, 9, 8, 14, 30)
        swap = run_directory("book.txt", "gender_swap", when=when, root=tmp_path)
        nb = run_directory("book.txt", "nonbinary", when=when, root=tmp_path)
        assert swap != nb

    def test_two_runs_of_one_transform_do_not_share_a_folder(self, tmp_path):
        """The bug: an all_female run replaced the nonbinary run's name map."""
        first = run_directory(
            "book.txt", "nonbinary", when=datetime(2026, 9, 8, 14, 30), root=tmp_path
        )
        second = run_directory(
            "book.txt", "nonbinary", when=datetime(2026, 9, 8, 15, 45), root=tmp_path
        )
        assert first != second

    def test_the_folder_is_created(self, tmp_path):
        assert run_directory("book.txt", "nonbinary", root=tmp_path).is_dir()

    def test_it_can_be_asked_not_to_create(self, tmp_path):
        directory = run_directory("book.txt", "nonbinary", root=tmp_path, create=False)
        assert not directory.exists()


class TestKeepingTheSource:
    def test_the_original_is_copied_in(self, tmp_path):
        source = tmp_path / "book.txt"
        source.write_text("It is a truth universally acknowledged", encoding="utf-8")
        directory = run_directory(source, "gender_swap", root=tmp_path)

        kept = keep_source(source, directory)
        assert kept is not None
        assert kept.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
        assert kept.parent == directory

    def test_it_keeps_the_extension(self, tmp_path):
        source = tmp_path / "book.json"
        source.write_text("{}", encoding="utf-8")
        directory = run_directory(source, "nonbinary", root=tmp_path)
        assert keep_source(source, directory).name == "source.json"

    def test_a_missing_source_is_not_an_error(self, tmp_path):
        directory = run_directory("gone.txt", "nonbinary", root=tmp_path)
        assert keep_source(tmp_path / "gone.txt", directory) is None

    def test_an_existing_copy_is_not_overwritten(self, tmp_path):
        source = tmp_path / "book.txt"
        source.write_text("original", encoding="utf-8")
        directory = run_directory(source, "nonbinary", root=tmp_path)
        keep_source(source, directory)
        (directory / "source.txt").write_text("edited by hand", encoding="utf-8")
        keep_source(source, directory)
        assert (directory / "source.txt").read_text(encoding="utf-8") == "edited by hand"


class TestEverythingLandsTogether:
    def test_the_run_folder_holds_the_whole_set(self, tmp_path):
        """What a finished run should look like on disk."""
        source = tmp_path / "pg1342-pride.txt"
        source.write_text("text", encoding="utf-8")
        directory = run_directory(source, "gender_swap", root=tmp_path)
        keep_source(source, directory)

        # the names the pipeline writes, all derived from the output path
        book = directory / "gender_swap.json"
        for name in [
            "gender_swap.json",
            "gender_swap_qc.json",
            "characters.json",
            "name_map.json",
            "name_report.json",
            "substitutions.json",
            "substitutions_to_review.json",
        ]:
            (directory / name).write_text("{}", encoding="utf-8")

        assert Path(book).parent == directory
        assert (directory / "source.txt").exists()
        assert len(list(directory.iterdir())) == 8
