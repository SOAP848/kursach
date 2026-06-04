# =============================================================================
# Dockerfile для Parametric Scatter Add-on
# =============================================================================
# Использование:
#   docker build -t parametric-scatter .
#   docker run --rm parametric-scatter test        # запуск тестов
#   docker run --rm parametric-scatter bandit       # запуск bandit
#   docker run --rm parametric-scatter lint         # запуск flake8
#   docker run --rm parametric-scatter all          # всё сразу
# =============================================================================

FROM python:3.11-slim AS base

LABEL org.opencontainers.image.title="Parametric Scatter Add-on"
LABEL org.opencontainers.image.description="Docker-образ для запуска тестов и SAST-анализа Blender-аддона"
LABEL org.opencontainers.image.version="1.0.0"

# Отключаем буферизацию вывода Python для логирования в реальном времени
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Устанавливаем системные зависимости (минимально необходимые)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements-dev.txt requirements.txt ./

# Удаляем строку с кастомным PyPI-индексом (он не работает вне Safety CLI)
# и устанавливаем зависимости из публичного PyPI
RUN tail -n +2 requirements-dev.txt > requirements-docker.txt \
    && pip install --no-cache-dir -r requirements-docker.txt \
    && rm requirements-docker.txt

# =============================================================================
# Стадия: тестирование
# =============================================================================
FROM base AS test-stage

# Копируем исходный код проекта
COPY . .

# Создаём симлинк, чтобы корень проекта был доступен как пакет parametric_scatter
# (файлы __init__.py, scatter_core.py и т.д. лежат в корне, а тесты импортируют
#  from parametric_scatter import scatter_core)
RUN ln -sf /app /usr/local/lib/python3.11/site-packages/parametric_scatter

# Команда по умолчанию — запуск тестов
CMD ["pytest", "tests/", "-v", "--tb=short"]

# =============================================================================
# Стадия: bandit (SAST-анализ)
# =============================================================================
FROM base AS bandit-stage

# Копируем исходный код проекта
COPY . .

# Создаём симлинк для импорта parametric_scatter
RUN ln -sf /app /usr/local/lib/python3.11/site-packages/parametric_scatter

# Команда для запуска bandit
CMD ["bandit", "-r", ".", "-c", ".bandit"]

# =============================================================================
# Стадия: lint (flake8)
# =============================================================================
FROM base AS lint-stage

# Копируем исходный код проекта
COPY . .

# Создаём симлинк для импорта parametric_scatter
RUN ln -sf /app /usr/local/lib/python3.11/site-packages/parametric_scatter

# Команда для запуска flake8
CMD ["flake8", ".", "--count", "--select=E9,F63,F7,F82", "--show-source", "--statistics", "--ignore=F722,F821"]

# =============================================================================
# Финальная стадия (по умолчанию)
# =============================================================================
FROM base AS final

# Копируем исходный код проекта
COPY . .

# Создаём симлинк для импорта parametric_scatter
RUN ln -sf /app /usr/local/lib/python3.11/site-packages/parametric_scatter

# Скрипт-точка входа для выбора режима запуска
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["test"]
