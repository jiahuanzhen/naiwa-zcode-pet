"""ZCode hooks 写入端：hook 触发时把事件追加到 ~/.zcode-pet/events.jsonl。

由 ZCode hooks 调用（stdin 可能带 JSON payload），绝不能抛错影响会话。
安装位置：C:/Users/lenovo/.zcode-pet/zcode_pet_hook.py（ASCII 路径）
"""
import json
import sys
import time
from pathlib import Path

DATA_DIR = Path.home() / ".zcode-pet"
EVENTS_FILE = DATA_DIR / "events.jsonl"


def main():
    try:
        event = sys.argv[1] if len(sys.argv) > 1 else "Unknown"
        payload = {}
        try:
            raw = "" if sys.stdin.isatty() else sys.stdin.read()
            if raw.strip():
                payload = json.loads(raw)
        except (ValueError, OSError):
            payload = {}

        tool = ""
        for key in ("tool_name", "tool", "ToolName"):
            v = payload.get(key)
            if isinstance(v, str):
                tool = v
                break
        session = payload.get("session_id") or payload.get("sessionId") or ""

        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            rec = {"ts": time.time(), "event": event, "tool": tool, "session": session}
            with EVENTS_FILE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except OSError:
            pass
    except Exception:
        pass  # 桌宠永远不能影响主会话
    sys.exit(0)


if __name__ == "__main__":
    main()
