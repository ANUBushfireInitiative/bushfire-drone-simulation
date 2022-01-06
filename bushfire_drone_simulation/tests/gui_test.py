"""Tests for the bushfire drone simulation GUI."""

import _tkinter

from bushfire_drone_simulation.gui.gui import GUI


def test_gui_runs() -> None:
    """Test that the GUI runs."""
    gui = GUI(mainloop=False)
    while gui.window.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
        pass
