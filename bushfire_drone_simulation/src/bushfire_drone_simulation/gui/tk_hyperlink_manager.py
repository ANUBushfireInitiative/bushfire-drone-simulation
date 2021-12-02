"""
Tkinter hyperlink assistant.

This module was modified from http://www.effbot.org/zone/copyright.htm with the following license:

Copyright © 1995-2014 by Fredrik Lundh

By obtaining, using, and/or copying this software and/or its associated documentation, you agree
that you have read, understood, and will comply with the following terms and conditions:

Permission to use, copy, modify, and distribute this software and its associated documentation for
any purpose and without fee is hereby granted, provided that the above copyright notice appears in
all copies, and that both that copyright notice and this permission notice appear in supporting
documentation, and that the name of Secret Labs AB or the author not be used in advertising or
publicity pertaining to distribution of the software without specific, written prior permission.

SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING ALL
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR BE
LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION,
ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""

from tkinter import Text
from tkinter.constants import CURRENT
from typing import Any, Callable, Dict, Tuple


class HyperlinkManager:
    """HyperlinkManager."""

    def __init__(self, text: Text) -> None:
        """Initialise hyperlink manager.

        Args:
            text (Text): text
        """
        self.text = text
        self.text.tag_config("hyper", foreground="blue", underline=True)
        self.text.tag_bind("hyper", "<Enter>", self._enter)
        self.text.tag_bind("hyper", "<Leave>", self._leave)
        self.text.tag_bind("hyper", "<Button-1>", self._click)
        self.links: Dict[str, Callable[[], Any]] = {}

    def add(self, action: Callable[[], Any]) -> Tuple[str, str]:
        """Add action.

        Args:
            action (Callable[[], None]): action

        Returns:
            Tuple[str, str]:
        """
        # add an action to the manager.  returns tags to use in
        # associated text widget
        tag = f"hyper-{len(self.links)}"
        self.links[tag] = action
        return "hyper", tag

    def _enter(self, _: Any) -> None:
        """Convert mouse pointer to hand on hover."""
        self.text.config(cursor="hand2")

    def _leave(self, _: Any) -> None:
        """Remove hand curser on leave."""
        self.text.config(cursor="")

    def _click(self, _: Any) -> None:
        """Handle click."""
        for tag in self.text.tag_names(CURRENT):
            if tag[:6] == "hyper-":
                self.links[tag]()
                return
