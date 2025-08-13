
一、安装依赖（建议新建虚拟环境）
pip install -r requirements.txt

二、运行测试
python app_main.py

三、打包 EXE（单文件）
pip install pyinstaller
pyinstaller -F app_main.py --name 业务工具确认版 --hidden-import=openpyxl --hidden-import=xlrd

四、注意事项
- 如需选择“老式 .xls”文件，必须确保 xlrd==1.2.0 已安装（requirements 已包含）。
- 首次运行会在 ./data 下创建 SQLite 数据库 app.db。
- “库维护”导入后，可在“批量转账”的“为选中行选择行号”里检索使用。
- 批量转账导出收口规则：只要 TRANSFER_MODE=0-行内，LINE_TYPE 导出为空。
- 编辑区内容居中显示；窗口自适应，按钮不遮挡。
