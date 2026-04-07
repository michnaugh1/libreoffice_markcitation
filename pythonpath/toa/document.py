"""
Document-level UNO operations: character styles, bookmarks, page numbers.

Keeps all direct UNO API calls in one place so commands.py stays readable.
"""

TOA_STYLE_NAME = "TOA Citation Mark"
TOA_HIGHLIGHT_COLOR = 0xADD8E6   # CSS "lightblue" — light enough to read through
TOA_NO_COLOR       = -1          # LibreOffice COL_TRANSPARENT as signed int32 — removes highlight


# ── Character style ────────────────────────────────────────────────────────────

def ensure_style(doc):
    """
    Create the 'TOA Citation Mark' character style if it doesn't exist.
    Sets the initial light-blue highlight. Subsequent calls are no-ops
    so toggling the highlight later is not undone by re-marking.

    We use CharHighlight (the dedicated "text marker" / highlighter-pen
    property) rather than CharBackColor + CharBackTransparent. Setting
    CharBackTransparent=True while CharBackColor is set causes LibreOffice
    to render the background black in some versions; CharHighlight avoids
    that entirely — 0xFFFFFFFF is its transparent/off value.
    """
    styles = doc.getStyleFamilies().getByName("CharacterStyles")
    if not styles.hasByName(TOA_STYLE_NAME):
        style = doc.createInstance("com.sun.star.style.CharacterStyle")
        styles.insertByName(TOA_STYLE_NAME, style)
        style = styles.getByName(TOA_STYLE_NAME)
        style.CharHighlight = TOA_HIGHLIGHT_COLOR


def toggle_highlights(doc):
    """
    Flip CharHighlight on the style between light-blue and transparent.
    Because all marked text uses the same named style, one property change
    updates every citation mark in the document simultaneously.

    Returns True if highlights are now ON, False if now OFF.
    Returns None if the style doesn't exist yet (no marks in document).
    """
    styles = doc.getStyleFamilies().getByName("CharacterStyles")
    if not styles.hasByName(TOA_STYLE_NAME):
        return None
    style = styles.getByName(TOA_STYLE_NAME)
    if style.CharHighlight in (TOA_NO_COLOR, -1):
        style.CharHighlight = TOA_HIGHLIGHT_COLOR
        return True
    else:
        style.CharHighlight = TOA_NO_COLOR
        return False


# ── Bookmarks ──────────────────────────────────────────────────────────────────

def insert_citation_bookmark(doc, text_range, bm_name):
    """
    Apply the TOA character style and insert a named bookmark over text_range.

    text_range must be a single XTextRange (e.g. selection.getByIndex(0)).
    The bookmark absorbs the range so it tracks that exact span of text.
    """
    text = doc.getText()
    cursor = text.createTextCursorByRange(text_range)

    # Apply character style before the bookmark is inserted so the styled
    # text is visually marked regardless of highlight toggle state.
    cursor.setPropertyValue("CharStyleName", TOA_STYLE_NAME)

    # Create the bookmark and make it cover the cursor's span.
    bookmark = doc.createInstance("com.sun.star.text.Bookmark")
    bookmark.setName(bm_name)
    text.insertTextContent(cursor, bookmark, True)   # True = absorb cursor range


def remove_citation_bookmark(doc, bm_name):
    """
    Clear the TOA character style on the bookmarked text and remove the bookmark.
    Returns True if found and removed, False if the bookmark did not exist.
    """
    bookmarks = doc.getBookmarks()
    if not bookmarks.hasByName(bm_name):
        return False

    bookmark = bookmarks.getByName(bm_name)
    anchor = bookmark.getAnchor()

    # Clear the character style from the anchored text
    text = doc.getText()
    cursor = text.createTextCursorByRange(anchor)
    cursor.setPropertyValue("CharStyleName", "")

    text.removeTextContent(bookmark)
    return True


def find_toa_bookmark_at_cursor(doc, frame, bookmark_prefix):
    """
    Return the name of the TOA bookmark that contains the view cursor,
    or None if the cursor is not inside any TOA bookmark.

    In Python UNO, queryInterface() returns None because the bridge
    exposes all interfaces directly on the object. We call compareRegionStarts
    and compareRegionEnds directly on the text object instead.

    XTextRangeCompare sign convention (confirmed by diagnostic):
      compareRegionStarts(r1, r2) > 0  →  r1.start is BEFORE r2.start
      compareRegionEnds(r1, r2)   < 0  →  r1.end   is AFTER  r2.end

    So for "anchor contains cursor":
      starts >= 0  →  anchor.start is before or at cursor  ✓
      ends   <= 0  →  anchor.end   is after  or at cursor  ✓
    """
    controller = frame.getController()
    view_cursor = controller.getViewCursor()
    text = doc.getText()
    bookmarks = doc.getBookmarks()

    for i in range(bookmarks.getCount()):
        bm = bookmarks.getByIndex(i)
        name = bm.getName()
        if not name.startswith(bookmark_prefix):
            continue
        anchor = bm.getAnchor()
        try:
            starts = text.compareRegionStarts(anchor, view_cursor)
            ends   = text.compareRegionEnds(anchor, view_cursor)
            if starts >= 0 and ends <= 0:
                return name
        except Exception:
            continue
    return None


# ── Page numbers ───────────────────────────────────────────────────────────────

def get_bookmark_page(doc, bm_name):
    """
    Return the rendered page number where a bookmark appears.

    ViewCursor.getPage() is the only reliable UNO method for this —
    it reflects the document's actual pagination at query time.
    Returns None if the bookmark does not exist.
    """
    bookmarks = doc.getBookmarks()
    if not bookmarks.hasByName(bm_name):
        return None

    bookmark = bookmarks.getByName(bm_name)
    anchor = bookmark.getAnchor()

    controller = doc.getCurrentController()
    view_cursor = controller.getViewCursor()

    # Move view cursor to the bookmark's start, then read the page.
    # We save and restore the original position so the visible selection
    # does not change while the table is being built.
    #
    # Edge case: when a citation begins right at the top of a page (i.e.
    # the very first character after a page break), LibreOffice attributes
    # the "before first character" cursor position to the END of the
    # previous page, returning a page number that is one too low.
    # Fix: after landing on anchor.getStart(), step one character to the
    # right into the citation text.  If the page number increases, the
    # anchor start was at a page boundary and the higher value is correct.
    # goRight() returns False at the end of the document, so no overflow.
    saved = view_cursor.getStart()
    try:
        view_cursor.gotoRange(anchor.getStart(), False)
        page = view_cursor.getPage()

        if view_cursor.goRight(1, False):
            page_after = view_cursor.getPage()
            if page_after > page:
                page = page_after   # anchor start was on the boundary
            view_cursor.goLeft(1, False)
    finally:
        view_cursor.gotoRange(saved, False)

    return page
