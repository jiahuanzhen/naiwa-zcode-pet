"""庆祝纸屑叠加帧生成：assets/celebrate/confetti_00..03.png（透明背景）。

用法: python tools/generate_confetti.py
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "celebrate")
SIZE = 256
SS = 3  # 超采样

COLORS = [(255, 99, 132, 255), (255, 205, 86, 255), (75, 192, 192, 255),
          (153, 102, 255, 255), (255, 159, 64, 255), (54, 162, 235, 255),
          (130, 220, 90, 255)]


def star(d, x, y, r, color):
    pts = []
    for k in range(8):
        ang = math.pi / 4 * k - math.pi / 2
        rr = r if k % 2 == 0 else r * 0.4
        pts.append((x + rr * math.cos(ang), y + rr * math.sin(ang)))
    d.polygon(pts, fill=color)


def main():
    os.makedirs(OUT, exist_ok=True)
    for i in range(4):
        rng = random.Random(100 + i)
        img = Image.new("RGBA", (SIZE * SS, SIZE * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # 上半屏撒纸屑，避开蛙身中下部
        for _ in range(26):
            x, y = rng.randint(8, SIZE - 8), rng.randint(6, int(SIZE * 0.45))
            color = rng.choice(COLORS)
            kind = rng.random()
            s = SS
            if kind < 0.4:
                d.ellipse([x * s - 5 * s, y * s - 5 * s, x * s + 5 * s, y * s + 5 * s], fill=color)
            elif kind < 0.75:
                star(d, x * s, y * s, 6 * s, color)
            else:
                w, h2 = rng.randint(4, 7), rng.randint(7, 11)
                ang = rng.uniform(0, math.pi)
                dx, dy = w * s * math.cos(ang), w * s * math.sin(ang)
                d.polygon([(x * s - dx, y * s - dy), (x * s + dx, y * s + dy),
                           (x * s + dx - 2 * s, y * s + dy + 2 * s),
                           (x * s - dx - 2 * s, y * s - dy + 2 * s)], fill=color)
        img = img.resize((SIZE, SIZE), Image.LANCZOS)
        img.save(os.path.join(OUT, "confetti_%02d.png" % i))
        print("saved", os.path.join(OUT, "confetti_%02d.png" % i))


if __name__ == "__main__":
    sys.exit(main())
