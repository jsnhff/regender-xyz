"""The content area must wrap long lines, not clip them.

Labels size to their content by default and ContentArea hides overflow-x, so a
sentence longer than the terminal lost its tail off the right edge instead of
continuing on the next row.
"""

import pytest

pytest.importorskip("textual")

from textual.app import App, ComposeResult  # noqa: E402

from src.cli.tui import ContentArea, _lookup_model_cost  # noqa: E402

LONG = (
    "English has no neutral form of sir, madam or ma'am, and master means "
    "four different things depending entirely on the words beside it."
)


class _Harness(App):
    def compose(self) -> ComposeResult:
        yield ContentArea()


@pytest.mark.asyncio
async def test_a_long_line_wraps_instead_of_being_clipped():
    app = _Harness()
    async with app.run_test(size=(80, 24)) as pilot:
        area = app.query_one(ContentArea)
        area.add_line(LONG)
        await pilot.pause()
        label = area.query(".log-line").first()
        # Wider than the terminal, so it has to occupy more than one row.
        assert len(LONG) > 80
        assert label.size.height > 1, "long line did not wrap"
        assert label.size.width <= 80, "line overflowed the terminal width"


@pytest.mark.asyncio
async def test_a_short_line_still_occupies_one_row():
    app = _Harness()
    async with app.run_test(size=(80, 24)) as pilot:
        area = app.query_one(ContentArea)
        area.add_line("Never, sir.")
        await pilot.pause()
        label = area.query(".log-line").first()
        assert label.size.height == 1


class TestModelPricing:
    """Every model the menu can show needs a price, or it reads "unknown"."""

    @pytest.mark.parametrize(
        "model_id,expected",
        [
            ("claude-fable-5-1", (10.00, 50.00)),
            ("claude-fable-5", (10.00, 50.00)),
            ("claude-opus-5", (5.00, 25.00)),
            ("claude-opus-4-8", (5.00, 25.00)),
            ("claude-sonnet-5", (2.00, 10.00)),
            ("claude-sonnet-4-6", (3.00, 15.00)),
            ("claude-haiku-4-5", (1.00, 5.00)),
        ],
    )
    def test_current_models_have_a_price(self, model_id, expected):
        assert _lookup_model_cost(model_id) == expected

    def test_a_dated_id_still_resolves(self):
        assert _lookup_model_cost("claude-haiku-4-5-20251001") == (1.00, 5.00)

    def test_longest_prefix_wins(self):
        """First-match-in-order priced gpt-4o-mini off the gpt-4o row."""
        assert _lookup_model_cost("gpt-4o-mini-2024-07-18") == (0.15, 0.60)
        assert _lookup_model_cost("gpt-4o-2024-08-06") == (2.50, 10.00)

    def test_an_unknown_model_is_still_unknown(self):
        assert _lookup_model_cost("some-other-vendor-model") is None


class TestPricingDrift:
    """The table is hand-maintained, so it needs a way to announce its own age.

    There is no pricing endpoint — the Models API returns ids, context windows
    and capabilities, never a price — so nothing can refresh this automatically.
    What it can do is notice when a model on offer has no price.
    """

    def test_the_menu_flags_a_model_it_cannot_price(self):
        from src.cli.tui import _UNPRICED, RegenderTUI

        app = RegenderTUI.__new__(RegenderTUI)
        app._model_choices = [
            ("claude-opus-5", "Claude Opus 5", "$5.00 / $25.00 per 1M tokens"),
            ("claude-from-the-future", "Claude From The Future", _UNPRICED),
        ]
        printed = []
        app.print = printed.append
        app._warn_about_unpriced_models()
        assert any("no price in the table" in line for line in printed)
        assert any("claude-from-the-future" in line for line in printed)

    def test_it_stays_quiet_when_every_model_is_priced(self):
        from src.cli.tui import RegenderTUI

        app = RegenderTUI.__new__(RegenderTUI)
        app._model_choices = [
            ("claude-opus-5", "Claude Opus 5", "$5.00 / $25.00 per 1M tokens"),
            ("claude-sonnet-5", "Claude Sonnet 5", "$2.00 / $10.00 per 1M tokens"),
        ]
        printed = []
        app.print = printed.append
        app._warn_about_unpriced_models()
        assert printed == []

    def test_the_fallback_list_is_priced(self):
        """The offline list is hardcoded text, so it drifts silently too."""
        from src.cli.tui import _FALLBACK_MODELS, _lookup_model_cost

        for model_id, _display, pricing in _FALLBACK_MODELS["anthropic"]:
            costs = _lookup_model_cost(model_id)
            assert costs is not None, f"{model_id} missing from MODEL_COSTS"
            assert f"${costs[0]:.2f}" in pricing, f"{model_id}: {pricing} disagrees with the table"
            assert f"${costs[1]:.2f}" in pricing, f"{model_id}: {pricing} disagrees with the table"
