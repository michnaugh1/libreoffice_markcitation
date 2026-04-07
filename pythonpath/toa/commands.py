"""
Command implementations — one function per TOA menu item.

Naming: cmd_<lowercased Addons.xcu command name>
  org.toa.command:MarkCitation  →  cmd_markcitation(ctx, frame)

Phase 2: MarkCitation, ToggleHighlights
Phase 3: EditCitation, RemoveCitation
Phase 4 will implement: BuildTable
Phase 5 will implement: ManageCategories
"""
from toa.ui import show_message


# ── Phase 2 ───────────────────────────────────────────────────────────────────

def cmd_markcitation(ctx, frame):
    """
    Mark the selected text as a citation.

    Flow:
      1. Validate that text is selected.
      2. Show Mark Citation dialog.
      3. Insert TOA_<uuid> bookmark over the selection.
      4. Apply 'TOA Citation Mark' character style (light-blue highlight).
      5. Persist citation metadata to document properties.
    """
    from toa import data as D, document as DOC, dialogs as DLG

    doc = frame.getController().getModel()

    # ── Ensure the character style exists ────────────────────────────────
    DOC.ensure_style(doc)

    # ── Validate selection ───────────────────────────────────────────────
    controller = frame.getController()
    try:
        selection = controller.getSelection()
        range0 = selection.getByIndex(0)
        selected_text = range0.getString()
    except Exception:
        show_message(frame, "Mark Citation",
                     "Please place your cursor in a Writer document "
                     "and select the text you want to mark.")
        return

    if not selected_text.strip():
        show_message(frame, "Mark Citation",
                     "No text is selected.\n\n"
                     "Select the full citation text before choosing Mark Citation.")
        return

    # ── Show dialog ──────────────────────────────────────────────────────
    toa_data = D.load(doc)
    categories = D.all_categories(toa_data)

    result = DLG.show_mark_dialog(ctx, frame, selected_text, categories)
    if result is None:
        return  # user cancelled

    # ── Insert bookmark + apply style ────────────────────────────────────
    cit_id = D.new_id()
    bm_name = D.bookmark_name(cit_id)

    try:
        DOC.insert_citation_bookmark(doc, range0, bm_name)
    except Exception as exc:
        show_message(frame, "Mark Citation",
                     f"Could not insert citation mark.\n\n"
                     f"Note: citations cannot be marked inside headers, "
                     f"footers, or text boxes.\n\nDetail: {exc}")
        return

    # ── Save metadata ────────────────────────────────────────────────────
    toa_data["citations"][cit_id] = {
        "long_form":  result["long_form"],
        "short_form": result["short_form"],
        "category":   result["category"],
    }
    D.save(doc, toa_data)


def cmd_togglehighlights(ctx, frame):
    """
    Toggle the light-blue highlight on all citation marks on/off.

    Because all marks share the 'TOA Citation Mark' character style,
    changing the style's background property updates every mark at once.
    Turn highlights OFF before exporting to PDF.
    """
    from toa import document as DOC

    doc = frame.getController().getModel()
    state = DOC.toggle_highlights(doc)

    if state is None:
        show_message(frame, "Toggle Citation Highlights",
                     "No citation marks found in this document yet.")
    elif state:
        show_message(frame, "Citation Highlights: ON",
                     "Citation highlights are now visible.\n\n"
                     "Use 'Toggle Citation Highlights' again to hide them "
                     "before exporting to PDF.")
    else:
        show_message(frame, "Citation Highlights: OFF",
                     "Citation highlights are now hidden.\n\n"
                     "The marks are still present — they will reappear "
                     "when you toggle highlights back on.")


# ── Phase 3 ───────────────────────────────────────────────────────────────────

def cmd_editcitation(ctx, frame):
    """
    Edit the citation the cursor is currently inside.

    Flow:
      1. Find the TOA bookmark containing the view cursor.
      2. Load its existing metadata.
      3. Show the Mark Citation dialog pre-populated.
      4. Write the updated metadata back to document properties.
         (The bookmark itself stays — only the metadata changes.)
    """
    from toa import data as D, document as DOC, dialogs as DLG

    doc = frame.getController().getModel()

    bm_name = DOC.find_toa_bookmark_at_cursor(doc, frame, D.BOOKMARK_PREFIX)
    if bm_name is None:
        show_message(frame, "Edit Citation",
                     "Place your cursor inside a marked citation, then choose Edit Citation.")
        return

    cit_id = D.citation_id_from_bookmark(bm_name)
    toa_data = D.load(doc)

    if cit_id not in toa_data["citations"]:
        show_message(frame, "Edit Citation",
                     "This bookmark has no citation data.\n\n"
                     "It may be a leftover from a removed citation. "
                     "You can safely delete it via the Navigator.")
        return

    existing = toa_data["citations"][cit_id]
    categories = D.all_categories(toa_data)

    # Use the bookmarked text as the "selected text" preview in the dialog
    bm = doc.getBookmarks().getByName(bm_name)
    current_text = bm.getAnchor().getString()

    result = DLG.show_mark_dialog(ctx, frame, current_text, categories, initial=existing)
    if result is None:
        return  # user cancelled

    toa_data["citations"][cit_id] = {
        "long_form":  result["long_form"],
        "short_form": result["short_form"],
        "category":   result["category"],
    }
    D.save(doc, toa_data)


