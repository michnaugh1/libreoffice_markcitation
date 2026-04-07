# LibreOffice Mark Citation

A LibreOffice Writer extension for attorneys that replicates the Table of Authorities workflow found in Microsoft Word. Mark citations throughout your brief, then generate a properly formatted Table of Authorities with dot leaders, page numbers, and *passim* notation — all without leaving LibreOffice.

## Features

- **Mark citations** with long form, short form, and category metadata
- **Edit or remove** existing citation marks
- **Toggle highlight visibility** — light-blue highlights show marks during drafting; hide them before exporting to PDF
- **Build Table of Authorities** — inserts a formatted table at the cursor with dot leaders and page numbers, grouped by category
- **Passim** — citations appearing on more pages than a configurable threshold (default: 5) show *passim* instead of individual page numbers
- **Rebuild warning** — alerts you if a table has already been inserted so you don't accidentally create a duplicate
- **Manage custom categories** — the six standard legal categories are built in; add your own (e.g., *Treatises*, *Secondary Sources*) per document

### Standard categories

1. Cases
2. Constitutional Provisions
3. Statutes
4. Regulations
5. Rules
6. Other Authorities

## Requirements

- LibreOffice 4.0 or later (developed and tested on LibreOffice 26.2)
- Linux, macOS, or Windows

## Installation

1. Download `toa.oxt` from the [Releases](https://github.com/michnaugh1/libreoffice_markcitation/releases) page.
2. In LibreOffice, go to **Tools → Extension Manager → Add…**
3. Select `toa.oxt` and click **Open**.
4. Restart LibreOffice.

A **TOA** menu will appear in the menu bar whenever a Writer document is open.

## Usage

### Mark a citation

1. Select the full citation text in your document.
2. Choose **TOA → Mark Citation…**
3. Fill in the Long Form, Short Form, and Category fields, then click **OK**.

The selected text receives a light-blue highlight indicating it is marked.

### Edit a citation

1. Place your cursor anywhere inside a marked citation.
2. Choose **TOA → Edit Citation…**
3. Update the fields and click **OK**.

### Remove a citation

1. Place your cursor anywhere inside a marked citation.
2. Choose **TOA → Remove Citation**.
3. Confirm the removal. The underlying text is preserved; only the mark is removed.

### Build the Table of Authorities

1. Position your cursor where you want the table inserted (typically after a page break at the start of the TOA section).
2. Choose **TOA → Build Table of Authorities**.
3. Set the *passim* threshold in the options dialog and click **OK**.

The table is inserted immediately, grouped by category, with dot leaders and page numbers.

### Toggle highlights

Choose **TOA → Toggle Citation Highlights** to show or hide the light-blue marks. Turn them off before exporting to PDF for a clean final document.

### Manage custom categories

Choose **TOA → Manage Categories…** to add, remove, or reorder custom categories. Custom categories are saved in the document and appear after the six standard ones in the TOA.

## Building from source

```bash
git clone https://github.com/michnaugh1/libreoffice_markcitation.git
cd libreoffice_markcitation
python3 create_icons.py   # only needed if icons/ are missing
bash build.sh
```

This produces `toa.oxt` in the project root.

## Data storage

Citation metadata (long form, short form, category, passim threshold) is stored as a JSON blob in the document's user-defined properties under the key `TOA_DATA`. It travels with the `.odt` file automatically — no sidecar files or external database required.

## License

MIT — see [LICENSE](LICENSE).
