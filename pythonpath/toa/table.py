"""
Table of Authorities generation.

Inserts a formatted TOA at the current cursor position.

Output format:
    TABLE OF AUTHORITIES                    ← bold, centred
                              Page          ← right-aligned tab
    Cases                                   ← bold, underlined heading
    Brown v. Board, 347 U.S. 483 (1954)... 3, 7   ← dot-leader entry
    Statutes
    42 U.S.C. § 1983...................... passim
"""

import uno
from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK

TOA_TABLE_BOOKMARK = "TOA_TABLE"

# ── Formatting constants ───────────────────────────────────────────────────────
_ALIGN_LEFT   = uno.Enum("com.sun.star.style.ParagraphAdjust", "LEFT")
_ALIGN_CENTER = uno.Enum("com.sun.star.style.ParagraphAdjust", "CENTER")
_BOLD         = 150.0   # com.sun.star.awt.FontWeight.BOLD
_NORMAL       = 100.0   # com.sun.star.awt.FontWeight.NORMAL
_UL_SINGLE    = 1       # com.sun.star.awt.FontUnderline.SINGLE
_UL_NONE      = 0       # com.sun.star.awt.FontUnderline.NONE
_TAB_RIGHT    = uno.Enum("com.sun.star.style.TabAlign", "RIGHT")


# ── Public entry point ─────────────────────────────────────────────────────────

def generate(doc, frame, toa_data, passim_threshold=None):
    """
    Build and insert a Table of Authorities at the current cursor position.

    Returns (success: bool, error_message: str | None).
    """
    from toa import data as D, document as DOC

    if passim_threshold is None:
        passim_threshold = toa_data.get("passim_threshold", D.DEFAULT_PASSIM_THRESHOLD)

    citations = toa_data["citations"]
    if not citations:
        return False, "No citations are marked in this document."

    # Save insertion point before moving the view cursor around for page nums.
    controller = frame.getController()
    view_cursor = controller.getViewCursor()
    text = doc.getText()
    insert_range = view_cursor.getStart()

    # ── Collect page numbers ──────────────────────────────────────────────────
    # Group by (category, short_form) so that the same citation cited on
    # multiple pages appears once in the table with all its page numbers.
    groups = {}
    for cit_id, cit in citations.items():
        page = DOC.get_bookmark_page(doc, D.bookmark_name(cit_id))
        if page is None:
            continue
        key = (cit["category"], cit["short_form"])
        if key not in groups:
            groups[key] = {
                "long_form":  cit["long_form"],
                "pages":      set(),
                "first_page": page,
            }
        groups[key]["pages"].add(page)
        # Use the long_form from the earliest occurrence in the document.
        if page < groups[key]["first_page"]:
            groups[key]["first_page"] = page
            groups[key]["long_form"]  = cit["long_form"]

    if not groups:
        return False, (
            "Could not determine page numbers for any citations.\n\n"
            "Make sure the document is open in Print Layout view, not Web View."
        )

    # ── Organise by category, sort within each ────────────────────────────────
    categories = D.all_categories(toa_data)
    by_cat = {}
    for (category, short_form), info in groups.items():
        pages = sorted(info["pages"])
        pages_str = "passim" if len(pages) > passim_threshold \
                    else ", ".join(str(p) for p in pages)
        by_cat.setdefault(category, []).append(
            (short_form.lower(), info["long_form"], pages_str)
        )
    for entries in by_cat.values():
        entries.sort()   # sort by lowercased short_form

    # ── Insert ────────────────────────────────────────────────────────────────
    tab_pos = _text_width(doc) - 100   # 1 mm from right edge of text area
    cursor  = text.createTextCursorByRange(insert_range)
    _insert_all(text, cursor, categories, by_cat, tab_pos)

    # ── Mark the table location with a bookmark ───────────────────────────────
    # This allows rebuild detection: if TOA_TABLE already exists, warn the user.
    # We place it at the title paragraph (insert_range).
    try:
        bookmarks = doc.getBookmarks()
        if bookmarks.hasByName(TOA_TABLE_BOOKMARK):
            text.removeTextContent(bookmarks.getByName(TOA_TABLE_BOOKMARK))
        bm = doc.createInstance("com.sun.star.text.Bookmark")
        bm.setName(TOA_TABLE_BOOKMARK)
        marker_cursor = text.createTextCursorByRange(insert_range)
        text.insertTextContent(marker_cursor, bm, False)
    except Exception:
        pass   # bookmark is best-effort; don't fail the whole operation

    return True, None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _text_width(doc):
    """
    Return the text-area width in 1/100 mm (page width minus both margins).
    Falls back to 15240 (~6 in) if the page style cannot be read.
    """
    try:
        page_styles = doc.getStyleFamilies().getByName("PageStyles")
        for name in ("Default Page Style", "Default Style", "Standard"):
            try:
                s = page_styles.getByName(name)
                return s.Width - s.LeftMargin - s.RightMargin
            except Exception:
                continue
    except Exception:
        pass
    return 15240