def cmd_removecitation(ctx, frame):
    """
    Remove the citation mark the cursor is currently inside.

    Clears the character style on the marked text, removes the bookmark,
    and deletes the citation metadata. The underlying text is preserved.
    """
    from toa import data as D, document as DOC
    from toa.ui import ask_yes_no

    doc = frame.getController().getModel()

    bm_name = DOC.find_toa_bookmark_at_cursor(doc, frame, D.BOOKMARK_PREFIX)
    if bm_name is None:
        show_message(frame, "Remove Citation",
                     "Place your cursor inside a marked citation, then choose Remove Citation.")
        return

    cit_id = D.citation_id_from_bookmark(bm_name)
    toa_data = D.load(doc)
    existing = toa_data["citations"].get(cit_id, {})
    long_form = existing.get("long_form", "(no data)")

    confirmed = ask_yes_no(
        frame,
        "Remove Citation",
        f"Remove the citation mark for:\n\n{long_form}\n\n"
        f"The text will remain in the document; only the mark will be removed."
    )
    if not confirmed:
        return

    DOC.remove_citation_bookmark(doc, bm_name)
    toa_data["citations"].pop(cit_id, None)
    D.save(doc, toa_data)


# ── Phase 4 ───────────────────────────────────────────────────────────────────

def cmd_buildtable(ctx, frame):
    """
    Scan all TOA bookmarks, collect page numbers, and insert a formatted
    Table of Authorities at the current cursor position.

    Citations marked more than once (short form cited on multiple pages)
    are deduplicated: all page numbers are collected and listed together.
    Citations appearing on more than N pages show "passim" instead (N is
    configurable in the build options dialog).

    If a table has already been inserted (detected via the TOA_TABLE bookmark),
    the user is warned and asked to confirm before inserting a new one.
    """
    from toa import data as D, table as T, dialogs as DLG
    from toa.ui import ask_yes_no

    doc = frame.getController().getModel()
    toa_data = D.load(doc)

    if not toa_data["citations"]:
        show_message(frame, "Build Table of Authorities",
                     "No citations are marked in this document yet.\n\n"
                     "Use TOA → Mark Citation to mark citations first.")
        return

    # ── Rebuild warning ───────────────────────────────────────────────────────
    bookmarks = doc.getBookmarks()
    if bookmarks.hasByName(T.TOA_TABLE_BOOKMARK):
        if not ask_yes_no(
            frame,
            "Table Already Exists",
            "A Table of Authorities has already been inserted in this document.\n\n"
            "Building again will insert a SECOND table at the current cursor position.\n\n"
            "To update, delete the old table manually first, then run Build Table again.\n\n"
            "Continue anyway and insert a new table?"
        ):
            return

    # ── Build options ─────────────────────────────────────────────────────────
    options = DLG.show_build_options_dialog(
        ctx, frame,
        passim_threshold=toa_data.get("passim_threshold", D.DEFAULT_PASSIM_THRESHOLD),
    )
    if options is None:
        return  # cancelled

    # Save updated threshold so it persists for next time
    toa_data["passim_threshold"] = options["passim_threshold"]
    D.save(doc, toa_data)

    success, error = T.generate(doc, frame, toa_data, passim_threshold=options["passim_threshold"])
    if not success:
        show_message(frame, "Build Table of Authorities", error)


# ── Phase 5 ───────────────────────────────────────────────────────────────────

def cmd_managecategories(ctx, frame):
    """
    Add, remove, and reorder custom citation categories.

    Default categories (Cases, Constitutional Provisions, Statutes,
    Regulations, Rules, Other Authorities) are fixed and always appear
    first. Custom categories (e.g. Treatises) are appended after them
    and can be freely managed here.
    """
    from toa import data as D, dialogs as DLG

    doc = frame.getController().getModel()
    toa_data = D.load(doc)

    result = DLG.show_manage_categories_dialog(
        ctx, frame,
        custom_categories=list(toa_data.get("custom_categories", [])),
        default_categories=D.DEFAULT_CATEGORIES,
    )

    if result is None:
        return  # cancelled

    toa_data["custom_categories"] = result
    D.save(doc, toa_data)


