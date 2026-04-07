#!/usr/bin/env python3
"""
Generate PNG icons for the TOA extension using only Python stdlib.
Run once from the project root: python3 create_icons.py
"""
import struct
import zlib
import os

NAVY = (44,  62,  80)    # #2c3e50 — background
GOLD = (212, 175, 55)    # #d4af37 — "T" shape
WHITE = (255, 255, 255)  # highlights


def make_png(width, height, get_pixel):
    """Write a minimal RGB PNG file. get_pixel(x, y) → (R, G, B)."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)          # filter type: None
        for x in range(width):
            raw.extend(get_pixel(x, y))

    compressed = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack('>II', width, height) + bytes([8, 2, 0, 0, 0])
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', compressed)
            + chunk(b'IEND', b''))


def toa_pixel(x, y, size):
    """
    Draw a bold 'T' (for Table / TOA) in gold on a navy background.
    The crossbar occupies the top ~30 % of the canvas; the stem is centred.
    """
    margin     = max(1, size // 8)
    bar_top    = max(1, size // 6)
    bar_bottom = bar_top + max(2, size // 5)
    stem_half  = max(1, size // 7)
    cx         = size // 2

    # Crossbar
    if bar_top <= y < bar_bottom and margin <= x < size - margin:
        return GOLD
    # Stem
    if bar_bottom <= y < size - margin and cx - stem_half <= x <= cx + stem_half:
        return GOLD
    return NAVY


def write_icon(size, path):
    data = make_png(size, size, lambda x, y: toa_pixel(x, y, size))
    with open(path, 'wb') as f:
        f.write(data)
    print(f"  {path}  ({size}×{size} px)")


if __name__ == "__main__":
    os.makedirs("icons", exist_ok=True)
    print("Generating icons...")
    write_icon(16, "icons/toa_16.png")
    write_icon(26, "icons/toa_26.png")
    write_icon(48, "icons/toa_48.png")   # used in Extension Manager
    print("Done.")
