"""动画系统：真奶蛙序列帧播放 + 程序化变换叠加（呼吸压缩/弹跳/摇摆），30fps。

素材结构：assets/<state>/frame_XX.png；meta.json 的 loop_start 表示
"前置段（如惊讶起势）播完一次后，从此帧开始循环"。
单帧姿态（idle/thinking/working/celebrate）由程序化变换驱动，多帧真动画
（attention/error）叠加轻微变换增强生命力。
"""
import json
import math
import os
import time

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QTransform

STATES = ["idle", "thinking", "working", "attention", "error", "celebrate"]

# 各状态参数：fps=序列帧播放率(0=静态姿态)；bob/period=弹跳幅度与周期；tilt=摆角；squash=压缩比
MOTION = {
    "idle":      dict(fps=0,  bob=4,  period=2600, tilt=1.5, squash=0.012),
    "thinking":  dict(fps=0,  bob=2,  period=1800, tilt=5.0, squash=0.010),
    "working":   dict(fps=0,  bob=6,  period=520,  tilt=0.0, squash=0.030),
    "attention": dict(fps=14, bob=2,  period=2000, tilt=0.0, squash=0.0),
    "error":     dict(fps=14, bob=2,  period=2400, tilt=0.0, squash=0.0),
    "celebrate": dict(fps=0,  bob=22, period=560,  tilt=4.0, squash=0.050),
}


class SpriteSet:
    def __init__(self, assets_dir=None):
        if assets_dir is None:
            from . import config
            assets_dir = str(config.ASSETS_DIR)
        self.dir = assets_dir
        self.frames = {}     # state -> [QPixmap]
        self.loop_start = {}  # state -> int
        self.confetti = []    # 庆祝纸屑帧

        for name in STATES:
            d = os.path.join(self.dir, name)
            pixmaps = []
            if os.path.isdir(d):
                for fn in sorted(os.listdir(d)):
                    if fn.startswith("frame_") and fn.lower().endswith(".png"):
                        pm = QPixmap(os.path.join(d, fn))
                        if not pm.isNull():
                            pixmaps.append(pm)
                meta = os.path.join(d, "meta.json")
                if os.path.exists(meta):
                    try:
                        self.loop_start[name] = int(json.loads(open(meta, encoding="utf-8").read()).get("loop_start", 0))
                    except (OSError, ValueError):
                        self.loop_start[name] = 0
            self.frames[name] = pixmaps

        cd = os.path.join(self.dir, "celebrate")
        if os.path.isdir(cd):
            for fn in sorted(os.listdir(cd)):
                if fn.startswith("confetti_") and fn.lower().endswith(".png"):
                    pm = QPixmap(os.path.join(cd, fn))
                    if not pm.isNull():
                        self.confetti.append(pm)

    def base_pixmap(self, state):
        pm_list = self.frames.get(state, [])
        return pm_list[0] if pm_list else None

    def tray_pixmap(self):
        return self.base_pixmap("idle")

    def scaled(self, scale):
        out = {}
        for name, pm_list in self.frames.items():
            out[name] = [
                pm.scaled(int(pm.width() * scale), int(pm.height() * scale),
                          Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
                for pm in pm_list
            ]
        return out


class TransformPlayer(QObject):
    """序列帧播放（fps/loop_start）+ 程序化变换（脚底基线）。"""

    frame_changed = Signal(QPixmap)

    def __init__(self, sprites: SpriteSet, scale=1.0, parent=None):
        super().__init__(parent)
        self.loop_start = dict(sprites.loop_start)
        self.frames = sprites.scaled(scale)
        self.state = "idle"
        self._t0 = time.monotonic()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(int(1000 / 30))
        self._emit()

    def set_state(self, name):
        if name == self.state or name not in self.frames:
            return
        self.state = name
        self._t0 = time.monotonic()  # 动画从头播
        self._emit()

    def _emit(self):
        pm = self._current_frame(0)
        if pm is not None:
            self.frame_changed.emit(pm)

    def _current_frame(self, elapsed_s):
        pm_list = [p for p in self.frames.get(self.state, []) if p is not None]
        if not pm_list:
            return None
        m = MOTION.get(self.state, MOTION["idle"])
        if m["fps"] <= 0 or len(pm_list) <= 1:
            return pm_list[0]
        start = self.loop_start.get(self.state, 0)
        total = len(pm_list)
        fi = elapsed_s * m["fps"]
        if fi < start:            # 前置段只播一次
            idx = int(fi)
        else:                     # 之后从 loop_start 循环
            span = max(1, total - start)
            idx = start + int(fi - start) % span
        return pm_list[min(idx, total - 1)]

    def _tick(self):
        now = time.monotonic()
        elapsed = now - self._t0
        pm = self._current_frame(elapsed)
        if pm is None:
            return
        m = MOTION.get(self.state, MOTION["idle"])
        ph = 2 * math.pi * (elapsed % (m["period"] / 1000.0)) / (m["period"] / 1000.0)

        bob = m["bob"] * (0.5 - 0.5 * math.cos(ph))
        angle = m["tilt"] * math.sin(ph)
        squash = m["squash"] * (0.5 - 0.5 * math.cos(2 * ph))
        sx, sy = 1.0 + squash, 1.0 - squash

        w, h = pm.width(), pm.height()
        ox, oy = w / 2.0, h - 4.0  # 脚底基线
        tr = QTransform()
        tr.translate(ox, oy)
        tr.rotate(angle)
        tr.scale(sx, sy)
        tr.translate(-ox, -oy)
        self.frame_changed.emit(pm.transformed(tr))
