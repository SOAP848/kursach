# Parametric Scatter — Blender Add-on

**Вариант 46.** 3D-редактор для параметрического размещения объектов.

Модуль-расширение для Blender, реализующий параметрическое размещение
геометрических объектов в заданном пространстве (аналог Corona Scatter).
Управление плотностью, масштабом и поворотом на основе карт текстур.

**Технологии:** Python + Blender API + NumPy

---

## Возможности

- **Параметрическое рассеивание** — размещение множества копий source-объекта
  по поверхности target-объекта.
- **Текстурное управление плотностью** — карта плотности определяет, где
  объекты располагаются гуще, а где реже.
- **Текстурное управление масштабом** — карта масштаба модулирует размер
  каждого экземпляра.
- **Текстурное управление поворотом** — карта поворота задаёт ориентацию
  объектов.
- **Выбор канала текстуры** — R, G, B, A или VALUE (средняя яркость).
- **Выравнивание по нормали** — объекты автоматически ориентируются по
  нормали поверхности.
- **Poisson-disc сэмплинг** — равномерное распределение с контролем
  минимального расстояния между объектами.
- **Jitter** — случайное смещение для более естественного вида.
- **Random Seed** — воспроизводимость результатов.
- **Undo support** — все операции отменяемы.

---

## Установка

### Требования

- Blender 4.2 или новее
- NumPy (обычно уже включён в поставку Blender)

### Установка через .zip (рекомендуется)

1. Упакуйте папку `parametric_scatter` в ZIP-архив:
   ```
   parametric_scatter/
   ├── __init__.py
   ├── blender_manifest.toml
   ├── scatter_core.py
   ├── texture_processor.py
   ├── operators.py
   └── ui_panel.py
   ```
2. В Blender: `Edit → Preferences → Add-ons → Install from Disk...`
3. Выберите ZIP-архив.
4. Найдите в списке "Parametric Scatter" и включите галочку.

### Установка вручную (для разработки)

1. Скопируйте папку `parametric_scatter` в директорию аддонов Blender:
   - **Windows:** `%APPDATA%\Blender Foundation\Blender\x.y\scripts\addons\`
   - **Linux:** `~/.config/blender/x.y/scripts/addons/`
   - **macOS:** `~/Library/Application Support/Blender/x.y/scripts/addons/`
2. В Blender: `Edit → Preferences → Add-ons` → найдите "Parametric Scatter"
   и включите.

---

## Использование

### Быстрый старт

1. Создайте **source-объект** — то, что будет рассеиваться (например, куб,
   сфера, любой меш).
2. Создайте **target-объект** — поверхность, по которой будут распределяться
   копии (плоскость, сфера, ландшафт).
3. Переключитесь в `Layout` или `Modeling` воркспейс.
4. Откройте боковую панель (`N`), перейдите на вкладку **Scatter**.
5. В панели **Parametric Scatter**:
   - Укажите **Source** и **Target** объекты.
   - Настройте **Density** (плотность).
   - При необходимости задайте текстурные карты для Density, Scale, Rotation.
   - Нажмите **Scatter**.

### Настройки

| Параметр | Описание |
|----------|----------|
| **Source** | Объект, копии которого будут рассеиваться |
| **Target** | Поверхность для рассеивания |
| **Density** | Количество объектов на единицу площади |
| **Density Multiplier** | Множитель плотности |
| **Density Map** | Текстура для модуляции плотности |
| **Scale Min / Max** | Диапазон масштаба |
| **Scale Map** | Текстура для модуляции масштаба |
| **Scale Map Influence** | Сила влияния карты масштаба (0–1) |
| **Rotation Min / Max** | Диапазон поворота (градусы) |
| **Rotation Map** | Текстура для модуляции поворота |
| **Rotation Map Influence** | Сила влияния карты поворота (0–1) |
| **Align to Normal** | Выравнивание по нормали поверхности |
| **Poisson Disc** | Равномерное распределение (подавление кластеризации) |
| **Poisson Radius** | Минимальное расстояние между объектами |
| **Jitter** | Случайное смещение (0 — строгая сетка, 1 — хаос) |
| **Random Seed** | Сид для воспроизводимости |
| **Collection** | Имя коллекции для результата |

---

## Архитектура

```
parametric_scatter/
├── __init__.py              # Регистрация аддона, PropertyGroup
├── blender_manifest.toml    # Манифест для Blender 4.2+
├── scatter_core.py          # Ядро: геометрия, генерация точек, трансформации
├── texture_processor.py     # Загрузка и сэмплирование текстур
├── operators.py             # Операторы Scatter / Clear
├── ui_panel.py              # UI-панель в 3D Viewport
├── README.md                # Данный файл
├── docs/
│   ├── architecture.md      # Архитектура и диаграммы (Mermaid)
│   └── api.md               # Полная API-документация
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Фикстуры и моки
│   ├── test_texture_processor.py  # 25 тестов
│   ├── test_scatter_core.py       # 22 теста
│   └── test_integration.py        # Интеграционные тесты
├── .bandit                  # Конфигурация SAST-анализатора
├── requirements-dev.txt     # Зависимости для разработки
└── Makefile                 # Цели: test, lint, security, docs
```

### Поток данных

```
Source Object ──┐
                ├──> scatter_core.run_scatter()
