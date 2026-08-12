@echo off
title 动态心电图 PDF 转 Excel Web 启动工具

echo ==================================================
echo    动态心电图 PDF 转 Excel 工具 正在启动...
echo ==================================================
echo.

if not exist "app.py" (
    echo [错误] 未找到 app.py 文件，请将本脚本放在项目主文件夹中运行！
    pause
    goto :end
)

if exist .active_port del .active_port

echo [提示] 正在启动后台服务引擎...
echo 提示: 启动成功后请保留本命令行窗口，不要关闭。
echo --------------------------------------------------

python app.py
if %errorlevel% neq 0 (
    echo.
    echo [提示] 核心组件未配置，正在自动为您安装必备依赖 (约需 5 秒)...
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple flask openpyxl pymupdf pdfplumber
    echo [提示] 组件安装完成，正在重新调起服务...
    python app.py
)

echo.
echo ==================================================
echo    系统已退出。按任意键关闭窗口。
echo ==================================================
echo.

pause

:end