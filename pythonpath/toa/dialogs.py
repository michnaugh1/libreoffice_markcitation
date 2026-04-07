"""
Dialog builders for the TOA extension.

All dialogs are constructed programmatically via the UNO dialog API —
no .xdl files needed, which keeps the extension package simpler.

Dialog coordinate units are "Map Appfont" (roughly 1/4 avg char width
horizontally, 1/8 avg char height vertically). Values below are tuned
for a typical desktop font size.
"""
import unohelper
from com.sun.star.awt import XActionListener


# ── Push button type constants ─────────────────────────────────────────────────
# com.sun.star.awt.PushButtonType: STANDARD=0, OK=1, CANCEL=2
_BTN_OK = 1
_BTN_CANCEL = 2


def _make_dialog(ctx, title, width, height):
    """Create a blank dialog model and return (smgr, toolkit, dlg_model)."""
    smgr = ctx.getServiceManager()
    toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    dlg = smgr.createInstanceWithContext(
        "com.sun.star.awt.UnoControlDialogModel", ctx)
    dlg.Width = width
    dlg.Height = height
    dlg.Title = title
    return smgr, toolkit, dlg


def _label(dlg, name, x, y, w, h, text):
    m = dlg.createInstance("com.sun.star.awt.UnoControlFixedTextModel")
    m.PositionX, m.PositionY, m.Width, m.Height = x, y, w, h
    m.Label = text
    dlg.insertByName(name, m)


def _edit(dlg, name, x, y, w, h, text=""):
    m = dlg.createInstance("com.sun.star.awt.UnoControlEditModel")
    m.PositionX, m.PositionY, m.Width, m.Height = x, y, w, h
    m.Text = text
    dlg.insertByName(name, m)


def _listbox(dlg, name, x, y, w, h, items, selected_idx=0):
    m = dlg.createInstance("com.sun.star.awt.UnoControlListBoxModel")
    m.PositionX, m.PositionY, m.Width, m.Height = x, y, w, h
    m.Dropdown = True
    m.StringItemList = tuple(items)
    if items:
        m.SelectedItems = (min(selected_idx, len(items) - 1),)
    dlg.insertByName(name, m)


def _button(dlg, name, x, y, w, h, label, btn_type):
    m = dlg.createInstance("com.sun.star.awt.UnoControlButtonModel")
    m.PositionX, m.PositionY, m.Width, m.Height = x, y, w, h
    m.Label = label
    m.PushButtonType = btn_type
    dlg.insertByName(name, m)


def _run(smgr, toolkit, dlg_model, parent_win):
    """Instantiate the dialog, run it, and return (result, dialog_control)."""
    dialog = smgr.createInstance("com.sun.star.awt.UnoControlDialog")
    dialog.setModel(dlg_model)
    dialog.createPeer(toolkit, parent_win)
    result = dialog.execute()
    return result, dialog


# ── Mark / Edit Citation dialog ────────────────────────────────────────────────

