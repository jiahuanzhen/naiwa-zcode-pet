# 奶蛙桌宠 · Zcode

一只**真奶蛙**住在你的桌面上，实时反映 Zcode Agent 的工作状态：你发消息它思考、
Zcode 读文件它翻资料、写代码它码字、等你审批它急得举手、报错它委屈、干完它举拳欢呼。

形象采用**真奶蛙序列帧**（不是 AI 重绘），动画循环取自
[NaiWaChatPet](https://github.com/SbongeBobybl/NaiWaChatPet) 的素材库，随仓库分发；
角色素材权利归原权利人，仅限个人桌面/同人非商用使用，详见 [NOTICE.md](NOTICE.md)。

架构参考（调研于 2026-11）：

- [SbongeBobybl/NaiWaChatPet](https://github.com/SbongeBobybl/NaiWaChatPet) — 真奶蛙素材来源；"真序列帧 + 情绪动作"的做法
- [kirito1207/claudia-pet](https://github.com/kirito1207/claudia-pet) — 工具名→动作分类、3 分钟超时回待机（attention 不受限）、一轮 ≥8 次工具完成的"得意"台词、系统通知
- [MerZlin/dsh-pet-indesktop](https://github.com/MerZlin/dsh-pet-indesktop) — hooks→JSONL→桌宠 的解耦架构

## 架构

```
Zcode CLI ──(hooks, 7 事件)──> zcode_pet_hook.py ──追加──> ~/.zcode-pet/events.jsonl
                                                              │ 只读轮询
                                              桌宠进程 (PySide6) <┘
                                    状态机 → 序列帧/姿态 + 程序化变换 + 气泡
```

- 桌宠与 CLI 完全解耦：桌宠崩溃不影响会话，hooks 写入失败不影响桌宠。
- 状态优先级：`attention > error > working/thinking > idle`；celebrate/error 播完自动回落。

## 状态对照

| Zcode Hook | 桌宠状态 | 表现 |
|---|---|---|
| `SessionStart` | 🎉 celebrate | 出场打招呼 + 纸屑 |
| `UserPromptSubmit` | 🤔 thinking | 托腮思考（ponder），左右轻摇 |
| `PreToolUse` / `PostToolUse` | 💼 working | 专注姿态（focused），气泡按工具分类：读文件→"翻资料中"、写文件→"码字中"、上网→"查资料"、子代理→"派活"、其余→"敲命令" |
| `PermissionRequest` | ✋ attention | **真帧动画**：surprised_in(14帧) + surprised 循环(95帧) @14fps，气泡粘滞 + 系统通知 |
| `PostToolUseFailure` | 😵 error | **真帧动画**：sad_in(15帧) + sad 循环(120帧) @14fps，8 秒后回落 |
| `Stop` | 🎉 celebrate | 举拳欢呼 + 纸屑；一轮 ≥8 次工具触发"得意"台词 |
| （180s 无事件） | 😴 idle | 微笑（smile）呼吸浮动 + 随机闲聊；attention 不受此限 |

交互：**拖拽**移动（自动记忆位置）、**单击**戳一戳、**双击**手动欢呼、**托盘**菜单
（显示/隐藏、手动测试 6 状态、退出）。

## 安装与运行

1. 依赖：`python -m pip install -r requirements.txt`（PySide6 / Pillow / numpy）
2. hooks 已合并进 `~/.zcode/cli/config.json`（7 事件，增量添加、原条目保留；
   合并前备份 `config.json.bak-naiwa`），写入端在 `C:/Users/lenovo/.zcode-pet/zcode_pet_hook.py`
3. 启动：双击 `启动桌宠.bat`，或 `python -m pet`
4. **新开的 Zcode 会话**起 hooks 生效（桌宠会忽略启动前的历史事件）

## 自定义

- **换动作**：`tools/fetch_naiwa_assets.py` 的 `STATE_MAP` 里改映射（45 个动作可选：
  angry/confused/shy/sleepy/dizzy/love/hug/proud…），重跑即可；备用姿态已下载到 `assets_extra/`
- **调手感**：`pet/sprites.py` 的 `MOTION`（帧率、弹跳、摇摆、压缩）；`~/.zcode-pet/pet_config.json`
  （缩放、超时、通知开关）
- **改台词**：`pet/bubble.py`

## 调试与测试

```
python -m pet --selftest            # 状态机自测（35 项断言）
python -m pet --render-test DIR     # 导出各状态基准帧
python -m pet --smoke 15000         # 启动 N 秒自动退出（冒烟）
python tools/fetch_naiwa_assets.py  # 重新拉取/更新真奶蛙素材
```

日志：`~/.zcode-pet/pet.log`；事件流：`~/.zcode-pet/events.jsonl`；预览图：`docs/preview/`。

## 卸载

1. 还原 `~/.zcode/cli/config.json`（删除 7 个含 `zcode_pet_hook.py` 的条目，或用 `config.json.bak-naiwa`）
2. 删除 `C:/Users/lenovo/.zcode-pet/` 与本项目目录

## 打包 exe

```
python -m pip install pyinstaller
python tools/make_icon.py
python -m PyInstaller --noconfirm --clean --windowed --name NaiWaPet --icon icon.ico --add-data "assets;assets" launcher.py
```

产物在 `dist/NaiWaPet/`（也可直接到 [Releases](../../releases) 下载打包好的 `奶蛙桌宠-win64.zip`）。

## 许可

- 本项目源代码：[MIT](LICENSE)
- 奶蛙角色动画素材：来源与权利声明见 [NOTICE.md](NOTICE.md)（个人使用/同人非商用）
