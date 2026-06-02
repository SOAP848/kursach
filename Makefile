# Makefile для Parametric Scatter Add-on
# Использование: make <target>

.PHONY: test test-verbose lint security docs clean install-deps help

help:
	@echo "Parametric Scatter Add-on - Makefile"
	@echo ""
	@echo "Цели:"
	@echo "  test          Запустить все unit-тесты (pytest)"
	@echo "  test-verbose  Запустить тесты с подробным выводом"
	@echo "  lint          Запустить flake8 линтинг"
	@echo "  security      Запустить SAST-анализ bandit"
	@echo "  docs          Открыть документацию"
	@echo "  clean         Очистить кэш Python"
	@echo "  install-deps  Установить зависимости для разработки"
	@echo ""

test:
	py -m pytest tests/ -v --tb=short

test-verbose:
	py -m pytest tests/ -v --tb=long

lint:
	py -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --ignore=F722,F821
	py -m flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics --ignore=F722,F821

security:
	py -m bandit -r . -c .bandit

docs:
	@echo "Документация доступна в директории docs/:"
	@echo "  docs/architecture.md - Архитектура проекта"
	@echo "  docs/api.md - API документация"
	@echo "  README.md - Основная документация"

clean:
	@echo "Очистка кэша Python..."
	py -c "import shutil, os; [shutil.rmtree(p) for p in ['__pycache__', '.pytest_cache'] if os.path.isdir(p)]"
	@echo "Готово."

install-deps:
	py -m pip install -r requirements-dev.txt