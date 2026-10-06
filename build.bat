@echo off
chcp 65001 >nul
cd /d %~dp0

echo ============================================================
echo   构建 Prism（含卸载程序）
echo ============================================================
echo.

echo [0/3] 清理旧构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "build_uninstall" rmdir /s /q "build_uninstall"
if exist "dist_uninstall" rmdir /s /q "dist_uninstall"

echo.
echo [1/3] 激活虚拟环境...
call .venv\Scripts\activate.bat
if errorlevel 1 goto :error

echo.
echo [2/3] 打包主程序（文件夹模式）...
pyinstaller Prism.spec --noconfirm --clean
if errorlevel 1 goto :error

echo.
echo [3/3] 打包卸载程序（单文件模式，直接输出到 dist\Prism）...
pyinstaller uninstall.spec --noconfirm --clean --distpath "dist\Prism"
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