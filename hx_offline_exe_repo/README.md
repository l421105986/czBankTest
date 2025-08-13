
# 一键自动产出 Windows EXE（GitHub Actions）

## 使用方法
1. 在 GitHub 新建一个**空仓库**（可私有）。
2. 把本目录下的所有文件推到仓库：
   - `app/`（包含源代码）
   - `.github/workflows/build_windows_exe.yml`（自动构建脚本）
3. 进仓库 **Actions** → 选择 **Build Windows EXE** → `Run workflow`。
4. 等几分钟，构建完成后在该 workflow 的 **Artifacts** 里下载：
   - `hx-offline-editor-exe`（单文件 EXE）
   - `hx-offline-editor-dist`（完整目录版）

> 如果你使用的是 `main` 或 `master` 分支，推送后也会自动触发构建。

## 本项目说明
- 代码路径：`app/`
- 主程序：`app/app_main.py`
- 依赖列表：`app/requirements.txt`
- 打包工具：PyInstaller
