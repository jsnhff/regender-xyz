# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jason Huff
"""A finished run says what is wrong with it.

The command line printed "Success!", a character count and a change count, and
exited 0 -- for a book with chapters the model never transformed, for a book
whose QC found the protagonist under two names, and for a book whose QC had
crashed and checked nothing. Every one of those was known to the run. They
were log lines among several hundred, or a file beside the output.

The interface did better, and still showed nothing at all when QC failed to
run, which is exactly what it shows for a clean report.
"""

import argparse
import asyncio

import pytest

import regender_cli
from src.app import run_problems

CLEAN = {
    "success": True,
    "book_title": "Pride and Prejudice",
    "characters": 34,
    "cast": {"total": 34, "regendered": 28},
    "changes": 312,
    "output_path": "out/gender_swap.json",
    "untransformed_chapters": [],
    "quality_control": {
        "structural": 0,
        "auto_fixable": 0,
        "needs_review": 2,
        "gendered_words": 4830,
        "transformed_words": 4812,
        "report": "out/gender_swap_qc.json",
    },
    "name_map_problems": [],
    "substitutions_to_review": 3,
}


class TestWhatCountsAsAProblem:
    def test_a_clean_run_has_none(self):
        assert run_problems(CLEAN) == []

    def test_things_to_review_are_not_problems(self):
        """needs_review is ordinary work; a gate that cries wolf gets switched off."""
        result = {**CLEAN, "quality_control": {**CLEAN["quality_control"], "needs_review": 57}}
        assert run_problems(result) == []

    def test_untransformed_chapters_are_named(self):
        (problem,) = run_problems({**CLEAN, "untransformed_chapters": [3, 7]})
        assert "Chapters 3, 7 kept the original text" in problem

    def test_one_chapter_reads_as_one(self):
        (problem,) = run_problems({**CLEAN, "untransformed_chapters": [12]})
        assert problem.startswith("Chapter 12 kept")

    def test_structural_findings_are_a_problem(self):
        qc = {**CLEAN["quality_control"], "structural": 2, "naming_problems": 1}
        (problem,) = run_problems({**CLEAN, "quality_control": qc})
        assert "2 structural problems" in problem
        assert "1 of them a character called a name nobody chose" in problem

    def test_one_finding_that_is_a_name_is_not_one_of_one(self):
        qc = {**CLEAN["quality_control"], "structural": 1, "naming_problems": 1}
        (problem,) = run_problems({**CLEAN, "quality_control": qc})
        assert "1 structural problem: a character is called a name nobody chose." in problem

    def test_qc_that_crashed_is_a_problem(self):
        result = {**CLEAN, "quality_control": {"did_not_run": "KeyError: 'paragraphs'"}}
        (problem,) = run_problems(result)
        assert "Quality control did not run (KeyError: 'paragraphs')" in problem
        assert "nothing in this book has been checked" in problem

    def test_qc_that_never_ran_is_a_problem(self):
        (problem,) = run_problems({**CLEAN, "quality_control": None})
        assert "Quality control did not run" in problem

    def test_name_map_problems_are_listed_and_counted(self):
        names = ["two people, one name", "given name lost", "a third", "a fourth"]
        (problem,) = run_problems({**CLEAN, "name_map_problems": names})
        assert "4 problems" in problem
        assert "two people, one name; given name lost; and 2 more" in problem

    def test_several_at_once_are_all_reported(self):
        result = {
            **CLEAN,
            "untransformed_chapters": [5],
            "quality_control": None,
            "name_map_problems": ["x"],
        }
        assert len(run_problems(result)) == 3


class TestQCThatDidNotRunSaysSo:
    def test_a_crash_is_returned_not_swallowed(self, tmp_path):
        from src.app import Application
        from src.models.transformation import TransformType

        app = Application.__new__(Application)
        import logging

        app.logger = logging.getLogger("test")

        class Transformation:
            def get_transformed_book(self):
                raise KeyError("paragraphs")

        out = tmp_path / "o.json"
        out.write_text("{}")
        summary = app._run_quality_control(
            {"chapters": []}, Transformation(), TransformType.GENDER_SWAP, str(out), []
        )
        assert "paragraphs" in summary["did_not_run"]


