"""状态机：把 ZCode hooks 事件流归纳为桌宠状态。

优先级/粘滞规则参考 dsh-pet-indesktop 与 claudia-pet：
attention（等你审批）> error > working/thinking > idle，celebrate/error 播完自动回落；
干活无消息 3 分钟自动回待机（attention 不受限）；一轮内工具调用 ≥8 次的完成触发"得意"台词。
"""
import time
from enum import Enum

SESSION_START = "SessionStart"
PROMPT_SUBMIT = "UserPromptSubmit"
PRE_TOOL_USE = "PreToolUse"
POST_TOOL_USE = "PostToolUse"
PERMISSION_REQUEST = "PermissionRequest"
POST_TOOL_FAILURE = "PostToolUseFailure"
STOP = "Stop"


class State(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    ATTENTION = "attention"
    ERROR = "error"
    CELEBRATE = "celebrate"


class Transition:
    def __init__(self, state, info=None):
        self.state = state
        self.info = info or {}


class PetStateMachine:
    def __init__(self, cfg, clock=time.monotonic):
        self.cfg = cfg
        self.now = clock
        self.state = State.IDLE
        self.tool = ""
        self.tool_count = 0  # 本轮（自上次 Stop/SessionStart 起）工具调用数，用于"得意"判定
        self._state_since = self.now()

    # ---- 事件入口 ----
    def handle_event(self, evt: dict):
        name = evt.get("event", "")
        self.tool = evt.get("tool") or self.tool
        t = self.now()

        if name == SESSION_START:
            self.tool_count = 0
            return self._go(State.CELEBRATE, {"greet": True})
        if name == PROMPT_SUBMIT:
            return self._go(State.THINKING)
        if name == PRE_TOOL_USE:
            self.tool_count += 1
            return self._go(State.WORKING, {"tool": self.tool})
        if name == POST_TOOL_USE:
            self._state_since = t  # 刷新超时计时，外观不变
            return None
        if name == PERMISSION_REQUEST:
            return self._go(State.ATTENTION, {"tool": self.tool})
        if name == POST_TOOL_FAILURE:
            return self._go(State.ERROR, {"tool": self.tool})
        if name == STOP:
            star = self.tool_count >= 8  # claudia-pet"得意"规则
            self.tool_count = 0
            return self._go(State.CELEBRATE, {"star": star})
        return None

    # ---- 周期 tick：处理自动回落 ----
    def tick(self):
        t, s = self.now(), self.state
        held_ms = (t - self._state_since) * 1000
        if s == State.ERROR and held_ms >= self.cfg["error_ms"]:
            return self._go(State.IDLE)
        if s == State.CELEBRATE and held_ms >= self.cfg["celebrate_ms"]:
            return self._go(State.IDLE)
        if s in (State.WORKING, State.THINKING) and held_ms >= self.cfg["work_timeout_ms"]:
            return self._go(State.IDLE)  # attention 不受限（claudia-pet 规则）
        return None

    # ---- 手动触发（托盘菜单/双击测试用） ----
    def force(self, state: State):
        return self._go(state, {"manual": True})

    def _go(self, state, info=None):
        if state == self.state and state not in (State.WORKING, State.THINKING):
            return None  # 同态跳过（working 允许刷新工具名）
        self.state = state
        self._state_since = self.now()
        return Transition(state, info)
