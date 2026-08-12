@echo off
chcp 936 >nul
title 动态心电图 PDF 转 Excel Web 启动工具

echo ==================================================
echo    动态心电图 PDF 转 Excel 工具 正在启动...
echo ==================================================
echo.

if exist .active_port del .active_port

:: 1. 检查当前电脑是否安装了系统 Python
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

:: 2. 检查现有 venv 文件夹中的主控 Python 路径与依赖包是否在当前电脑上完整有效
set NEED_REBUILD=0

if exist "venv\pyvenv.cfg" (
    for /f "usebackq tokens=1,* delims==" %%A in ("venv\pyvenv.cfg") do (
        set "CFG_KEY=%%A"
        set "CFG_VAL=%%B"
        call :check_cfg_path
    )
) else (
    set NEED_REBUILD=1
)

:: 即使 venv 路径存在，进一步检查核心依赖包是否完整 (防止缺失 flask)
if "%NEED_REBUILD%"=="0" (
    venv\Scripts\python.exe -c "import flask, openpyxl, fitz" >nul 2>&1
    if %errorlevel% neq 0 (
        set NEED_REBUILD=1
    )
)

if "%NEED_REBUILD%"=="1" (
    echo [提示] 首次启动或环境缺失组件，正在配置专属解析环境 (约需 5 秒)...
    if exist venv rmdir /s /q venv >nul 2>&1
    python -m venv venv
    echo [1/2] 专属环境创建完成，正在从镜像源下载安装核心组件 (Flask/OpenPyXL/PyMuPDF)...
    call venv\Scriptsctivate.bat
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pdfplumber openpyxl flask pymupdf
    echo [2/2] 所有依赖组件安装成功！
    echo --------------------------------------------------
)

:: 3. 同步确保组件就绪后，启动后台解析引擎
echo [提示] 正在启动后台解析引擎...
if exist "venv\Scripts\python.exe" (
    start /b venv\Scripts\python.exe app.py
) else (
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pdfplumber openpyxl flask pymupdf
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
exit /b 0

:check_cfg_path
set "CFG_KEY=%CFG_KEY: =%"
if /i "%CFG_KEY%"=="home" (
    set "TARGET_PATH=%CFG_VAL:~1%"
    if not exist "%TARGET_PATH%" set NEED_REBUILD=1
)
if /i "%CFG_KEY%"=="executable" (
    set "TARGET_PATH=%CFG_VAL:~1%"
    if not exist "%TARGET_PATH%" set NEED_REBUILD=1
)
goto :eof