class _Provider:
    model = "claude-sonnet-5-5"
    tokens_in = 120_000
    tokens_out = 140_000
    calls = 61


class _App:
    """Stands in for the Application: returns a finished run without making one."""

    result = CLEAN

    def __init__(self, _config):
        self.shut_down = False

    async def process_book(self, **_kwargs):
        return dict(type(self).result)

    def get_service(self, _name):
        return type("Service", (), {"provider": _Provider()})()

    def shutdown(self):
        self.shut_down = True


def _run_cli(monkeypatch, tmp_path, result):
    app_class = type("App", (_App,), {"result": result})
    monkeypatch.setattr(regender_cli, "Application", app_class)
    monkeypatch.setattr(regender_cli, "_write_decision_sheet", lambda *_a: None)
    args = argparse.Namespace(
        config=None,
        input="book.txt",
        output=str(tmp_path / "gender_swap.json"),
        transform_type="gender_swap",
        characters=None,
        characters_file=None,
        name_map=None,
        title=None,
    )
    asyncio.run(regender_cli.process_book(args))


class TestTheCommandLine:
    def test_a_clean_run_exits_normally_and_reports(self, monkeypatch, tmp_path, capsys):
        _run_cli(monkeypatch, tmp_path, CLEAN)
        out = capsys.readouterr().out
        assert "Success" in out
        assert "Characters: 34 (28 regendered)" in out
        assert "Gender words: 4,812 of 4,830 changed (99.6%)" in out
        assert "QC: 0 structural, 0 auto-fixable, 2 to review" in out
        assert "To review: 3 substitution pairs" in out
        assert "Before you use this book" not in out

    def test_one_pair_is_singular(self, monkeypatch, tmp_path, capsys):
        _run_cli(monkeypatch, tmp_path, {**CLEAN, "substitutions_to_review": 1})
        assert "To review: 1 substitution pair\n" in capsys.readouterr().out

    def test_it_names_the_model_and_what_it_used(self, monkeypatch, tmp_path, capsys):
        _run_cli(monkeypatch, tmp_path, CLEAN)
        out = capsys.readouterr().out
        assert "Model: claude-sonnet-5-5" in out
        assert "Usage: 120,000 tokens in, 140,000 out, 61 calls" in out

    def test_untransformed_chapters_are_said_and_change_the_exit(
        self, monkeypatch, tmp_path, capsys
    ):
        with pytest.raises(SystemExit) as stopped:
            _run_cli(monkeypatch, tmp_path, {**CLEAN, "untransformed_chapters": [3, 7]})
        assert stopped.value.code == regender_cli.EXIT_FINISHED_WITH_PROBLEMS == 2
        out = capsys.readouterr().out
        assert "Finished, with problems" in out
        assert "Success" not in out, "the heading said success above a list of problems"
        assert "Before you use this book" in out
        assert "Chapters 3, 7 kept the original text" in out
        assert "Output:" in out, "the book was still written, and the path still shown"

    def test_a_qc_crash_is_said_and_changes_the_exit(self, monkeypatch, tmp_path, capsys):
        result = {**CLEAN, "quality_control": {"did_not_run": "boom"}}
        with pytest.raises(SystemExit) as stopped:
            _run_cli(monkeypatch, tmp_path, result)
        assert stopped.value.code == 2
        out = capsys.readouterr().out
        assert "Quality control did not run (boom)" in out
        assert "QC: 0 structural" not in out, "a crashed QC must not print a clean tally"

    def test_a_failed_run_still_exits_one(self, monkeypatch, tmp_path, capsys):
        with pytest.raises(SystemExit) as stopped:
            _run_cli(monkeypatch, tmp_path, {"success": False, "error": "no provider"})
        assert stopped.value.code == 1
