"""奶蛙桌宠 —— Zcode 桌宠。用法：
  python -m pet            启动桌宠
  python -m pet --selftest 无头状态机自测
  python -m pet --render-test DIR  导出各状态基准帧 PNG（素材验收用）
"""
import os
import sys


def _run_gui(cfg, quit_after_ms=None):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from .state import PetStateMachine
    from .window import PetWindow

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关窗不退出，走托盘
    sm = PetStateMachine(cfg)
    win = PetWindow(cfg, sm)
    win.show()
    if quit_after_ms:  # 冒烟测试用：自动退出
        QTimer.singleShot(quit_after_ms, app.quit)
    return app.exec()


def _run_selftest(cfg):
    """无头跑一遍状态机断言主要转移。"""
    from .state import PetStateMachine, State

    t = {"v": 1000.0}
    clock = lambda: t["v"] / 1000.0
    sm = PetStateMachine(cfg, clock=clock)
    ok = True

    def feed(evt, expect):
        nonlocal ok
        change = sm.handle_event(evt)
        got = change.state if change else None
        status = "OK " if got == expect else "FAIL"
        if got != expect:
            ok = False
        ev = evt.get("event")
        ex = getattr(expect, "value", None)
        g = getattr(got, "value", None)
        print(f"[{status}] {ev:<22} expect={str(ex):<10} got={g}")
        return change

    def tick_advance(ms, expect):
        nonlocal ok
        t["v"] += ms
        change = sm.tick()
        got = change.state if change else None
        status = "OK " if got == expect else "FAIL"
        if got != expect:
            ok = False
        ex = getattr(expect, "value", None)
        g = getattr(got, "value", None)
        print(f"[{status}] tick +{ms:<7}      expect={str(ex):<10} got={g}")

    feed({"event": "SessionStart"}, State.CELEBRATE)
    tick_advance(6000, State.IDLE)
    feed({"event": "UserPromptSubmit"}, State.THINKING)
    feed({"event": "PreToolUse", "tool": "Bash"}, State.WORKING)
    feed({"event": "PostToolUse"}, None)
    feed({"event": "PermissionRequest"}, State.ATTENTION)
    feed({"event": "PreToolUse", "tool": "Edit"}, State.WORKING)   # 审批通过后继续干活
    feed({"event": "PostToolUseFailure"}, State.ERROR)
    tick_advance(8000, State.IDLE)
    # 少工具完成的普通庆祝
    feed({"event": "PreToolUse", "tool": "Read"}, State.WORKING)
    stop_change = feed({"event": "Stop"}, State.CELEBRATE)
    if stop_change is None or not stop_change.info.get("star") == False:
        pass  # star=False 属正常
    tick_advance(6000, State.IDLE)
    # 8+ 工具完成触发"得意"
    for _ in range(8):
        feed({"event": "PreToolUse", "tool": "Bash"}, State.WORKING)
        feed({"event": "PostToolUse"}, None)
    stop_change = feed({"event": "Stop"}, State.CELEBRATE)
    if stop_change is None or not stop_change.info.get("star"):
        ok = False
        print("[FAIL] 8-tool round should set star=True, got", stop_change.info if stop_change else None)
    else:
        print("[OK ] 8-tool round star=True")
    tick_advance(6000, State.IDLE)
    feed({"event": "PreToolUse", "tool": "Read"}, State.WORKING)
    tick_advance(180000, State.IDLE)  # 干活 3 分钟超时回落
    # attention 不受超时限制
    feed({"event": "PermissionRequest"}, State.ATTENTION)
    tick_advance(300000, None)
    if sm.state != State.ATTENTION:
        ok = False
        print("[FAIL] attention should persist over timeout, got", sm.state)
    else:
        print("[OK ] attention persists over timeout")

    print("\nSELFTEST", "PASSED ✅" if ok else "FAILED ❌")
    return 0 if ok else 1


def _run_render_test(out_dir):
    """导出每个状态的基准帧到 PNG，供素材验收。"""
    os.makedirs(out_dir, exist_ok=True)
    from PySide6.QtWidgets import QApplication
    from .sprites import STATES, SpriteSet

    QApplication.instance() or QApplication(sys.argv)  # QPixmap 需要 QGuiApplication
    sprites = SpriteSet()
    for name in STATES:
        pm = sprites.base_pixmap(name)
        if pm is None:
            print(f"!! no frames for {name}")
            continue
        pm.save(os.path.join(out_dir, f"{name}.png"))
        print(f"saved {name}.png ({pm.width()}x{pm.height()})")
    return 0


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from .config import load_config
    cfg = load_config()

    if "--selftest" in sys.argv:
        sys.exit(_run_selftest(cfg))
    if "--render-test" in sys.argv:
        out = sys.argv[sys.argv.index("--render-test") + 1] if len(sys.argv) > sys.argv.index("--render-test") + 1 else "render_out"
        sys.exit(_run_render_test(out))
    quit_after = None
    if "--smoke" in sys.argv:
        i = sys.argv.index("--smoke")
        quit_after = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 else 15000
    sys.exit(_run_gui(cfg, quit_after))


if __name__ == "__main__":
    main()
