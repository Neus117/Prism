@echo off
chcp 65001 >nul
cd /d %~dp0

echo ============================================================
echo   构建 Prism（含卸载程序）
echo ============================================================
echo.

echo [1/3] 激活虚拟环境...
call .venv\Scripts\activate.bat
if errorlevel 1 goto :error

echo.
echo [2/3] 打包主程序...
pyinstaller Prism.spec --noconfirm --clean
if errorlevel 1 goto :error

echo.
echo [3/3] 打包卸载程序（单文件）...
pyinstaller ^
    --onefile --console --clean --noconfirm ^
    --name "uninstall" ^
    --distpath "dist_uninstall" ^
    --workpath "build_uninstall" ^
    --specpath "build_uninstall" ^
    "tools\uninstall\uninstall.py"
if errorlevel 1 goto :error

echo.
echo 拷贝卸载程序到主程序输出目录...
copy /y "dist_uninstall\uninstall.exe" "dist\Prism\" >nul
if errorlevel 1 goto :error

echo.
echo ============================================================
echo   ✅ 构建完成！
echo   主程序: dist\Prism\Prism.exe
echo   卸载器: dist\Prism\uninstall.exe
echo ============================================================
pause
exit /b 0

:error
echo.
echo ❌ 构建失败，请检查上面的错误信息。
pause
exit /b 1