@echo off
setlocal enabledelayedexpansion
chcp 936 >nul
title 动态心电图 PDF 转 Excel Web 启动工具

echo ==================================================
echo    动态心电图 PDF 转 Excel 工具 正在启动...
echo ==================================================
echo.

if exist .active_port del .active_port

:: 1. 智能检测系统的 Python 解释器
set PY_CMD=
python --version >nul 2>&1
if !errorlevel! equ 0 set PY_CMD=python

if "!PY_CMD!"=="" (
    py -3 --version >nul 2>&1
    if !errorlevel! equ 0 set PY_CMD=py -3
)

if "!PY_CMD!"=="" (
    py --version >nul 2>&1
    if !errorlevel! equ 0 set PY_CMD=py
)

if "!PY_CMD!"=="" (
    echo.
    echo ==================================================
    echo [错误] 未在当前电脑检测到已安装的 Python 环境！
    echo --------------------------------------------------
    echo 请先安装 Python (只需安装一次):
    echo 1. 下载地址: https://www.python.org/downloads/
    echo 2. 安装时务必勾选 "Add python.exe to PATH"
    echo 3. 安装完成后重新双击本脚本即可。
    echo ==================================================
    echo.
    pause
    goto :end
)

echo [提示] 成功调起系统 Python 解释器: !PY_CMD!
echo.

:: 2. 检查并自动安装缺失的解析组件 (Flask / OpenPyXL / PyMuPDF)
echo [提示] 正在检查后台解析组件包...
!PY_CMD! -c "import flask, openpyxl, fitz, pdfplumber" >nul 2>&1
if !errorlevel! neq 0 (
    echo [提示] 正在为您自动安装必备组件 (Flask/OpenPyXL/PyMuPDF)...
    !PY_CMD! -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple flask openpyxl pymupdf pdfplumber
    echo [提示] 组件安装完毕！
    echo.
)

:: 3. 启动后台解析服务
echo [提示] 正在启动后台服务引擎...
start /b !PY_CMD! app.py

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

:end