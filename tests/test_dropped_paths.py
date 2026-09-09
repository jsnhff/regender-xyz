"""Dropping a file into the TUI has to open it.

Dropping does not paste the path — it pastes the path as a shell would need it
written, which differs by terminal. A file whose folder has a space in its name
("regender-xyz test books") arrived escaped or quoted, opened with neither, and
the prompt that invites you to drop one said only "File not found".
"""

import pytest

from src.utils.paths import normalize_dropped_path

PLAIN = "/Users/me/test books/pride.txt"


class TestWhatTerminalsProduce:
    @pytest.mark.parametrize(
        "dropped",
        [
            PLAIN,
            "/Users/me/test\\ books/pride.txt",
            f"'{PLAIN}'",
            f'"{PLAIN}"',
            f"  {PLAIN}  ",
            f"  '{PLAIN}'  ",
        ],
    )
    def test_every_form_resolves_to_the_same_path(self, dropped):
        assert normalize_dropped_path(dropped) == PLAIN

    def test_a_file_url_is_decoded(self):
        assert (
            normalize_dropped_path("file:///Users/me/test%20books/pride.txt")
            == "/Users/me/test books/pride.txt"
        )


class TestItDoesNotCorruptRealPaths:
    def test_a_quoted_backslash_is_literal(self):
        """Inside quotes a backslash is a character, not an escape."""
        assert normalize_dropped_path(r"'/tmp/od\d name.txt'") == r"/tmp/od\d name.txt"

    def test_an_unquoted_backslash_is_an_escape(self):
        assert normalize_dropped_path(r"/tmp/a\ b.txt") == "/tmp/a b.txt"

    def test_a_path_with_no_special_characters_is_untouched(self):
        assert normalize_dropped_path("/tmp/plain.txt") == "/tmp/plain.txt"

    def test_an_apostrophe_inside_a_name_survives(self):
        """Only a matched pair wraps the path; one apostrophe is part of it."""
        assert normalize_dropped_path("/tmp/O'Brien.txt") == "/tmp/O'Brien.txt"

    def test_empty_input_is_handled(self):
        assert normalize_dropped_path("   ") == ""


class TestTheRealCase:
    def test_the_folder_that_broke_it(self):
        """The repo's own test books live in a folder with two spaces in it."""
        real = "/Users/jasonhuff/regender-xyz test books/pride-prejudice-golden.txt"
        for dropped in (real.replace(" ", "\\ "), f"'{real}'", f'"{real}"'):
            assert normalize_dropped_path(dropped) == real
