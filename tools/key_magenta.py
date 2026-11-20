"""品红背景抠图管线：AI 生图 → 透明 PNG 精灵。

步骤：
1. 采样四角中位色作为背景参考色
2. 与参考色相近的像素做边界洪泛填充（只抠与边缘连通的背景，不伤体内同色区）
3. 去品红溢色（spill）：边缘处 B 通道被 R/G 压制
4. 右下角水印矩形强制置为背景；保留最大连通前景
5. alpha 轻腐蚀+羽化，裁剪 bbox，落到统一画布（脚底贴基线，居中）

用法: python tools/key_magenta.py IN OUT [CANVAS] [FILL_MARGIN]
"""
import sys

import numpy as np
from PIL import Image, ImageFilter


def ref_color(arr):
    corners = [arr[:40, :40].reshape(-1, 3), arr[:40, -40:].reshape(-1, 3),
               arr[-40:, :40].reshape(-1, 3), arr[-40:, -40:].reshape(-1, 3)]
    stack = np.concatenate(corners)
    return np.median(stack, axis=0)


def key(path_in, path_out, canvas=256, fill_margin=26):
    im = Image.open(path_in).convert("RGB")
    arr = np.asarray(im).astype(np.float32)
    h, w, _ = arr.shape
    ref = ref_color(arr)

    # 全局品红判定：与背景参考色距离近，且 G 远低于 R/B（奶蛙身上没有这种色度，阴影暗化的品红也满足）
    dist = np.sqrt(((arr - ref) ** 2).sum(axis=2))
    r_, g_, b_ = arr[..., 0], arr[..., 1], arr[..., 2]
    chroma_bg = (g_ < r_ * 0.65) & (g_ < b_ * 0.85)
    bg = (dist < 120) & chroma_bg
    # 深色接触阴影（暗品红）：距离不够近但色度仍是"品红家族"
    bg |= (g_ < r_ * 0.5) & (b_ > g_ * 1.8)

    # 右下角水印强制清除（Z.AI生成 字样）
    wm = np.zeros_like(bg)
    wm[int(h*0.86):, int(w*0.62):] = True
    bg |= wm

    alpha = np.where(bg, 0, 255).astype(np.uint8)

    # 最大连通前景：过滤零散水印残块
    a_bin = alpha > 0
    labels = np.zeros((h, w), dtype=np.int32)
    cur = 0
    sizes = {}
    for sy in range(h):
        for sx in range(w):
            if a_bin[sy, sx] and labels[sy, sx] == 0:
                cur += 1
                comp = [(sy, sx)]
                labels[sy, sx] = cur
                n = 0
                while comp:
                    y, x = comp.pop()
                    n += 1
                    for ny, nx in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
                        if 0 <= ny < h and 0 <= nx < w and a_bin[ny, nx] and labels[ny, nx] == 0:
                            labels[ny, nx] = cur
                            comp.append((ny, nx))
                sizes[cur] = n
    if sizes:
        keep = max(sizes, key=sizes.get)
        alpha[labels != keep] = 0

    # 去品红溢色：非背景像素 B 通道压到 R/G 较大值以下
    fg = alpha > 0
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    despill_b = np.minimum(b, np.maximum(r, g) * 0.92)
    arr[..., 2] = np.where(fg, despill_b, b)
    r2 = np.minimum(r, np.maximum(g, arr[..., 2]) * 1.06)
    arr[..., 0] = np.where(fg, r2, r)

    out = Image.fromarray(np.dstack([arr.astype(np.uint8), alpha]), "RGBA")

    # 轻腐蚀 + 羽化，去边缘杂色
    a = Image.fromarray(alpha)
    a = a.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.0))
    out.putalpha(a)

    # 裁剪 bbox，脚底贴基线居中
    bbox = out.getbbox()
    if bbox:
        out = out.crop(bbox)
    cw, ch = canvas, canvas
    scale = min((cw - 12) / out.width, (ch - 20) / out.height, 1.0)
    out = out.resize((max(1, int(out.width * scale)), max(1, int(out.height * scale))), Image.LANCZOS)
    canvas_im = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    x = (cw - out.width) // 2
    y = ch - 6 - out.height  # 脚底留 6px 基线
    canvas_im.paste(out, (x, y))
    canvas_im.save(path_out)
    print(f"{path_in} -> {path_out}  ({out.width}x{out.height} @ canvas {cw}x{ch})")


if __name__ == "__main__":
    key(sys.argv[1], sys.argv[2],
        int(sys.argv[3]) if len(sys.argv) > 3 else 256,
        float(sys.argv[4]) if len(sys.argv) > 4 else 26)
