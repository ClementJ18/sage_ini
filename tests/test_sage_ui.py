"""Qt-level tests for the sage_ui Browser: the onboarding state and the typo-tolerant
search. Headless via the Qt 'offscreen' platform, so no display is needed; marked `full`
(peripheral package, like the other sage_utils/sage_ui suites)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # headless; must precede the Qt import

import pytest

pytestmark = pytest.mark.full

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication, QLabel, QPushButton  # noqa: E402

import sage_ui.browser as browser_module  # noqa: E402
from sage_ini.model.game import Game  # noqa: E402
from sage_ini.parser.blockparser import parse  # noqa: E402
from sage_ui.browser import Browser  # noqa: E402
from sage_utils.views import display_name_index  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def browser(qapp, tmp_path, monkeypatch):
    # An empty APPDATA (no saved sources) and a tmp cwd (no repo-root `data/` to auto-add)
    # land the window in its fresh-start state.
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    window = Browser()
    window.sources_panel.clear()
    return window


def _panel_widget(window):
    """The single widget currently filling the results area."""
    return window._panels_row.itemAt(0).widget()


def _labels(widget):
    found = widget.findChildren(QLabel)
    if isinstance(widget, QLabel):  # a bare-label panel is its own only label
        found = [widget, *found]
    return [label.text() for label in found]


def _buttons(widget):
    return [button.text() for button in widget.findChildren(QPushButton)]


def _load_units(window):
    """Give the window a one-object game with a localized display name."""
    game = Game()
    game.load_document(
        parse("Object MordorFighter\n  DisplayName = OBJECT:Mordor\nEnd\n", file="t.ini").document
    )
    game.strings.update({"OBJECT:Mordor": "Mordor Orc Warrior"})
    window.game = game
    window._object_names = ["MordorFighter"]
    window._display_names, window._display_index = display_name_index(game, ["MordorFighter"])
    return game


class TestOnboarding:
    def test_guides_to_add_files_when_no_install_detected(self, browser, monkeypatch):
        monkeypatch.setattr(browser_module, "detect_installed_games", lambda: {})
        browser._set_onboarding()
        card = _panel_widget(browser)

        assert any("Welcome" in text for text in _labels(card))
        # No auto-detected game → the manual "add files" buttons are offered.
        assert any("Add data folder" in text for text in _buttons(card))
        assert any("Add .big" in text for text in _buttons(card))

    def test_offers_edain_when_an_install_is_detected(self, browser, monkeypatch):
        monkeypatch.setattr(
            browser_module, "detect_installed_games", lambda: {"RotWK": r"C:\Games\RotWK"}
        )
        browser._set_onboarding()
        card = _panel_widget(browser)

        assert any("Load Edain" in text for text in _buttons(card))
        assert any("RotWK" in text for text in _labels(card))  # names the detected install

    def test_ready_message_once_a_source_is_queued(self, browser):
        browser.sources_panel.add_source("folder", r"C:\data")
        browser._show_initial_state()
        # A queued source replaces onboarding with a one-line "press Load" prompt.
        assert any("Load" in text for text in _labels(_panel_widget(browser)))


class TestTypoSearch:
    def test_exact_name_opens_directly(self, browser):
        _load_units(browser)
        browser.search.setText("MordorFighter")
        browser._on_enter()

        assert browser.panel_a is not None
        assert browser.panel_a._current_obj.name == "MordorFighter"

    def test_misspelled_name_offers_a_suggestion_that_opens(self, browser):
        _load_units(browser)
        browser.search.setText("MordrFighter")  # dropped an 'o'
        browser._on_enter()
        card = _panel_widget(browser)

        assert any("No unit matched" in text for text in _labels(card))
        assert any("MordorFighter" in text for text in _buttons(card))

        # Clicking the suggestion opens the unit.
        suggestion = next(b for b in card.findChildren(QPushButton) if "MordorFighter" in b.text())
        suggestion.click()
        assert browser.panel_a is not None
        assert browser.panel_a._current_obj.name == "MordorFighter"

    def test_misspelled_display_name_resolves_in_display_mode(self, browser):
        _load_units(browser)
        browser.string_search_toggle.setChecked(True)
        browser.search.setText("Mordor Orc Warier")  # typo of "Mordor Orc Warrior"
        browser._on_enter()
        card = _panel_widget(browser)

        assert any("Mordor Orc Warrior" in text for text in _buttons(card))

    def test_no_close_match_shows_a_gentle_nudge_not_a_button(self, browser):
        _load_units(browser)
        browser.search.setText("zzzzzzzz")
        browser._on_enter()
        card = _panel_widget(browser)

        assert any("No unit matched" in text for text in _labels(card))
        assert _buttons(card) == []  # nothing close enough to suggest

    def test_compare_typo_reports_the_closest_on_the_status_line(self, browser):
        _load_units(browser)
        browser.show_object("MordorFighter")  # panel A must exist before comparing
        browser.compare_search.setText("MordrFighter")
        browser._on_compare_enter()

        assert "MordorFighter" in browser.status.text()
