# Архитектура Parametric Scatter

## Общая структура

```
parametric_scatter/
├── __init__.py              # Регистрация аддона, ScatterSettings (PropertyGroup)
├── blender_manifest.toml    # Манифест для Blender 4.2+ Extensions
├── scatter_core.py          # Ядро: геометрия, генерация точек, трансформации
├── texture_processor.py     # Загрузка и сэмплирование текстур
├── operators.py             # Операторы Scatter / Clear / Create Test Objects
├── ui_panel.py              # UI-панель в 3D Viewport
├── README.md                # Документация пользователя
├── docs/
│   ├── architecture.md      # Архитектура и диаграммы (данный файл)
│   └── api.md               # API-документация
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Фикстуры и моки для тестирования
│   ├── test_texture_processor.py
│   ├── test_scatter_core.py
│   └── test_integration.py
├── .bandit                  # Конфигурация SAST-анализатора bandit
├── requirements-dev.txt     # Зависимости для разработки
└── Makefile                 # Цели: test, lint, security, docs
```

## Диаграмма компонентов

```mermaid
graph TB
    subgraph "Blender UI Layer"
        UI[ui_panel.py<br/>PARAMETRICSCATTER_PT_main]
        OPS[operators.py<br/>PARAMETRICSCATTER_OT_scatter<br/>PARAMETRICSCATTER_OT_clear_scatter<br/>PARAMETRICSCATTER_OT_create_test_objects]
    end

    subgraph "Settings Layer"
        SETTINGS[__init__.py<br/>ScatterSettings PropertyGroup]
    end

    subgraph "Core Layer"
        SCATTER[scatter_core.py<br/>get_mesh_data<br/>generate_points<br/>compute_transforms<br/>create_scatter_objects<br/>run_scatter]
        TEXTURE[texture_processor.py<br/>load_texture_data<br/>sample_texture<br/>_extract_channel]
    end

    subgraph "External"
        BPY[bpy — Blender Python API]
        NP[numpy]
    end

    UI -->|"draw()"| SETTINGS
    OPS -->|"execute()"| SCATTER
    OPS -->|"execute()"| SETTINGS
    SCATTER -->|"get_mesh_data()"| BPY
    SCATTER -->|"load_texture_data()"| TEXTURE
    SCATTER -->|"sample_texture()"| TEXTURE
    SCATTER -->|"create_scatter_objects()"| BPY
    SCATTER --> NP
    TEXTURE --> NP
```

## Диаграмма потока данных (Data Flow)

```mermaid
sequenceDiagram
    participant User as Пользователь
    participant UI as ui_panel.py
    participant OPS as operators.py
    participant CORE as scatter_core.py
    participant TEX as texture_processor.py
    participant BPY as Blender API

    User->>UI: Настраивает параметры
    UI->>SETTINGS: Сохраняет в PropertyGroup
    User->>OPS: Нажимает "Scatter"
    OPS->>CORE: run_scatter(settings)

    CORE->>BPY: get_mesh_data(target_obj)
    BPY-->>CORE: vertices, faces, normals, areas

    alt density_map задана
        CORE->>TEX: load_texture_data(density_map)
        TEX-->>CORE: texture_array
    end

    CORE->>CORE: generate_points(mesh_data, density, ...)
    Note over CORE: _sample_triangle() + Poisson-disc filter

    alt scale_map задана
        CORE->>TEX: load_texture_data(scale_map)
        TEX-->>CORE: scale_texture
    end

    alt rotation_map задана
        CORE->>TEX: load_texture_data(rotation_map)
        TEX-->>CORE: rotation_texture
    end

    CORE->>CORE: compute_transforms(points, ...)
    Note over CORE: _transform_points(), _transform_normal()

    CORE->>BPY: create_scatter_objects(source, transforms)
    BPY-->>CORE: collection

    CORE-->>OPS: success
    OPS-->>User: Отчёт в UI
```

## Диаграмма классов (моки для тестирования)

```mermaid
classDiagram
    class MockVector {
        -_seq: tuple
        +length: float
        +dot(other) float
        +cross(other) MockVector
        +normalized() MockVector
        +rotation_difference(target) MockQuaternion
        +to_track_quat(track, up) MockQuaternion
    }

    class MockEuler {
        -_angles: tuple
        +order: str
        +to_matrix() MockMatrix
    }

    class MockQuaternion {
        +w, x, y, z: float
        +to_matrix() MockMatrix
    }

    class MockMatrix {
        -_data: np.ndarray
        +Identity(size) MockMatrix
        +Rotation(angle, size, axis) MockMatrix
        +to_euler() MockEuler
    }

    class MockObject {
        +name: str
        +type: str
        +matrix_world: MockMatrix
        +location: MockVector
        +rotation_euler: MockEuler
        +scale: MockVector
        +evaluated_get() MockObject
        +to_mesh() MockMesh
        +copy() MockObject
    }

    class MockMesh {
        +vertices: list[MockMeshVertex]
        +polygons: list[MockMeshPolygon]
        +uv_layers: MagicMock
    }

    class MockCollection {
        +name: str
        +objects: list
        +link(obj) void
    }

    MockObject --> MockMatrix
    MockObject --> MockVector
    MockObject --> MockEuler
    MockObject --> MockMesh
    MockEuler --> MockMatrix
    MockQuaternion --> MockMatrix
    MockMesh --> MockMeshVertex
    MockMesh --> MockMeshPolygon
```

## Диаграмма состояний оператора Scatter

```mermaid
stateDiagram-v2
    [*] --> IDLE: Аддон загружен

    IDLE --> VALIDATING: Нажата кнопка Scatter
    VALIDATING --> ERROR_SOURCE: source_object is None
    VALIDATING --> ERROR_TARGET: target_object is None
    VALIDATING --> ERROR_MESH: target не MESH
    VALIDATING --> SCATTERING: Валидация пройдена

    SCATTERING --> GET_MESH: get_mesh_data()
    GET_MESH --> GENERATE: generate_points()
    GENERATE --> TRANSFORM: compute_transforms()
    TRANSFORM --> CREATE: create_scatter_objects()
    CREATE --> SUCCESS: Объекты созданы

    ERROR_SOURCE --> IDLE
    ERROR_TARGET --> IDLE
    ERROR_MESH --> IDLE
    SUCCESS --> IDLE
```

## Зависимости модулей

| Модуль | Импортирует | Назначение |
|--------|-------------|------------|
| `__init__.py` | `bpy`, `scatter_core`, `texture_processor`, `ui_panel`, `operators` | Регистрация, PropertyGroup |
| `scatter_core.py` | `bpy`, `mathutils`, `numpy`, `texture_processor` | Ядро алгоритма |
| `texture_processor.py` | `bpy`, `numpy` | Обработка текстур |
| `operators.py` | `bpy`, `scatter_core` | Операторы |
| `ui_panel.py` | `bpy` | UI-панель |