def show_mark_dialog(ctx, frame, selected_text, categories, initial=None):
    """
    Show the Mark Citation (or Edit Citation) dialog.

    Args:
        ctx:           UNO component context
        frame:         active document frame (for parent window)
        selected_text: the text the user has selected
        categories:    list of category strings for the dropdown
        initial:       dict {long_form, short_form, category} for Edit mode,
                       or None for a fresh Mark

    Returns:
        dict {long_form, short_form, category}  — if the user clicked OK
        None                                    — if the user cancelled
    """
    title = "Edit Citation" if initial else "Mark Citation"
    smgr, toolkit, dlg = _make_dialog(ctx, title, width=260, height=104)

    # ── Preview of selected text (read-only) ──────────────────────────────
    preview = selected_text[:85] + ("…" if len(selected_text) > 85 else "")
    _label(dlg, "lbl_preview", 6, 6, 248, 10, f"Selected: {preview}")

    # ── Long Form ─────────────────────────────────────────────────────────
    long_val = initial["long_form"] if initial else selected_text
    _label(dlg, "lbl_long", 6, 24, 64, 10, "Long Form:")
    _edit (dlg, "txt_long", 72, 22, 182, 12, long_val)

    # ── Short Form ────────────────────────────────────────────────────────
    short_val = initial["short_form"] if initial else selected_text
    _label(dlg, "lbl_short", 6, 42, 64, 10, "Short Form:")
    _edit (dlg, "txt_short", 72, 40, 182, 12, short_val)

    # ── Category ──────────────────────────────────────────────────────────
    cat_val = initial.get("category", categories[0]) if initial else categories[0]
    sel_idx = categories.index(cat_val) if cat_val in categories else 0
    _label  (dlg, "lbl_cat", 6, 60, 64, 10, "Category:")
    _listbox(dlg, "lst_cat", 72, 58, 182, 12, categories, sel_idx)

    # ── Buttons ───────────────────────────────────────────────────────────
    _button(dlg, "btn_ok",     150, 84, 50, 14, "OK",     _BTN_OK)
    _button(dlg, "btn_cancel", 204, 84, 50, 14, "Cancel", _BTN_CANCEL)

    # ── Run ───────────────────────────────────────────────────────────────
    parent_win = frame.getContainerWindow()
    result, dialog = _run(smgr, toolkit, dlg, parent_win)

    if result == 1:   # OK
        data = {
            "long_form":  dialog.getControl("txt_long").getText(),
            "short_form": dialog.getControl("txt_short").getText(),
            "category":   dialog.getControl("lst_cat").getSelectedItem(),
        }
        dialog.dispose()
        return data

    dialog.dispose()
    return None


# ── Manage Categories dialog ───────────────────────────────────────────────────

class _CategoryHandler(unohelper.Base, XActionListener):
    """
    Handles Add / Remove / Move Up / Move Down button clicks in the
    Manage Categories dialog without closing it.
    """

    def __init__(self, dialog, initial_categories):
        self.dialog = dialog
        self.categories = list(initial_categories)

    # XActionListener
    def actionPerformed(self, event):
        cmd = event.ActionCommand
        if   cmd == "add":    self._add()
        elif cmd == "remove": self._remove()
        elif cmd == "up":     self._move(-1)
        elif cmd == "down":   self._move(1)

    def disposing(self, source):
        pass

    # ── Internal helpers ──────────────────────────────────────────────────
    def _lb(self):
        return self.dialog.getControl("lb_cats")

    def _refresh(self, select_idx=None):
        lb = self._lb()
        lb.removeItems(0, lb.getItemCount())
        for i, cat in enumerate(self.categories):
            lb.insertItemText(i, cat)
        if select_idx is not None and 0 <= select_idx < len(self.categories):
            lb.selectItemPos(select_idx, True)

    def _add(self):
        txt = self.dialog.getControl("txt_new").getText().strip()
        if not txt or txt in self.categories:
            return
        self.categories.append(txt)
        self._refresh(len(self.categories) - 1)
        self.dialog.getControl("txt_new").setText("")

    def _remove(self):
        idx = self._lb().getSelectedItemPos()
        if 0 <= idx < len(self.categories):
            del self.categories[idx]
            new_sel = min(idx, len(self.categories) - 1) if self.categories else None
            self._refresh(new_sel)

    def _move(self, direction):
        lb  = self._lb()
        idx = lb.getSelectedItemPos()
        new = idx + direction
        if 0 <= idx < len(self.categories) and 0 <= new < len(self.categories):
            self.categories[idx], self.categories[new] = \
                self.categories[new], self.categories[idx]
            self._refresh(new)


