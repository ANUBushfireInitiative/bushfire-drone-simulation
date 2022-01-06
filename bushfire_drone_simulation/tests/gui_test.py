"""Tests for the bushfire drone simulation GUI."""

from pathlib import Path

import pytest
from PIL import Image
from pytest_mock import MockFixture

from bushfire_drone_simulation.gui.gui import GUI


@pytest.fixture(name="gui")
def fixture_gui() -> GUI:
    """Pytest fixture to provide GUI without running the mainloop."""
    return GUI(mainloop=False)


def test_gui_runs(gui: GUI) -> None:
    """Test that the GUI runs."""
    gui.run_events()


def test_gui_screenshot_dialog(  # type: ignore
    gui: GUI, tmp_path: Path, mocker: MockFixture
) -> None:
    """Test GUI screenshot dialog."""
    filename = tmp_path / "screenshot.png"
    mocker.patch("tkinter.filedialog.asksaveasfilename", return_value=filename)
    gui.run_events()
    gui.tools_menu.invoke(gui.tools_menu.index("Screenshot") or 0)
    gui.run_events()
    assert filename.exists(), f"Error: Screenshot not created at {filename}."
    Image.open(filename)
