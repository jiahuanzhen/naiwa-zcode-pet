"""从真奶蛙 idle 帧生成多尺寸 icon.ico。

用法: python tools/make_icon.py
"""
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "idle", "frame_00.png")
OUT = os.path.join(ROOT, "icon.ico")


def main():
    im = Image.open(SRC).convert("RGBA")
    # 裁到内容包围盒再做方形画布，图标里蛙更饱满
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    side = max(im.width, im.height)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    canvas.save(OUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("saved", OUT)


if __name__ == "__main__":
    sys.exit(main())