def _dot_tab(position):
    """Create a right-justified, dot-filled tab stop at *position* (1/100 mm)."""
    tab = uno.createUnoStruct("com.sun.star.style.TabStop")
    tab.Position   = position
    tab.Alignment  = _TAB_RIGHT
    tab.FillChar    = '.'
    tab.DecimalChar = '.'
    return tab


def _set(cursor, prop, val):
    """setPropertyValue, silently ignoring unsupported properties."""
    try:
        cursor.setPropertyValue(prop, val)
    except Exception:
        pass


def _set_tab_stops(cursor, tab_stops):
    """
    Set ParaTabStops with an explicit UNO type so LO knows the element type.
    Without this, Python UNO can't infer the struct sequence type and silently
    falls back to default tab stops. uno.Any must be passed via uno.invoke.
    """
    typed = uno.Any("[]com.sun.star.style.TabStop", tab_stops)
    uno.invoke(cursor, "setPropertyValue", ("ParaTabStops", typed))


def _para(text, cursor, content,
          align=None, bold=False, underline=False, tab_stops=()):
    """
    Emit one paragraph: set formatting, insert text, insert paragraph break.

    All properties are set explicitly on every call so that paragraphs never
    accidentally inherit stray formatting from the cursor's starting position
    (e.g. the 'TOA Citation Mark' style if the cursor was inside a citation).
    """
    _set(cursor, "CharStyleName",  "")           # strip any char style
    _set(cursor, "CharHighlight",  -1)            # no highlight (COL_TRANSPARENT)
    _set(cursor, "CharWeight",     _BOLD if bold else _NORMAL)
    _set(cursor, "CharUnderline",  _UL_SINGLE if underline else _UL_NONE)
    _set(cursor, "ParaAdjust",     align or _ALIGN_LEFT)
    _set_tab_stops(cursor, tab_stops)
    _set(cursor, "ParaLeftMargin", 0)
    _set(cursor, "ParaFirstLineIndent", 0)

    text.insertString(cursor, content, False)
    text.insertControlCharacter(cursor, PARAGRAPH_BREAK, False)


def _insert_all(text, cursor, categories, by_cat, tab_pos):
    """Insert every TOA paragraph in order."""
    dots = (_dot_tab(tab_pos),)

    # Title
    _para(text, cursor, "TABLE OF AUTHORITIES", align=_ALIGN_CENTER, bold=True)

    # Blank line after title
    _para(text, cursor, "")

    first_cat = True
    for category in categories:
        if category not in by_cat:
            continue
        if not first_cat:
            _para(text, cursor, "")   # blank line between categories
        first_cat = False

        # Category heading
        _para(text, cursor, category, bold=True, underline=True)

        # Citation entries: long form + tab + page numbers
        for _, long_form, pages_str in by_cat[category]:
            _para(text, cursor, f"{long_form}\t{pages_str}", tab_stops=dots)
