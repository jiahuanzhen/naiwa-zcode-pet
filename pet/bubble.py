"""对话气泡：淡入淡出、自动避让屏幕边缘。奶蛙台词按状态分组。"""
import random

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel

STYLE = """
QLabel {
    background: rgba(255, 255, 255, 242);
    color: #1f2d3d;
    font-size: 13px;
    font-family: "Microsoft YaHei UI";
    padding: 7px 12px;
    border: 1px solid rgba(120, 200, 90, 100);
    border-radius: 10px;
}
"""

CHATTER = [
    "呱～摸鱼也要记得喝水哦",
    "拍拍肚皮，效率满满",
    "有事随时叫蛙，蛙都在",
    "要不要起来走两步？",
    "盯——蛙在盯着 Zcode 干活呢",
    "今天也是奶黄味的一天～",
]

GREETINGS = [
    "奶蛙上线！今天也要元气满满～",
    "呱！主人来了，我在这儿呢～",
    "开工开工，奶蛙陪着你～",
]

THINKING = ["呱……让蛙想想 🤔", "唔，这个问题有点意思…", "正在检索蛙脑记忆…"]

# claudia-pet 的工具分类：关键词匹配工具名 → 干活台词
WORKING_CATEGORIES = [
    (["read", "grep", "glob", "list", "view", "cat", "pdf", "zotero", "doc"], "翻资料中…"),
    (["write", "edit", "patch", "replace", "create", "apply"], "码字中…"),
    (["web", "fetch", "browse", "search", "http"], "上网查资料…"),
    (["agent", "task", "subagent", "delegate"], "派活给小分队…"),
]
WORKING_TOOL_LINES = {
    "Bash": "敲命令中，呱呱作响…",
    "TodoWrite": "列个清单先…",
    "AskUserQuestion": "蛙有几个问题想问你…",
}
WORKING_DEFAULT = "认真干活中，勿扰呱！"

ATTENTION = ["呱！需要你点个允许 ✋", "停！等你确认呢！", "有件事非你不可，快看看！"]

ERROR = ["呱呱呱！翻车了…", "呜呜，出错了 (´;ω;`)", "蛙生无常，报错了…"]

DONE = ["搞定！捧肚大笑三秒钟 😂", "干完啦！奶蛙很满意～", "呱哈哈，完工！"]

STAR = ["大工程竣工！蛙蛙敬礼 🫡", "火力全开完工，太强了呱！"]


def working_line(tool):
    if not tool:
        return WORKING_DEFAULT
    if tool in WORKING_TOOL_LINES:
        return WORKING_TOOL_LINES[tool]
    low = tool.lower()
    for keys, line in WORKING_CATEGORIES:
        if any(k in low for k in keys):
            return line
    return WORKING_DEFAULT


def pick(lines):
    return random.choice(lines)


class Bubble(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet(STYLE)
        self.setWordWrap(True)
        self.setMaximumWidth(240)
        self.setVisible(False)
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(260)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def say(self, text, ms=3800):
        self.setText(text)
        self.adjustSize()
        self._place()
        self.setVisible(True)
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self._hide_timer.start(ms)

    def _fade_out(self):
        self._anim.stop()
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()
        QTimer.singleShot(280, lambda: self.setVisible(False)
                          if self._anim.state() != QPropertyAnimation.State.Running else None)

    def _place(self):
        """气泡挂在头顶右上方，越界时向左/向下收。"""
        if not self.parent():
            return
        pw, ph = self.parent().width(), self.parent().height()
        bw, bh = self.width(), self.height()
        x = pw - int(bw * 0.35)
        y = max(0, int(ph * 0.18) - bh)
        screen = getattr(self.parent(), "screen_geom", lambda: None)()
        if screen is not None:
            top_left = self.parent().mapToGlobal(QPoint(0, 0))
            if top_left.y() + y < screen.top() + 4:
                y = min(ph - bh - 8, int(ph * 0.3))
            if top_left.x() + x + bw > screen.right() - 4:
                x = -bw + 8
        self.move(x, y)
        self.raise_()
