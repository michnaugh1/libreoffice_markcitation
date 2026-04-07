#!/usr/bin/env bash
# Build toa.oxt (the installable LibreOffice extension).
# An .oxt file is simply a zip archive with a specific structure.
#
# Install via: Tools → Extension Manager → Add... → select toa.oxt
# After installing, restart LibreOffice and open a Writer document.
# You should see a "TOA" menu in the menu bar.
set -e
cd "$(dirname "$0")"

OUT="toa.oxt"
rm -f "$OUT"

zip -r "$OUT" \
  META-INF/ \
  pythonpath/ \
  icons/ \
  toa.py \
  Addons.xcu \
  ProtocolHandler.xcu \
  description.xml \
  description-en.txt \
  LICENSE

echo ""
echo "Built: $OUT"
echo ""
echo "Install:  Tools → Extension Manager → Add... → $(pwd)/$OUT"
echo "Restart LibreOffice, then open a Writer document to see the TOA menu."
