"""路径与配置。配置存放在 ~/.zcode-pet/，与项目目录解耦。

所有路径由 pathlib 构造：无 .. 分量、限制在用户目录的数据子目录内。
"""
import json
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = APP_DIR / "assets"

DATA_DIR = Path.home() / ".zcode-pet"
DEFAULT_EVENTS_FILE = DATA_DIR / "events.jsonl"
CONFIG_FILE = DATA_DIR / "pet_config.json"


def _resolve(path: Path, allowed_parent: Path) -> Path:
    """规范化并校验：解析真实路径、拒绝 .. 分量、限制在允许父目录内。"""
    rp = Path(path).resolve()
    parent = Path(allowed_parent).resolve()
    if ".." in rp.parts:
        raise ValueError("path traversal denied")
    if rp != parent and not rp.is_relative_to(parent):
        raise ValueError("path outside allowed dir")
    return rp


def events_file_path() -> Path:
    return _resolve(DEFAULT_EVENTS_FILE, DATA_DIR)


def config_file_path() -> Path:
    return _resolve(CONFIG_FILE, DATA_DIR)


DEFAULTS = {
    "events_file": str(DEFAULT_EVENTS_FILE),
    "scale": 1.2,               # 精灵缩放（素材画布 256px）
    "poll_ms": 250,             # 事件文件轮询间隔
    "error_ms": 8000,           # error 自动回落
    "celebrate_ms": 6000,       # celebrate 自动回落
    "work_timeout_ms": 180000,  # working/thinking 无事件超时回落（claudia-pet 同款 3 分钟）
    "notify_attention": True,   # 等审批时弹系统通知
    "notify_done": False,       # 任务完成弹系统通知（默认关，避免吵）
}


def load_config():
    cfg = dict(DEFAULTS)
    try:
        user = json.loads(config_file_path().read_text(encoding="utf-8"))
        if isinstance(user, dict):
            cfg.update({k: v for k, v in user.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    config_file_path().write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
