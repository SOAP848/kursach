# Makefile для Parametric Scatter Add-on
# Использование: make <target>

.PHONY: test test-verbose lint security docs clean install-deps help \
        docker-build docker-test docker-bandit docker-lint docker-all docker-clean

help:
	@echo "Parametric Scatter Add-on - Makefile"
	@echo ""
	@echo "Цели (локальные):"
	@echo "  test          Запустить все unit-тесты (pytest)"
	@echo "  test-verbose  Запустить тесты с подробным выводом"
	@echo "  lint          Запустить flake8 линтинг"
	@echo "  security      Запустить SAST-анализ bandit"
	@echo "  docs          Открыть документацию"
	@echo "  clean         Очистить кэш Python"
	@echo "  install-deps  Установить зависимости для разработки"
	@echo ""
	@echo "Цели (Docker):"
	@echo "  docker-build    Собрать Docker-образ"
	@echo "  docker-test     Запустить тесты в Docker"
	@echo "  docker-bandit   Запустить bandit в Docker"
	@echo "  docker-lint     Запустить flake8 в Docker"
	@echo "  docker-all      Запустить все проверки в Docker"
	@echo "  docker-clean    Очистить Docker-образы"
	@echo ""

# --- Локальные цели ---

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

# --- Docker цели ---

docker-build:
	docker compose build

docker-test:
	docker compose run --rm test

docker-bandit:
	docker compose run --rm bandit

docker-lint:
	docker compose run --rm lint

docker-all:
	docker compose run --rm all

docker-clean:
	@echo "Очистка Docker-образов..."
	docker rmi parametric-scatter:latest parametric-scatter:test parametric-scatter:bandit parametric-scatter:lint 2>/dev/null || true
	@echo "Готово."