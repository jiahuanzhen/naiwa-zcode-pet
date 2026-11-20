# NOTICE · 素材来源与权利声明

## 奶蛙角色动画素材（`assets/` 与 `assets_extra/`）

- 来源项目：[SbongeBobybl/NaiWaChatPet](https://github.com/SbongeBobybl/NaiWaChatPet)（仓库以 GPL-3.0 发布），
  经 `tools/fetch_naiwa_assets.py` 自该仓库 `Source/NaiWaChatPet/animations/` 拉取并缩放归一化。
- 奶蛙为网络流行的 AI 二创角色（源自奶龙的恶搞二创），其角色及相关美术的权利归原权利人。
  本仓库不主张任何角色素材的权利，素材权利不因本仓库发生转让。
- 用途限定：个人桌面使用 / 同人非商用。如需商用请自行联系权利人获得授权。
- 如你是权利人并认为本仓库的素材使用不当，请提 Issue，我会立即处理（移除素材并改为
  `tools/fetch_naiwa_assets.py` 按需拉取的方式）。

## 代码

本项目自有源代码（`pet/`、`tools/`、`hooks/`、`launcher.py`）以 MIT 许可发布，见 LICENSE。
架构与玩法设计参考了以下项目，仅借鉴思路，未复制代码：

- [SbongeBobybl/NaiWaChatPet](https://github.com/SbongeBobybl/NaiWaChatPet) — 真奶蛙序列帧素材与"情绪动作"做法
- [kirito1207/claudia-pet](https://github.com/kirito1207/claudia-pet) — 工具分类台词、超时回落、任务通知
- [MerZlin/dsh-pet-indesktop](https://github.com/MerZlin/dsh-pet-indesktop) — hooks→JSONL→桌宠 解耦架构

## 构建产物

Releases 中的运行包（`奶蛙桌宠-win64.zip`）由 PyInstaller 打包，包含上述素材，
其素材部分适用与本文件相同的声明。
