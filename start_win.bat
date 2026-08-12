@echo off
chcp 936 >nul
title 动态心电图 PDF 转 Excel Web 启动工具

echo ==================================================
echo    动态心电图 PDF 转 Excel 工具 正在启动...
echo ==================================================
echo.

if exist .active_port del .active_port

:: 1. 检查当前电脑是否安装了 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未在当前电脑检测到 Python 环境！
    echo --------------------------------------------------
    echo 请先安装 Python:
    echo 1. 下载地址: https://www.python.org/downloads/
    echo 2. 安装时请务必勾选 "Add python.exe to PATH"
    echo 3. 安装完成后双击本脚本即可自动启动。
    echo --------------------------------------------------
    echo.
    pause
    exit /b 1
)

:: 2. 检测现有 venv 虚拟环境是否对当前电脑有效 (防止发给别人因路径不同报错)
set NEED_REBUILD=0
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -c "import sys" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [提示] 检测到跨电脑转移的旧环境路径在当前电脑上不兼容，正在自动重置...
        set NEED_REBUILD=1
    )
) else (
    set NEED_REBUILD=1
)

if "%NEED_REBUILD%"=="1" (
    if exist venv rmdir /s /q venv >nul 2>&1
    echo [提示] 正在在当前电脑配置专属 Python 解析环境，请稍候...
    python -m venv venv
    echo [1/2] 专属环境配置完成，正在下载安装相关支持组件包...
    call venv\Scriptsctivate.bat
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pdfplumber openpyxl flask pymupdf
    echo [2/2] 组件包安装完成！
    echo --------------------------------------------------
)

:: 3. 启动后台解析引擎
echo [提示] 正在启动后台解析引擎...
if exist "venv\Scripts\python.exe" (
    start /b venv\Scripts\python.exe app.py
) else (
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pdfplumber openpyxl flask pymupdf >nul 2>&1
    start /b python app.py
)

timeout /t 3 /nobreak >nul

set PORT=5050
if exist .active_port (
    set /p PORT=<.active_port
)

start http://127.0.0.1:%PORT%

echo.
echo ==================================================
echo    系统已成功启动！
echo    浏览器已自动打开网页: http://127.0.0.1:%PORT%
echo    提示: 使用完毕后直接关闭本窗口即可退出程序。
echo ==================================================
echo.

pause