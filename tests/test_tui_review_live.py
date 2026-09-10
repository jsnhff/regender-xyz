"""The review menu, driven through a real Textual app.

The menu rendered correctly and could not be typed into: a transform leaves
the input bar disabled and spinning, and only the export menu turned it back
on. Unit tests on the handler could not see that, because they call the
handler directly -- which is exactly the step a person could not reach.
"""

import pytest

from src.cli.tui import HeaderBar, InputBar, RegenderTUI

pytestmark = pytest.mark.asyncio

FINDING = {
    "severity": "needs_review",
    "kind": "residual_term",
    "chapter": 1,
    "paragraph": 12,
    "detail": "'pages' left untransformed",
    "excerpt": "...read three pages, he interrupted her",
    "term": "pages",
}


def app_with_review():
    app = RegenderTUI(process_callback=None)
    app._review_items = [dict(FINDING)]
    app._review_idx = 0
    app._json_output_path = ""
    return app


class TestTheKeyboardComesBack:
    async def test_the_input_is_usable_at_the_review_menu(self):
        """A question you cannot answer is not a question."""
        app = app_with_review()
        async with app.run_test() as pilot:
            bar = app.query_one(InputBar)
            bar.disable()
            await pilot.pause()

            app._show_review_menu()
            await pilot.pause()

            assert not bar.disabled, "the review menu left the input disabled"

    async def test_typing_reaches_the_review_handler(self):
        app = app_with_review()
        async with app.run_test() as pilot:
            app._show_review_menu()
            await pilot.pause()
            assert app._stage == "qc_review"

            app._handle_review_input("")
            await pilot.pause()
            assert app._review_idx == 1, "answering did not advance the stepper"

    async def test_the_export_menu_is_still_usable(self):
        app = app_with_review()
        async with app.run_test() as pilot:
            bar = app.query_one(InputBar)
            bar.disable()
            await pilot.pause()

            app._show_export_menu()
            await pilot.pause()
            assert not bar.disabled


class TestTheHeaderCost:
    async def test_the_real_spend_reaches_the_header(self):
        """The report showed $0.19 while the header stayed blank."""
        app = app_with_review()
        async with app.run_test() as pilot:
            header = app.query_one(HeaderBar)
            header.set_actual_cost(0.19)
            await pilot.pause()

            labels = app.query("#stats-row2 > Label")
            rendered = str(labels[-1].content)
            assert "$0.19" in rendered, f"header shows {rendered!r}"

    async def test_a_run_report_updates_the_header(self):
        app = app_with_review()
        app._session_usage = {"tokens_in": 32160, "tokens_out": 12371, "calls": 13}
        app._book_stats = {"chapters": 5}
        app._json_output_path = "books/output/x/gender_swap.json"
        async with app.run_test() as pilot:
            app._show_run_report({"changes": 1}, 34.5)
            await pilot.pause()

            rendered = str(app.query("#stats-row2 > Label")[-1].content)
            assert "$" in rendered, f"header shows {rendered!r}"


class TestTheHeaderFitsEightyColumns:
    """The figure was reaching the header and being clipped off the edge.

    "total cost: $0.19" wants 17 columns and the row gives the last label 16,
    so the header read as though no cost had been recorded at all.
    """

    async def check(self, cost_setter, expected):
        app = RegenderTUI(process_callback=None)
        async with app.run_test(size=(80, 24)) as pilot:
            header = app.query_one(HeaderBar)
            header._transform = "gender_swap"
            header._model = "Claude Sonnet 5"
            cost_setter(header)
            await pilot.pause()
            label = app.query("#stats-row2 > Label")[-1]
            text = str(label.content)
            assert expected in text
            assert len(text) <= label.size.width, (
                f"{text!r} needs {len(text)} columns, has {label.size.width}"
            )

    async def test_a_real_spend_fits(self):
        await self.check(lambda h: h.set_actual_cost(0.19), "$0.19")

    async def test_a_large_spend_fits(self):
        await self.check(lambda h: h.set_actual_cost(123.45), "$123.45")

    async def test_an_estimate_fits(self):
        await self.check(lambda h: h.update_meta({"estimated_cost": 12.34}), "~$12.34")

    async def test_an_unpriced_model_fits(self):
        await self.check(lambda h: h.update_meta({"estimated_cost": None}), "—")
