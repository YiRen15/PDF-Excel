@echo off
setlocal enabledelayedexpansion
if "%~1"=="RUN" goto :main
cmd /k ""%~f0" RUN"
exit /b

:main
title 动态心电图 PDF 转 Excel Web 诊断启动工具

echo ==================================================
echo    动态心电图 PDF 转 Excel - 系统深度诊断与启动
echo ==================================================
echo.
echo [诊断日志] 启动时间: %DATE% %TIME%
echo [诊断日志] 当前工作路径: %CD%
echo.

:: --------------------------------------------------
:: 步骤 1: 检查必要代码文件是否存在
:: --------------------------------------------------
echo ===== 步骤 1: 检查核心代码文件 =====
if exist "app.py" (
    echo   [OK] app.py 存在
) else (
    echo   [错误] 未找到 app.py！请务必将 ZIP 压缩包【解压到文件夹】后双击运行！
    echo   [错误] 当前目录文件列表如下:
    dir /b
    echo.
    pause
    exit /b
)

if exist "parser_engine.py" (
    echo   [OK] parser_engine.py 存在
) else (
    echo   [警告] 未找到 parser_engine.py，请检查解压完整性
)
echo.

:: --------------------------------------------------
:: 步骤 2: 搜寻系统中的 Python 解释器路径 (全盘原生递归多路全检索)
:: --------------------------------------------------
echo ===== 步骤 2: 检索 Python 路径 =====
set "PY_EXE="

:: 1) 原生全递归搜寻 AppData\Local\Programs 目录
if exist "%LOCALAPPDATA%\Programs" (
    for /r "%LOCALAPPDATA%\Programs" %%f in (python.exe) do (
        if exist "%%f" if "!PY_EXE!"=="" (
            set "PY_EXE=%%f"
            echo   [OK] 在 AppData 中自动匹配到: %%f
        )
    )
)

:: 2) 检查系统 PATH 环境变量
if "!PY_EXE!"=="" (
    python -c "import sys" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_EXE=python"
        echo   [OK] 通过环境变量匹配到: python
    )
)

:: 3) 检查 Windows 启动器 py
if "!PY_EXE!"=="" (
    py -c "import sys" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_EXE=py"
        echo   [OK] 通过 Windows 启动器匹配到: py
    )
)

:: 4) 原生全递归搜寻 C:\Program Files
if "!PY_EXE!"=="" (
    if exist "C:\Program Files" (
        for /r "C:\Program Files" %%f in (python.exe) do (
            if exist "%%f" if "!PY_EXE!"=="" (
                set "PY_EXE=%%f"
                echo   [OK] 在 Program Files 中匹配到: %%f
            )
        )
    )
)

if "!PY_EXE!"=="" (
    echo.
    echo   [错误] 未能在您的电脑中检索到有效的 Python 解释器！
    echo   请确认已安装 Python (下载地址: https://www.python.org/downloads/)
    echo   安装时务必勾选 "Add python.exe to PATH"
    echo.
    pause
    exit /b
)

echo   [诊断日志] 最终锁定使用的 Python 解释器: "!PY_EXE!"
"!PY_EXE!" --version
echo.

:: --------------------------------------------------
:: 步骤 3: 测试 Python 依赖组件
:: --------------------------------------------------
echo ===== 步骤 3: 测试核心组件库 (Flask/OpenPyXL/PyMuPDF) =====
"!PY_EXE!" -c "import flask, openpyxl, fitz, pdfplumber; print('  [OK] 所有核心依赖组件库检测完毕，完全正常！')" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [提示] 正在自动为您下载安装缺失依赖 (使用清华国内极速镜像源)...
    "!PY_EXE!" -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple flask openpyxl pymupdf pdfplumber
    echo   [OK] 组件安装完成！
) else (
    echo   [OK] 依赖库全部完整预备就绪！
)
echo.

:: --------------------------------------------------
:: 步骤 4: 启动后端服务引擎
:: --------------------------------------------------
echo ===== 步骤 4: 启动 Flask 后端 Web 服务 =====
echo [提示] 正在调起应用程序，请观察下方输出日志...
echo --------------------------------------------------

"!PY_EXE!" app.py

echo.
echo ==================================================
echo    系统运行结束。控制台已留存，请查看上方输出。
echo ==================================================
echo.

pause