def show_build_options_dialog(ctx, frame, passim_threshold):
    """
    Show the Build Table options dialog.

    Lets the user set the passim threshold (number of pages above which
    "passim" is shown instead of individual page numbers).

    Returns dict {"passim_threshold": int} if OK, else None.
    """
    smgr, toolkit, dlg = _make_dialog(ctx, "Build Table of Authorities", width=240, height=68)

    _label(dlg, "lbl_passim", 6, 10, 160, 10,
           "Show 'passim' when cited on more than:")
    _edit(dlg, "txt_passim", 170, 8, 30, 12, str(passim_threshold))
    _label(dlg, "lbl_pages", 204, 10, 30, 10, "pages")

    _button(dlg, "btn_ok",     130, 48, 50, 14, "OK",     _BTN_OK)
    _button(dlg, "btn_cancel", 184, 48, 50, 14, "Cancel", _BTN_CANCEL)

    parent_win = frame.getContainerWindow()
    result, dialog = _run(smgr, toolkit, dlg, parent_win)

    if result == 1:
        try:
            threshold = int(dialog.getControl("txt_passim").getText().strip())
            threshold = max(1, threshold)
        except ValueError:
            threshold = passim_threshold
        dialog.dispose()
        return {"passim_threshold": threshold}

    dialog.dispose()
    return None


def show_manage_categories_dialog(ctx, frame, custom_categories, default_categories):
    """
    Show the Manage Custom Categories dialog.

    Displays current custom categories in a live listbox with Add / Remove /
    Move Up / Move Down controls. Default categories are shown for reference
    but cannot be edited.

    Returns the updated custom_categories list if OK was clicked, else None.
    """
    smgr = ctx.getServiceManager()
    toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)

    dlg = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
    dlg.Width  = 270
    dlg.Height = 220
    dlg.Title  = "Manage Custom Categories"

    # ── Info about fixed defaults ─────────────────────────────────────────
    _label(dlg, "lbl_note", 6, 6, 258, 10,
           "Standard categories (fixed): " + ", ".join(default_categories))

    # ── Custom categories listbox ─────────────────────────────────────────
    _label(dlg, "lbl_custom", 6, 22, 258, 10, "Custom categories:")

    lb_model = dlg.createInstance("com.sun.star.awt.UnoControlListBoxModel")
    lb_model.PositionX, lb_model.PositionY = 6, 34
    lb_model.Width, lb_model.Height        = 182, 80
    lb_model.StringItemList = tuple(custom_categories)
    dlg.insertByName("lb_cats", lb_model)

    # ── Side buttons (STANDARD type — don't close dialog) ─────────────────
    def _std_btn(name, label, y):
        m = dlg.createInstance("com.sun.star.awt.UnoControlButtonModel")
        m.PositionX, m.PositionY, m.Width, m.Height = 194, y, 70, 14
        m.Label          = label
        m.PushButtonType = 0   # STANDARD — fires ActionListener, doesn't close
        dlg.insertByName(name, m)

    _std_btn("btn_up",   "Move Up",   34)
    _std_btn("btn_down", "Move Down", 52)
    _std_btn("btn_rem",  "Remove",    70)

    # Set ActionCommands so the handler can identify which button was clicked
    for name, cmd in [("btn_up", "up"), ("btn_down", "down"), ("btn_rem", "remove")]:
        dlg.getByName(name).ActionCommand = cmd

    # ── New category row ──────────────────────────────────────────────────
    _label(dlg, "lbl_new", 6,  124, 60,  10, "New category:")
    _edit (dlg, "txt_new", 68, 122, 120, 12)

    m = dlg.createInstance("com.sun.star.awt.UnoControlButtonModel")
    m.PositionX, m.PositionY, m.Width, m.Height = 194, 122, 70, 14
    m.Label = "Add"
    m.PushButtonType = 0
    m.ActionCommand  = "add"
    dlg.insertByName("btn_add", m)

    # ── OK / Cancel ───────────────────────────────────────────────────────
    _button(dlg, "btn_ok",     150, 200, 50, 14, "OK",     _BTN_OK)
    _button(dlg, "btn_cancel", 206, 200, 58, 14, "Cancel", _BTN_CANCEL)

    # ── Build dialog and attach listener ──────────────────────────────────
    dialog = smgr.createInstance("com.sun.star.awt.UnoControlDialog")
    dialog.setModel(dlg)
    dialog.createPeer(toolkit, frame.getContainerWindow())

    handler = _CategoryHandler(dialog, custom_categories)
    for btn_name in ("btn_up", "btn_down", "btn_rem", "btn_add"):
        dialog.getControl(btn_name).addActionListener(handler)

    result = dialog.execute()
    final  = handler.categories if result == 1 else None
    dialog.dispose()
    return final