Target Object ──┘         │
     │                    │
     ├── get_mesh_data()  │  ← геометрия поверхности
     ├── generate_points()│  ← точки с учётом карты плотности
     │      └── texture_processor (density_map)
     ├── compute_transforms()  ← масштаб + поворот по картам
     │      └── texture_processor (scale_map, rotation_map)
     └── create_scatter_objects()  ← дубликаты в коллекцию
```

Подробные диаграммы (компонентов, последовательности, классов, состояний) —
см. [`docs/architecture.md`](docs/architecture.md).

---

## API документация

Полная документация всех функций, классов и операторов —
см. [`docs/api.md`](docs/api.md).

### Краткий справочник

| Функция | Модуль | Назначение |
|---------|--------|------------|
| `get_mesh_data()` | `scatter_core` | Извлечение геометрии mesh |
| `generate_points()` | `scatter_core` | Генерация точек на поверхности |
| `compute_transforms()` | `scatter_core` | Вычисление трансформаций |
| `create_scatter_objects()` | `scatter_core` | Создание дубликатов |
| `run_scatter()` | `scatter_core` | Главная функция рассеивания |
| `load_texture_data()` | `texture_processor` | Загрузка текстуры в numpy |
| `sample_texture()` | `texture_processor` | Сэмплирование текстуры |
| `_extract_channel()` | `texture_processor` | Извлечение канала |

---

## Примеры

### Пример 1: Трава на ландшафте

1. Source: низкополигональная травинка
2. Target: ландшафт с UV-развёрткой
3. Density Map: шумовая текстура (белые участки — гуще)
4. Scale Map: градиент (низины — крупнее, вершины — мельче)
5. Нажать **Scatter**

### Пример 2: Камни на дороге

1. Source: несколько вариантов камней (группа)
2. Target: дорожное полотно
3. Density: 50
4. Rotation Map: текстура с направлением
5. Poisson Disc: включён, Radius: 0.5

---

## Разработка

### Запуск из Blender

Для быстрой перезагрузки аддона используйте в Scripting workspace:

```python
import bpy
bpy.ops.preferences.addon_disable(module="parametric_scatter")
bpy.ops.preferences.addon_enable(module="parametric_scatter")
```

### Запуск тестов

#### Модульные тесты (pytest, без Blender)

```bash
cd parametric_scatter
py -m pytest tests/ -v
```

#### Интеграционные тесты (внутри Blender)

Интеграционные тесты (`tests/test_integration.py`) запускаются непосредственно в
Blender через его встроенный Python. Для этого используется скрипт-обёртка
[`run_blender_tests.py`](run_blender_tests.py).

**Требования:**
- Аддон должен быть установлен в Blender (см. [Установка](#установка))
- Blender 4.2 или новее

**Запуск в PowerShell:**

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --python run_blender_tests.py
```

