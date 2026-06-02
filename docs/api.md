# API-документация Parametric Scatter

## Модуль `scatter_core.py` — Ядро алгоритма рассеивания

### `get_mesh_data(obj: bpy.types.Object) -> Optional[dict]`

Извлекает геометрию mesh-объекта в мировых координатах.

**Параметры:**
- `obj` — целевой mesh-объект (должен иметь `type == "MESH"`)

**Возвращает:**
- Словарь с ключами:
  - `vertices` — `np.ndarray`, shape `(N, 3)` — мировые координаты вершин
  - `faces` — `list[list[int]]` — индексы вершин полигонов
  - `centers` — `np.ndarray`, shape `(M, 3)` — центры полигонов
  - `normals` — `np.ndarray`, shape `(M, 3)` — нормали полигонов
  - `areas` — `np.ndarray`, shape `(M,)` — площади полигонов
  - `uv_layer` — `str | None` — имя активного UV-слоя
- `None`, если `obj is None`, `obj.type != "MESH"` или mesh не содержит полигонов

**Исключения:** нет (все ошибки обрабатываются внутри)

---

### `generate_points(mesh_data: dict, density: int, density_multiplier: float = 1.0, density_map: Optional[np.ndarray] = None, density_channel: str = "VALUE", use_poisson_disc: bool = False, poisson_radius: float = 0.5, jitter: float = 0.0, random_seed: int = 0) -> np.ndarray`

Генерирует точки на поверхности mesh-объекта.

**Параметры:**
- `mesh_data` — словарь от `get_mesh_data()`
- `density` — базовое количество точек на единицу площади
- `density_multiplier` — множитель плотности (0.0–10.0)
- `density_map` — текстура плотности (`np.ndarray`, shape `(H, W, C)`) или `None`
- `density_channel` — канал текстуры: `"R"`, `"G"`, `"B"`, `"A"`, `"VALUE"`
- `use_poisson_disc` — включить Poisson-disc фильтр
- `poisson_radius` — минимальное расстояние между точками
- `jitter` — случайное смещение (0.0 — строгая сетка, 1.0 — полный хаос)
- `random_seed` — сид для воспроизводимости

**Возвращает:**
- `np.ndarray`, shape `(K, 3)` — координаты точек в мировом пространстве

**Алгоритм:**
1. Для каждого полигона вычисляется количество точек пропорционально его площади
2. Точки генерируются внутри треугольников через `_sample_triangle()`
3. Если задана `density_map`, плотность модулируется значением текстуры
4. Опционально применяется Poisson-disc фильтр для равномерного распределения

---

### `_sample_triangle(triangle: np.ndarray, count: int, jitter: float = 0.0) -> np.ndarray`

Генерирует точки внутри треугольника.

**Параметры:**
- `triangle` — `np.ndarray`, shape `(3, 3)` — вершины треугольника
- `count` — количество точек
- `jitter` — коэффициент случайного смещения (0.0 — равномерная сетка)

