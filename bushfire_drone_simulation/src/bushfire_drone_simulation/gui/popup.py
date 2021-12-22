"""
Class for managing creating simple popup windows in GUI.
"""

import tkinter as tk


class GuiPopup(tk.Toplevel):
    """
    Class for managing creating simple popup windows in GUI.
    """

    def __init__(self, parent_window: tk.Tk, width: int, height: int) -> None:
        super().__init__(parent_window)
        self.width = width
        self.height = height
        self.parent_window = parent_window
        self.grab_set()
        popup_x = (
            self.parent_window.winfo_x() + (self.parent_window.winfo_width() - self.width) // 2
        )
        popup_y = (
            self.parent_window.winfo_y() + (self.parent_window.winfo_height() - self.height) // 2
        )
        self.geometry(f"{self.width}x{self.height}+{popup_x}+{popup_y}")

    def close(self) -> None:
        """Close popup."""
        self.grab_release()  # type: ignore
        self.destroy()
