#!/usr/bin/env python3
"""Generate a simple AppIcon for the XHS Assistant .app bundle.
Run on macOS — uses native sips + iconutil."""

import subprocess
import os
import shutil
import tempfile

SIZES = [16, 32, 64, 128, 256, 512, 1024]


def main():
    iconset = tempfile.mkdtemp(suffix=".iconset")
    os.makedirs(iconset, exist_ok=True)

    # Create a simple SVG with pink gradient + 📕 emoji-like circle
    svg_path = os.path.join(iconset, "icon.svg")
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#ff6b6b"/>
      <stop offset="100%" style="stop-color:#ff8e8e"/>
    </linearGradient>
  </defs>
  <rect width="1024" height="1024" rx="200" fill="url(#g)"/>
  <text x="512" y="640" text-anchor="middle" font-size="520" font-family="serif">📕</text>
</svg>"""
    with open(svg_path, "w") as f:
        f.write(svg)

    # Need rsvg-convert or similar to convert SVG to PNG.
    # Fallback: use a solid pink square with Python Pillow if available.
    try:
        from PIL import Image, ImageDraw, ImageFont
        has_pillow = True
    except ImportError:
        has_pillow = False

    if has_pillow:
        _generate_with_pillow(iconset)
    else:
        # Try rsvg-convert (from librsvg)
        try:
            for size in SIZES:
                name = f"icon_{size}x{size}.png"
                subprocess.run(
                    ["rsvg-convert", "-w", str(size), "-h", str(size),
                     "-o", os.path.join(iconset, name), svg_path],
                    check=True,
                )
                if size <= 512:
                    name2x = f"icon_{size}x{size}@2x.png"
                    subprocess.run(
                        ["rsvg-convert", "-w", str(size * 2), "-h", str(size * 2),
                         "-o", os.path.join(iconset, name2x), svg_path],
                        check=True,
                    )
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("⚠️  rsvg-convert not found. Install with: brew install librsvg")
            print("    Using placeholder solid-color icon instead...")
            _generate_solid(iconset)

    # Create .icns
    icns_path = os.path.join(os.path.dirname(iconset), "AppIcon.icns")
    subprocess.run(["iconutil", "-c", "icns", "-o", icns_path, iconset], check=True)
    print(f"✅ Icon generated: {icns_path}")
    shutil.rmtree(iconset)


def _generate_with_pillow(iconset):
    from PIL import Image, ImageDraw, ImageFont
    for size in SIZES:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Rounded rect
        draw.rounded_rectangle([0, 0, size, size], radius=size // 5, fill="#ff6b6b")
        # Simple text
        try:
            fnt = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", size // 2)
        except (IOError, OSError):
            fnt = ImageFont.load_default()
        draw.text((size // 2, size // 2), "📕", fill="white", anchor="mm", font=fnt)
        name = f"icon_{size}x{size}.png"
        img.save(os.path.join(iconset, name))
        if size <= 512:
            img2 = img.resize((size * 2, size * 2), Image.LANCZOS)
            name2x = f"icon_{size}x{size}@2x.png"
            img2.save(os.path.join(iconset, name2x))


def _generate_solid(iconset):
    """Fallback: solid pink PNGs with no icon."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("❌ Pillow not available. Cannot generate icon.")
        print("   Install: pip3 install Pillow")
        return

    for size in SIZES:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, size, size], radius=size // 5, fill="#ff6b6b")
        name = f"icon_{size}x{size}.png"
        img.save(os.path.join(iconset, name))
        if size <= 512:
            img2 = img.resize((size * 2, size * 2), Image.LANCZOS)
            name2x = f"icon_{size}x{size}@2x.png"
            img2.save(os.path.join(iconset, name2x))


if __name__ == "__main__":
    main()
