"""Скрипт для запуска интеграционных тестов внутри Blender.

Использование в PowerShell:
  & "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --python run_blender_tests.py
"""

import sys
import os
import unittest

# Добавляем путь к установленным extensions Blender
extensions_path = os.path.expanduser(
    r"~\AppData\Roaming\Blender Foundation\Blender\5.1\extensions\user_default"
)
if os.path.isdir(extensions_path):
    sys.path.insert(0, extensions_path)

# Импортируем аддон (НЕ регистрируем — он уже включён в Blender)
import parametric_scatter

# Добавляем tests в sys.path и запускаем тесты
project_root = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.join(project_root, "tests")
sys.path.insert(0, tests_dir)

import test_integration

if __name__ == "__main__":
    sys.argv = [sys.argv[0]]
    unittest.main(module=test_integration, verbosity=2)