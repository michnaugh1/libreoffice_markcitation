"""
UI utilities for the TOA extension.

Thin wrappers around UNO dialog services so the rest of the code
doesn't have to deal with the boilerplate.
"""
from com.sun.star.awt.MessageBoxType import MESSAGEBOX, QUERYBOX
from com.sun.star.awt.MessageBoxButtons import BUTTONS_OK, BUTTONS_OK_CANCEL, BUTTONS_YES_NO
from com.sun.star.awt.MessageBoxResults import OK, YES


def _get_parent(frame):
    """Return a suitable parent window for dialogs."""
    return frame.getContainerWindow()


def show_message(frame, title, message):
    """Show a simple OK message box."""
    parent = _get_parent(frame)
    toolkit = parent.getToolkit()
    box = toolkit.createMessageBox(parent, MESSAGEBOX, BUTTONS_OK, title, message)
    box.execute()
    box.dispose()


def ask_yes_no(frame, title, message):
    """Show a Yes/No question box. Returns True if the user chose Yes."""
    parent = _get_parent(frame)
    toolkit = parent.getToolkit()
    box = toolkit.createMessageBox(parent, QUERYBOX, BUTTONS_YES_NO, title, message)
    result = box.execute()
    box.dispose()
    return result == YES
