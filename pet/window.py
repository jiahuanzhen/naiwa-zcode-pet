"""奶蛙主窗口：透明无边框置顶、拖拽、托盘菜单（含系统通知）、状态应用。"""
import json
import random
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QTimer, Qt
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QIcon
from PySide6.QtWidgets import QLabel, QMenu, QApplication, QSystemTrayIcon, QWidget

from . import config
from . import bubble as bubble_text
from .bubble import Bubble
from .sprites import SpriteSet, TransformPlayer
from .state import State

DRAG_THRESHOLD = 5


def log(msg):
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        f = config.DATA_DIR / "pet.log"
        with f.open("a", encoding="utf-8") as fh:
            fh.write("%s %s\n" % (datetime.now().isoformat(timespec="seconds"), msg))
    except OSError:
        pass


def _save_json(path: Path, obj):
    """写入 JSON：路径规范化校验（禁止 .. 且限定在数据目录内）。"""
    rp = Path(path).resolve()
    parent = config.DATA_DIR.resolve()
    if ".." in rp.parts or not (rp == parent or rp.is_relative_to(parent)):
        raise ValueError("path outside data dir")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _load_json(path: Path):
    try:
        return json.loads(Path(path).resolve().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


class PetWindow(QWidget):
    def __init__(self, cfg, sm):
        super().__init__(None)
        self.cfg = cfg
        self.sm = sm
        self.setWindowTitle("奶蛙桌宠 · Zcode")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # 不进任务栏
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.sprites = SpriteSet(config.ASSETS_DIR)
        self.sprite_label = QLabel(self)
        self.sprite_label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        self.player = TransformPlayer(self.sprites, scale=cfg["scale"], parent=self)
        self.player.frame_changed.connect(self.sprite_label.setPixmap)

        # 庆祝纸屑叠加层
        self.confetti_label = QLabel(self)
        self.confetti_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.confetti_label.hide()
        self._confetti_idx = 0
        self._confetti_timer = QTimer(self)
        self._confetti_timer.timeout.connect(self._next_confetti)

        self.bubble = Bubble(self)

        first = self.sprites.tray_pixmap()
        if first is not None:
            self.resize(int(first.width() * cfg["scale"]), int(first.height() * cfg["scale"]))

        self._drag_offset = None
        self._dragging = False
        self._press_pos = None
        self._bounce = None

        self._build_tray()
        self._restore_position()

        self._file_pos = 0
        self._event_seen = False  # 启动时忽略历史事件
        self._poll = QTimer(self)
        self._poll.timeout.connect(self._poll_events)
        self._poll.start(cfg["poll_ms"])
        self._tick = QTimer(self)
        self._tick.timeout.connect(self._tick_state)
        self._tick.start(500)

        self._chat = QTimer(self)
        self._chat.timeout.connect(self._idle_chatter)
        self._chat.start(random.randint(120, 200) * 1000)

        self.player.set_state(State.IDLE.value)
        self.player._emit()

    # ---------- 布局与屏幕 ----------
    def resizeEvent(self, event):
        self.sprite_label.setGeometry(self.rect())
        self.confetti_label.setGeometry(self.rect())
        super().resizeEvent(event)

    def screen_geom(self):
        screen = self.screen() or QGuiApplication.primaryScreen()
        return screen.availableGeometry() if screen else None

    def _restore_position(self):
        geom = self.screen_geom()
        if geom is None:
            return
        pos = _load_json(config.DATA_DIR / "pet_position.json")
        if pos and isinstance(pos, dict):
            x, y = int(pos.get("x", 0)), int(pos.get("y", 0))
        else:
            x = geom.right() - self.width() - 24
            y = geom.bottom() - self.height() - 8
        x = max(geom.left(), min(x, geom.right() - self.width()))
        y = max(geom.top(), min(y, geom.bottom() - self.height()))
        self.move(x, y)

    # ---------- 托盘 ----------
    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        pm = self.sprites.tray_pixmap()
        if pm is not None:
            self.tray.setIcon(QIcon(pm.scaled(64, 64)))
        menu = QMenu()
        act_show = QAction("显示/隐藏", menu)
        act_show.triggered.connect(self.toggle_visible)
        menu.addAction(act_show)

        test_menu = menu.addMenu("手动测试状态")
        group = QActionGroup(test_menu)
        label = {"idle": "待机", "thinking": "思考", "working": "干活",
                 "attention": "等审批", "error": "出错", "celebrate": "庆祝"}
        for s in State:
            a = QAction(label.get(s.value, s.value), test_menu)
            a.setCheckable(True)
            a.triggered.connect(lambda checked, st=s: self.apply_change(self.sm.force(st)))
            group.addAction(a)
            test_menu.addAction(a)

        menu.addSeparator()
        act_quit = QAction("退出", menu)
        act_quit.triggered.connect(self.quit_app)
        menu.addAction(act_quit)

        self.tray.setContextMenu(menu)
        self.tray.setToolTip("奶蛙桌宠 · 点窗口戳一戳")
        self.tray.activated.connect(
            lambda reason: self.toggle_visible()
            if reason == QSystemTrayIcon.ActivationReason.Trigger else None
        )
        self.tray.show()

    def _notify(self, title, body, ms=4000):
        if self.tray.supportsMessages():
            self.tray.showMessage(title, body, QSystemTrayIcon.MessageIcon.Information, ms)

    def toggle_visible(self):
        self.setVisible(not self.isVisible())

    def quit_app(self):
        self._save_position()
        self.tray.hide()
        QApplication.quit()

    # ---------- 鼠标：拖拽 / 点击 / 双击 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press_pos = e.globalPosition().toPoint()
            self._drag_offset = self._press_pos - self.frameGeometry().topLeft()
            self._dragging = False

    def mouseMoveEvent(self, e):
        if self._drag_offset is None:
            return
        delta = e.globalPosition().toPoint() - self._press_pos
        if not self._dragging and delta.manhattanLength() > DRAG_THRESHOLD:
            self._dragging = True
        if self._dragging:
            self.move(e.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        was_drag = self._dragging
        self._drag_offset = None
        self._dragging = False
        if not was_drag:
            self.bubble.say(bubble_text.pick(bubble_text.CHATTER))
            self._bounce_once()

    def mouseDoubleClickEvent(self, e):
        self.apply_change(self.sm.force(State.CELEBRATE))

    def _bounce_once(self):
        start = self.pos()
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(320)
        anim.setEasingCurve(QEasingCurve.Type.OutBounce)
        anim.setStartValue(start)
        anim.setKeyValueAt(0.4, start + QPoint(0, -18))
        anim.setEndValue(start)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._bounce = anim  # 防 GC

    # ---------- 状态应用 ----------
    def apply_change(self, change):
        if change is None:
            return
        self.player.set_state(change.state.value)
        info = change.info
        s = change.state
        if s == State.CELEBRATE:
            lines = bubble_text.GREETINGS if info.get("greet") else (
                bubble_text.STAR if info.get("star") else bubble_text.DONE)
            self.bubble.say(bubble_text.pick(lines))
            self._start_confetti()
            if self.cfg.get("notify_done") and not info.get("greet"):
                self._notify("奶蛙桌宠", "任务完成 🎉")
        elif s == State.THINKING:
            self.bubble.say(bubble_text.pick(bubble_text.THINKING))
            self._stop_confetti()
        elif s == State.WORKING:
            self.bubble.say(bubble_text.working_line(info.get("tool")), 3000)
            self._stop_confetti()
        elif s == State.ATTENTION:
            self.bubble.say(bubble_text.pick(bubble_text.ATTENTION), 0)  # 粘滞，不自动消失
            self._stop_confetti()
            self._bounce_once()
            self.raise_()
            if self.cfg.get("notify_attention"):
                self._notify("奶蛙桌宠", "需要你审批/确认一个操作 ✋")
        elif s == State.ERROR:
            self.bubble.say(bubble_text.pick(bubble_text.ERROR), 5000)
            self._stop_confetti()
            self._bounce_once()
        elif s == State.IDLE:
            self.bubble.say("忙完啦，蛙先歇会儿～", 2500)
            self._stop_confetti()
        log("state -> %s %s" % (s.value, info))

    # ---------- 纸屑 ----------
    def _start_confetti(self):
        if not self.sprites.confetti:
            return
        self._confetti_idx = 0
        self._next_confetti()
        self._confetti_timer.start(140)
        self.confetti_label.raise_()

    def _stop_confetti(self):
        self._confetti_timer.stop()
        self.confetti_label.hide()

    def _next_confetti(self):
        if not self.sprites.confetti:
            self._confetti_timer.stop()
            return
        pm = self.sprites.confetti[self._confetti_idx % len(self.sprites.confetti)]
        self._confetti_idx += 1
        self.confetti_label.setPixmap(pm)
        self.confetti_label.show()

    # ---------- 事件流 ----------
    def _poll_events(self):
        path = config.events_file_path()
        try:
            if not path.exists():
                self._event_seen = True
                return
            with path.open("r", encoding="utf-8", errors="replace") as f:
                if not self._event_seen:
                    f.seek(0, 2)  # 启动时忽略历史，只看新事件
                    self._file_pos = f.tell()
                    self._event_seen = True
                    return
                f.seek(self._file_pos)
                new = f.read()
                self._file_pos = f.tell()
        except OSError:
            return
        for line in new.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except ValueError:
                continue
            self.apply_change(self.sm.handle_event(evt))

    def _tick_state(self):
        self.apply_change(self.sm.tick())

    def _idle_chatter(self):
        if self.sm.state == State.IDLE and self.isVisible():
            self.bubble.say(bubble_text.pick(bubble_text.CHATTER))
        self._chat.start(random.randint(120, 200) * 1000)

    def _save_position(self):
        try:
            _save_json(config.DATA_DIR / "pet_position.json", {"x": self.x(), "y": self.y()})
        except (OSError, ValueError):
            pass

    def closeEvent(self, e):
        self._save_position()
        super().closeEvent(e)