**Возвращает:**
- `np.ndarray`, shape `(count', 3)` — точки внутри треугольника (count' может отличаться при jitter > 0 из-за клиппинга)

**Алгоритм:**
- Использует барицентрические координаты: `P = A + u*(B-A) + v*(C-A)`, где `u, v >= 0` и `u + v <= 1`
- При `jitter = 0` точки располагаются равномерно по треугольнику
- При `jitter > 0` к барицентрическим координатам добавляется случайное возмущение

---

### `_poisson_disc_filter(points: np.ndarray, radius: float, random_seed: int) -> np.ndarray`

Жадный алгоритм Poisson-disc сэмплинга.

**Параметры:**
- `points` — `np.ndarray`, shape `(N, 3)` — входные точки
- `radius` — минимальное расстояние между точками
- `random_seed` — сид

**Возвращает:**
- `np.ndarray`, shape `(K, 3)` — отфильтрованные точки, где `K <= N`

**Алгоритм:**
1. Случайно выбирается начальная точка
2. Итеративно добавляются точки, находящиеся на расстоянии >= radius от всех уже выбранных
3. Используется `scipy.spatial.KDTree` (или numpy-реализация) для эффективного поиска ближайших соседей

---

### `compute_transforms(points: np.ndarray, mesh_data: dict, scale_min: float = 0.5, scale_max: float = 2.0, scale_map: Optional[bpy.types.Image] = None, scale_channel: str = "VALUE", scale_map_influence: float = 1.0, rotation_min: float = 0.0, rotation_max: float = 360.0, rotation_map: Optional[bpy.types.Image] = None, rotation_channel: str = "VALUE", rotation_map_influence: float = 1.0, align_to_normal: bool = True, random_seed: int = 0) -> list[dict]`

Вычисляет трансформации (location, rotation, scale) для каждой точки.

**Параметры:**
- `points` — `np.ndarray`, shape `(K, 3)` — координаты точек
- `mesh_data` — словарь от `get_mesh_data()`
- `scale_min`, `scale_max` — диапазон масштаба
- `scale_map` — текстура масштаба или `None`
- `scale_channel` — канал текстуры масштаба
- `scale_map_influence` — сила влияния карты масштаба (0.0–1.0)
- `rotation_min`, `rotation_max` — диапазон поворота в градусах
- `rotation_map` — текстура поворота или `None`
- `rotation_channel` — канал текстуры поворота
- `rotation_map_influence` — сила влияния карты поворота (0.0–1.0)
- `align_to_normal` — выравнивать по нормали поверхности
- `random_seed` — сид

**Возвращает:**
- Список словарей, каждый вида:
  ```python
  {
      "location": Vector,   # mathutils.Vector (3D)
      "rotation": Euler,    # mathutils.Euler (XYZ)
      "scale": Vector,      # mathutils.Vector (3D)
  }
  ```

---

### `_transform_points(points: np.ndarray, matrix: np.ndarray) -> np.ndarray`

Применяет 4x4 матрицу трансформации к набору 3D-точек.

**Параметры:**
- `points` — `np.ndarray`, shape `(N, 3)` — row-векторы точек
- `matrix` — `np.ndarray`, shape `(4, 4)` — матрица трансформации (row-major)

**Возвращает:**
- `np.ndarray`, shape `(N, 3)` — трансформированные точки

**Формула:** `transformed = homogenous @ matrix.T`, где `homogenous = [x, y, z, 1]`

---

### `_transform_normal(normal: np.ndarray, matrix: np.ndarray) -> np.ndarray`

Трансформирует нормаль матрицей 4x4 (без учёта переноса).

**Параметры:**
- `normal` — `np.ndarray`, shape `(3,)` — row-вектор нормали
- `matrix` — `np.ndarray`, shape `(4, 4)` — матрица трансформации

**Возвращает:**
- `np.ndarray`, shape `(3,)` — трансформированная и нормализованная нормаль

**Формула:** `normal' = (inv(R)^T @ normal.reshape(3,1)).flatten()`, где `R = matrix[:3, :3]`

---

### `create_scatter_objects(source_obj: bpy.types.Object, transforms: list, collection_name: str = "Scatter_Result") -> bpy.types.Collection`

Создаёт дубликаты source-объекта в указанной коллекции.

**Параметры:**
- `source_obj` — исходный объект для дублирования
- `transforms` — список трансформаций от `compute_transforms()`
- `collection_name` — имя целевой коллекции

**Возвращает:**
- `bpy.types.Collection` — коллекция с созданными объектами

---

### `run_scatter(settings) -> bool`

Запускает полный процесс рассеивания на основе настроек.

**Параметры:**
- `settings` — объект с атрибутами `ScatterSettings` (PropertyGroup)

**Возвращает:**
- `True` при успехе, `False` при ошибке

**Исключения:**
- `ValueError` — если `source_object` или `target_object` не заданы

---

## Модуль `texture_processor.py` — Обработка текстур

### `load_texture_data(image: bpy.types.Image) -> Optional[np.ndarray]`

Загружает пиксельные данные текстуры в numpy-массив.

**Параметры:**
- `image` — объект `bpy.types.Image`

**Возвращает:**
- `np.ndarray`, shape `(H, W, 4)` — RGBA-данные текстуры, dtype `float64`
- `None`, если `image is None`

---

### `sample_texture(texture_data: np.ndarray, uv: Tuple[float, float], channel: str = "VALUE", mode: str = "LINEAR") -> float`

Сэмплирует значение текстуры в заданной UV-точке.

**Параметры:**
- `texture_data` — `np.ndarray`, shape `(H, W, C)` — данные текстуры
- `uv` — `(u, v)` координаты в диапазоне [0, 1]
- `channel` — канал: `"R"`, `"G"`, `"B"`, `"A"`, `"VALUE"`
- `mode` — режим интерполяции: `"LINEAR"` (билинейная) или `"NEAREST"`

**Возвращает:**
- `float` — значение текстуры в диапазоне [0, 1]

**Алгоритм:**
- При `mode="LINEAR"` — билинейная интерполяция между 4 соседними пикселями
- При `mode="NEAREST"` — выбор ближайшего пикселя
- UV-координаты циклически заворачиваются (wrap)

---

### `_extract_channel(data: np.ndarray, channel: str) -> np.ndarray`

Извлекает одноканальные данные из многоканальной текстуры.

**Параметры:**
- `data` — `np.ndarray`, shape `(H, W, C)`
- `channel` — `"R"`, `"G"`, `"B"`, `"A"`, `"VALUE"`

**Возвращает:**
- `np.ndarray`, shape `(H, W)` — одноканальные данные

**Примечание:** Для `"VALUE"` вычисляется средняя яркость: `(R + G + B) / 3`

---

### `get_texture_resolution(image: bpy.types.Image) -> Tuple[int, int]`

Возвращает разрешение текстуры.

**Параметры:**
- `image` — объект `bpy.types.Image`

**Возвращает:**
- `(width, height)` в пикселях, или `(0, 0)` если `image is None`

---

### `generate_preview_texture(width: int = 256, height: int = 256) -> np.ndarray`

Генерирует тестовую текстуру (шахматная доска) для предварительного просмотра.

**Параметры:**
- `width`, `height` — размеры текстуры

**Возвращает:**
- `np.ndarray`, shape `(H, W, 4)` — RGBA-данные с шахматным паттерном 4x4

---

## Модуль `operators.py` — Операторы

### `PARAMETRICSCATTER_OT_scatter`

Запускает процесс параметрического рассеивания.

- **bl_idname:** `parametric_scatter.scatter`
- **Вызов:** `bpy.ops.parametric_scatter.scatter()`
- **poll:** требует `context.scene.parametric_scatter.source_object` и `target_object`

### `PARAMETRICSCATTER_OT_clear_scatter`

Удаляет все объекты в целевой коллекции рассеивания.

- **bl_idname:** `parametric_scatter.clear_scatter`
- **Параметры:** `collection_name` (StringProperty, default: `"Scatter_Result"`)
- **Вызов:** `bpy.ops.parametric_scatter.clear_scatter(collection_name="Scatter_Result")`

### `PARAMETRICSCATTER_OT_create_test_objects`

Создаёт тестовые Source (сфера) и Target (плоскость) объекты.

- **bl_idname:** `parametric_scatter.create_test_objects`
- **Параметры:**
  - `plane_size` (FloatProperty, default: 5.0)
  - `sphere_radius` (FloatProperty, default: 0.2)

---

## Модуль `__init__.py` — ScatterSettings (PropertyGroup)

### `ScatterSettings`

Настройки рассеивания, сохраняемые в blend-файле.

| Свойство | Тип | По умолчанию | Описание |
|----------|-----|-------------|----------|
| `source_object` | PointerProperty | None | Source-объект |
| `target_object` | PointerProperty | None | Target-объект |
| `density_map` | PointerProperty | None | Карта плотности |
| `scale_map` | PointerProperty | None | Карта масштаба |
| `rotation_map` | PointerProperty | None | Карта поворота |
| `density` | IntProperty | 50 | Плотность (1–1000) |
| `density_multiplier` | FloatProperty | 1.0 | Множитель плотности (0.0–10.0) |
| `scale_min` | FloatProperty | 0.5 | Мин. масштаб (0.01–10.0) |
| `scale_max` | FloatProperty | 2.0 | Макс. масштаб (0.01–10.0) |
| `scale_map_influence` | FloatProperty | 1.0 | Влияние карты масштаба (0.0–1.0) |
| `rotation_min` | FloatProperty | 0.0 | Мин. поворот (0–360) |
| `rotation_max` | FloatProperty | 360.0 | Макс. поворот (0–360) |
| `rotation_map_influence` | FloatProperty | 1.0 | Влияние карты поворота (0.0–1.0) |
| `align_to_normal` | BoolProperty | True | Выравнивание по нормали |
| `random_seed` | IntProperty | 0 | Сид (0–9999) |
| `collection_name` | StringProperty | "Scatter_Result" | Имя коллекции |
| `density_channel` | EnumProperty | "VALUE" | Канал плотности |
| `scale_channel` | EnumProperty | "VALUE" | Канал масштаба |
| `rotation_channel` | EnumProperty | "VALUE" | Канал поворота |
| `use_poisson_disc` | BoolProperty | False | Poisson-disc фильтр |
| `poisson_radius` | FloatProperty | 0.5 | Радиус Poisson (0.01–10.0) |
| `jitter` | FloatProperty | 0.0 | Jitter (0.0–1.0) |

---

## Модуль `ui_panel.py` — UI-панель

### `PARAMETRICSCATTER_PT_main`

Основная панель Parametric Scatter в 3D Viewport.

- **bl_idname:** `PARAMETRICSCATTER_PT_main`
- **bl_space_type:** `VIEW_3D`
- **bl_region_type:** `UI`
- **bl_category:** `Scatter`
- **bl_label:** `Parametric Scatter`

Содержит:
1. **Source & Target** — выбор объектов
2. **Density** — настройки плотности + карта
3. **Scale** — настройки масштаба + карта
4. **Rotation** — настройки поворота + карта
5. **Advanced** — Poisson-disc, Jitter, Seed
6. **Actions** — кнопки Scatter, Clear, Create Test Objects