**Запуск в cmd:**

```cmd
"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --python run_blender_tests.py
```

**Запуск с указанием полного пути (из любой директории):**

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --python "C:\полный\путь\к\parametric_scatter\run_blender_tests.py"
```

> **Важно:** Флаг `--background` запускает Blender без графического интерфейса.
> Если нужно видеть окно Blender в процессе тестов, опустите этот флаг.

**Что делает скрипт:**
1. Добавляет путь к установленным extensions Blender в `sys.path`
2. Импортирует модуль `parametric_scatter`
3. Запускает `unittest` с тестами из `tests/test_integration.py`

**Пример вывода успешного запуска:**

```
Blender 5.1.2 (hash ...)
test_addon_enabled ... ok
test_operators_exist ... ok
test_panel_exists ... ok
test_property_group_exists ... ok
test_create_test_objects ... ok
test_clear_removes_objects ... ok
test_scatter_creates_objects ... ok
test_scatter_objects_have_varied_transforms ... ok
test_scatter_objects_on_surface ... ok
test_scatter_with_density_map ... ok
----------------------------------------------------------------------
Ran 10 tests in 1.164s
OK
```

### SAST-анализ (статический анализ безопасности)

```bash
# Установка
py -m pip install bandit

# Запуск
py -m bandit -r . -c .bandit
```

### Проверка зависимостей

```bash
# Установка
py -m pip install safety

# Запуск (требуется подключение к интернету)
py -m safety check -r requirements-dev.txt
```

> **Примечание:** Safety 3.x требует API-ключ и подключение к интернету.
> При отсутствии доступа к PyUp API используйте bandit для SAST-анализа.

### Makefile цели

```bash
make test       # Запуск всех тестов
make lint       # Статический анализ кода (flake8)
make security   # SAST-анализ (bandit)
make docs       # Просмотр документации
make clean      # Очистка кэша Python
make install-deps  # Установка зависимостей для разработки
```

---

## Безопасность

### SAST-анализ (Static Application Security Testing)

Для статического анализа кода используется **bandit**.
Конфигурация — в файле [`.bandit`](.bandit).

**Результаты последнего запуска:**
- Просканировано: **1211 строк кода**
- Найдено уязвимостей: **0**
- Пропущенные тесты: `B101` (assert), `B311` (random), `B324` (hashlib)

Проверяемые категории уязвимостей:
- Инъекции (`eval`, `exec`, `subprocess`)
- Использование небезопасных библиотек (`pickle`, `marshal`, `xml`)
- Жёстко заданные пароли и криптографические ключи
- Небезопасные сетевые соединения

### Проверка зависимостей

Для проверки уязвимостей в зависимостях используется **safety**.
Список зависимостей — в [`requirements-dev.txt`](requirements-dev.txt).

> **Важно:** Safety 3.x требует регистрации на PyUp.io и API-ключа.
> Для офлайн-проверки используйте `pip-audit` или проводите проверку
> в среде с доступом к интернету.

---

## Тестирование

| Файл | Тестов | Статус | Описание |
|------|--------|--------|----------|
| `tests/test_texture_processor.py` | 25 | ✅ Все проходят | Модульные тесты обработки текстур |
| `tests/test_scatter_core.py` | 22 | ✅ Все проходят | Модульные тесты ядра рассеивания |
| `tests/test_integration.py` | 10 | ✅ Все проходят | Интеграционные тесты (запуск в Blender) |
| **Всего** | **57** | **57 passed** | |

---

## Лицензия

MIT
