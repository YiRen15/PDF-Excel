@echo off
if "%~1"=="RUN" goto :main
cmd /k ""%~f0" RUN"
exit /b

:main
setlocal enabledelayedexpansion
title 动态心电图 PDF 转 Excel Web 诊断启动工具 (PDF-Excel 1.01.00)

echo ==================================================
echo    动态心电图 PDF 转 Excel - 系统深度诊断与启动 [版本: PDF-Excel 1.01.00]
echo ==================================================
echo.
echo [诊断日志] 启动时间: %DATE% %TIME%
echo [诊断日志] 当前工作路径: %CD%
echo.

:: --------------------------------------------------
:: 步骤 1: 检查核心代码文件
:: --------------------------------------------------
echo ===== 步骤 1: 检查核心代码文件 =====
if exist "app.py" (
    echo   [OK] app.py 存在
) else (
    echo   [错误] 未找到 app.py！请务必将 ZIP 压缩包解压后再运行！
    pause
    exit /b
)
if exist "parser_engine.py" (
    echo   [OK] parser_engine.py 存在
)
echo.

:: --------------------------------------------------
:: 步骤 2: 检索 Python 路径
:: --------------------------------------------------
echo ===== 步骤 2: 检索 Python 路径 =====
set "PY_EXE="

if exist "%LOCALAPPDATA%\Programs" (
    for /r "%LOCALAPPDATA%\Programs" %%f in (python.exe) do (
        if exist "%%f" if "!PY_EXE!"=="" (
            set "PY_EXE=%%f"
            echo   [OK] 在 AppData 中自动匹配到: %%f
        )
    )
)

if "!PY_EXE!"=="" (
    python -c "import sys" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_EXE=python"
        echo   [OK] 通过环境变量匹配到: python
    )
)

if "!PY_EXE!"=="" (
    py -c "import sys" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_EXE=py"
        echo   [OK] 通过 Windows 启动器匹配到: py
    )
)

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
    echo   [错误] 未能检索到有效的 Python 解释器！
    echo   请安装 Python: https://www.python.org/downloads/
    echo   安装时务必勾选 "Add python.exe to PATH"
    echo.
    pause
    exit /b
)

echo   [诊断日志] 最终锁定 Python: "!PY_EXE!"
"!PY_EXE!" --version
echo.

:: --------------------------------------------------
:: 步骤 3: 测试核心组件库
:: --------------------------------------------------
echo ===== 步骤 3: 测试核心组件库 =====
"!PY_EXE!" -c "import flask, openpyxl, fitz, pdfplumber" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [提示] 正在自动安装缺失依赖【使用清华国内镜像源】...
    "!PY_EXE!" -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple flask openpyxl pymupdf pdfplumber
    echo   [OK] 组件安装完成！
) else (
    echo   [OK] 依赖库全部就绪！
)
echo.

:: --------------------------------------------------
:: 步骤 4: 启动后端 Web 服务并调起浏览器
:: --------------------------------------------------
echo ===== 步骤 4: 启动 Web 服务与浏览器 =====
echo [提示] 正在为您自动唤起默认浏览器打开 http://127.0.0.1:5050 ...
echo --------------------------------------------------

:: 在后台拉起 2 秒延时自动打开浏览器线程
:: 已由 app.py 统一精准拉起 1 个浏览器标签页，避免重复多页开标签

"!PY_EXE!" app.py

echo.
echo ==================================================
echo    系统运行结束，控制台已留存，请查看上方输出。
echo ==================================================
echo.
pause