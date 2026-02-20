#!/usr/bin/env python3
"""
Скрипт сборки MKAI в исполняемый файл (.exe)
=====================================================
Запуск: python build_exe.py
Результат: dist/MKAI.exe
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
APP_NAME = "MKAI"
MAIN_SCRIPT = "task_solver_desktop.py"
ICON_FILE = "image-Picsart-AiImageEnhancer.ico"

def check_pyinstaller():
    try:
        import PyInstaller
        print("✓ PyInstaller установлен")
        return True
    except ImportError:
        print("✗ PyInstaller не установлен")
        print("  Установка: pip install pyinstaller")
        return False

def build():
    if not check_pyinstaller():
        return False
    
    print(f"\n{'='*50}")
    print(f"  Сборка {APP_NAME}")
    print(f"{'='*50}\n")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", APP_NAME,
        "--clean",
        "--noconfirm",
    ]

    if ICON_FILE and Path(ICON_FILE).exists():
        cmd.extend(["--icon", ICON_FILE])

    hidden_imports = [
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtWidgets", 
        "PyQt6.QtGui",
        "requests",
    ]
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    cmd.append(MAIN_SCRIPT)
    
    print("Выполняю команду:")
    print(" ".join(cmd))
    print()

    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        exe_path = Path("dist") / f"{APP_NAME}.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\n{'='*50}")
            print(f"  ✓ Сборка успешна!")
            print(f"  Файл: {exe_path.absolute()}")
            print(f"  Размер: {size_mb:.1f} MB")
            print(f"{'='*50}\n")
            return True
    
    print("\n✗ Ошибка сборки")
    return False

def main():
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    if not Path(MAIN_SCRIPT).exists():
        print(f"✗ Файл {MAIN_SCRIPT} не найден")
        return
    
    build()

if __name__ == "__main__":
    main()
