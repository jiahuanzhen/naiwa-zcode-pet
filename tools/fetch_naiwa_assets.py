"""从 NaiWaChatPet (github.com/SbongeBobybl/NaiWaChatPet) 抓取真奶蛙序列帧，
归一化为桌宠素材 assets/<state>/frame_XX.png（+meta.json 记录循环起点）。

安全约束（Mimosa）：仅 https；域名白名单；解析 IP 必须为全局地址（拒绝私网/环回/链路本地）；
重定向逐跳校验；失败重试 3 次。
原始帧缓存于 assets_raw/<action>/，重复运行不重新下载。

用法: python tools/fetch_naiwa_assets.py [state ...]
"""
import ipaddress
import json
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "assets_raw"
OUT = ROOT / "assets"

ALLOWED_HOSTS = {"raw.githubusercontent.com", "api.github.com"}
UA = {"User-Agent": "naiwa-pet-assets/1.0"}
CANVAS = 300
BASELINE = 6


def _validate_url(url):
    """https + 域名白名单 + 解析出的 IP 必须是全局地址。"""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https":
        raise ValueError("only https allowed: %s" % url)
    host = parts.hostname or ""
    if host not in ALLOWED_HOSTS:
        raise ValueError("host not allowed: %s" % host)
    for info in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP):
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ValueError("non-global IP %s for %s" % (ip, host))
    return parts


class _GuardedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_url(newurl)  # 重定向逐跳校验
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_GuardedRedirect)


def _open(url):
    """带校验与重试的 GET，返回 bytes。"""
    _validate_url(url)
    last = None
    for attempt in range(3):
        req = urllib.request.Request(url, headers=UA)
        try:
            with _OPENER.open(req, timeout=60) as r:
                return r.read()
        except (OSError, urllib.error.URLError) as e:
            last = e
            time.sleep(1 + attempt)
    raise last


# 状态 -> [(action, [帧号] or None=全部)]
STATE_MAP = {
    "idle":      [("smile", [0])],
    "thinking":  [("ponder", [0])],
    "working":   [("focused", [0])],
    "attention": [("surprised_in", None), ("surprised", None)],
    "error":     [("sad_in", None), ("sad", None)],
    "celebrate": [("celebrate", [0])],
}
# 备用单帧姿态（放 assets_extra，供托盘/未来切换）
EXTRA = ["dizzy", "crying", "sleepy", "bored", "excited", "greet", "love", "proud", "smug", "worried", "shocked", "cheer"]


def fetch_frame(action, idx):
    d = RAW / action
    d.mkdir(parents=True, exist_ok=True)
    p = d / ("%04d.png" % idx)
    if p.exists() and p.stat().st_size > 0:
        return p
    p.write_bytes(_open("%s/%s/%04d.png" % (BASE_URL, action, idx)))
    return p


BASE_URL = "https://raw.githubusercontent.com/SbongeBobybl/NaiWaChatPet/main/Source/NaiWaChatPet/animations"


def frame_count(action):
    cache = RAW / ("_count_%s.json" % action)
    if cache.exists():
        return json.loads(cache.read_text())["n"]
    api = ("https://api.github.com/repos/SbongeBobybl/NaiWaChatPet/contents/"
           "Source/NaiWaChatPet/animations/%s" % action)
    items = json.loads(_open(api).decode("utf-8"))
    n = sum(1 for it in items if isinstance(it, dict) and str(it.get("name", "")).endswith(".png"))
    RAW.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"n": n}))
    return n


def normalize(paths, out_dir):
    from PIL import Image
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("frame_*.png"):
        old.unlink()
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGBA")
        scale = (CANVAS - 24) / max(im.width, im.height)
        w, h = max(1, round(im.width * scale)), max(1, round(im.height * scale))
        im = im.resize((w, h), Image.LANCZOS)
        canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
        canvas.paste(im, ((CANVAS - w) // 2, CANVAS - BASELINE - h))
        canvas.save(out_dir / ("frame_%02d.png" % i))
    return len(paths)


def main():
    only = set(sys.argv[1:]) or None  # 可传状态名只重建部分
    summary = {}
    for state, sets in STATE_MAP.items():
        if only and state not in only:
            continue
        paths, loop_start = [], 0
        for action, idxs in sets:
            if idxs is None:
                idxs = list(range(frame_count(action)))
            if paths and len(idxs) > 1:
                loop_start = len(paths)  # in 段播完一次后，从这里循环
            for i in idxs:
                paths.append(fetch_frame(action, i))
        n = normalize(paths, OUT / state)
        (OUT / state / "meta.json").write_text(json.dumps({"loop_start": loop_start}), encoding="utf-8")
        summary[state] = (n, loop_start)
        print("%-10s %3d frames (loop_start=%d)" % (state, n, loop_start))

    if not only:
        for action in EXTRA:
            try:
                p = fetch_frame(action, 0)
                from PIL import Image
                im = Image.open(p).convert("RGBA")
                scale = (CANVAS - 24) / max(im.width, im.height)
                im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
                canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
                canvas.paste(im, ((CANVAS - im.width) // 2, CANVAS - BASELINE - im.height))
                d = ROOT / "assets_extra" / action
                d.mkdir(parents=True, exist_ok=True)
                canvas.save(d / "frame_00.png")
            except Exception as e:
                print("extra %-9s skipped: %s" % (action, e))
    print("done")


if __name__ == "__main__":
    sys.exit(main())
