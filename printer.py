import cups
import os
import re
import subprocess
import tempfile
from PIL import Image

PRINT_WIDTH = 576   # total printable dots (72 mm @ 8 dots/mm on 80 mm paper)
IMAGE_WIDTH = 512   # actual image width; padded to PRINT_WIDTH for centering
IMAGE_X_OFFSET = +6  # horizontal paste offset; decrease to shift image leftward

_ALIGN = {"left": b"\x00", "center": b"\x01", "right": b"\x02"}


def _parse_segments(line: str) -> list[dict]:
    result = []
    for part in re.split(r"(\*\*.*?\*\*|_.*?_)", line):
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            result.append({"text": part[2:-2], "bold": True, "underline": False})
        elif part.startswith("_") and part.endswith("_") and len(part) > 2:
            result.append({"text": part[1:-1], "bold": False, "underline": True})
        elif part:
            result.append({"text": part, "bold": False, "underline": False})
    return result


def build_escpos(text: str, align: str = "left") -> bytes:
    buf = bytearray()
    buf += b"\x1b\x40"                          # init
    buf += b"\x1b\x61" + _ALIGN.get(align, b"\x00")

    for line in text.split("\n"):
        for seg in _parse_segments(line):
            if seg["bold"]:
                buf += b"\x1b\x45\x01"
            if seg["underline"]:
                buf += b"\x1b\x2d\x01"
            buf += seg["text"].encode("cp437", errors="replace")
            if seg["bold"]:
                buf += b"\x1b\x45\x00"
            if seg["underline"]:
                buf += b"\x1b\x2d\x00"
        buf += b"\n"

    buf += b"\n\n\n\n"
    buf += b"\x1d\x56\x00"  # full cut
    return bytes(buf)


def build_image_escpos(image: Image.Image) -> bytes:
    w, h = image.size
    new_h = max(1, round(IMAGE_WIDTH * h / w))
    resized = image.convert("L").resize((IMAGE_WIDTH, new_h)).convert("1")

    # Paste onto a PRINT_WIDTH-wide white canvas to center horizontally.
    canvas = Image.new("1", (PRINT_WIDTH, new_h), 1)  # 1 = white in mode "1"
    canvas.paste(resized, ((PRINT_WIDTH - IMAGE_WIDTH) // 2 + IMAGE_X_OFFSET, 0))

    width_bytes = PRINT_WIDTH // 8
    pixels = canvas.tobytes()
    # PIL "1" stores 1=white, 0=black; ESC/POS raster wants 1=black.
    inverted = bytes(b ^ 0xFF for b in pixels)

    buf = bytearray()
    buf += b"\x1b\x40"  # init

    chunk_rows = 128  # keep each GS v 0 command small for printer buffers
    for y in range(0, new_h, chunk_rows):
        rows = min(chunk_rows, new_h - y)
        buf += b"\x1d\x76\x30\x00"
        buf += bytes([width_bytes & 0xFF, (width_bytes >> 8) & 0xFF])
        buf += bytes([rows & 0xFF, (rows >> 8) & 0xFF])
        buf += inverted[y * width_bytes : (y + rows) * width_bytes]

    buf += b"\n\n\n\n"
    buf += b"\x1d\x56\x00"  # full cut
    return bytes(buf)


class Printer:
    def __init__(self, printer_name: str):
        self.conn = cups.Connection()
        self.name = printer_name

    def print_text(self, text: str, align: str = "left") -> None:
        self._send_raw(build_escpos(text, align))

    def print_image(self, image: Image.Image) -> None:
        self._send_raw(build_image_escpos(image))

    def _send_raw(self, data: bytes) -> None:
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(data)
            path = f.name
        try:
            subprocess.run(["lp", "-d", self.name, "-o", "raw", path], check=True)
        finally:
            os.unlink(path)
