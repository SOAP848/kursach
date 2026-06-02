"""
conftest.py — Pytest-фикстуры и моки для тестирования
=======================================================
Мокирует Blender API (bpy, mathutils) на уровне модуля,
чтобы тесты можно было запускать вне Blender.

ВАЖНО: Моки устанавливаются ДО импорта parametric_scatter,
чтобы перехватить import bpy внутри пакета.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import numpy as np
import pytest
import sys


# ===========================================================================
# Моки для mathutils — устанавливаются в sys.modules до всех импортов
# ===========================================================================

class MockVector:
    """Мок-замена mathutils.Vector."""

    def __init__(self, seq=(0.0, 0.0, 0.0)):
        self._seq = tuple(float(v) for v in seq)

    def __getitem__(self, idx):
        return self._seq[idx]

    def __setitem__(self, idx, val):
        lst = list(self._seq)
        lst[idx] = float(val)
        self._seq = tuple(lst)

    def __len__(self):
        return len(self._seq)

    def __repr__(self):
        return f"Vector({self._seq})"

    @property
    def length(self):
        return float(np.linalg.norm(self._seq))

    def dot(self, other):
        return sum(a * b for a, b in zip(self._seq, other._seq))

    def rotation_difference(self, target):
        return MockQuaternion()

    def to_track_quat(self, track, up):
        return MockQuaternion()

    def normalized(self):
        norm = self.length
        if norm == 0:
            return MockVector(self._seq)
        return MockVector(tuple(v / norm for v in self._seq))

    def cross(self, other):
        v1 = np.array(self._seq)
        v2 = np.array(other._seq)
        return MockVector(np.cross(v1, v2))

    def __sub__(self, other):
        return MockVector(tuple(a - b for a, b in zip(self._seq, other._seq)))

    def __add__(self, other):
        return MockVector(tuple(a + b for a, b in zip(self._seq, other._seq)))

    def __mul__(self, scalar):
        return MockVector(tuple(v * scalar for v in self._seq))

    def __neg__(self):
        return MockVector(tuple(-v for v in self._seq))


class MockEuler:
    """Мок-замена mathutils.Euler."""

    def __init__(self, angles=(0.0, 0.0, 0.0), order="XYZ"):
        self._angles = tuple(float(a) for a in angles)
        self.order = order

    def __getitem__(self, idx):
        return self._angles[idx]

    def __repr__(self):
        return f"Euler({self._angles})"

    def to_matrix(self):
        return MockMatrix.Identity(3)


class MockQuaternion:
    """Мок-замена mathutils.Quaternion."""

    def __init__(self, seq=(1.0, 0.0, 0.0, 0.0)):
        self.w, self.x, self.y, self.z = seq

    def to_matrix(self):
        return MockMatrix.Identity(3)


class MockMatrix:
    """Мок-замена mathutils.Matrix."""

    def __init__(self, data=None):
        if data is not None:
            self._data = np.array(data, dtype=np.float64)
        else:
            self._data = np.eye(4, dtype=np.float64)

    @staticmethod
    def Identity(size):
        m = MockMatrix()
        m._data = np.eye(size, dtype=np.float64)
        return m

    @staticmethod
    def Rotation(angle, size, axis):
        m = MockMatrix()
        c = np.cos(angle)
        s = np.sin(angle)
        if axis == "Z":
            m._data = np.array([
                [c, -s, 0],
                [s, c, 0],
                [0, 0, 1],
            ], dtype=np.float64)
        else:
            m._data = np.eye(size, dtype=np.float64)
        return m

    def __matmul__(self, other):
        result = MockMatrix()
        if isinstance(other, MockMatrix):
            result._data = self._data @ other._data
        else:
            result._data = self._data @ np.array(other._data)
        return result

    def to_euler(self):
        return MockEuler()

    def __getitem__(self, idx):
        return self._data[idx]

    def __repr__(self):
        return f"Matrix({self._data})"


# ===========================================================================
# Моки для bpy — устанавливаются в sys.modules до всех импортов
# ===========================================================================

class MockImage:
    """Мок-замена bpy.types.Image."""

    def __init__(self, name="TestImage", width=256, height=256, channels=4):
        self.name = name
        self.size = (width, height)
        self.channels = channels
        self.is_float = channels == 1
        rng = np.random.RandomState(42)
        if channels == 1:
            self.pixels = rng.rand(width * height).tolist()
        else:
            self.pixels = rng.rand(width * height * 4).tolist()


class MockUVLoop:
    """Мок-замена UV-координаты loop."""

    def __init__(self, uv=(0.0, 0.0)):
        self.uv = uv


class MockMeshPolygon:
    """Мок-замена mesh polygon."""

    def __init__(self, vertices, normal=(0, 0, 1), area=1.0, loop_indices=None):
        self.vertices = vertices
        self.loop_indices = loop_indices if loop_indices is not None else list(vertices)
        self.normal = MockVector(normal)
        self.area = area


class MockMeshVertex:
    """Мок-замена mesh vertex."""

    def __init__(self, co=(0, 0, 0)):
        self.co = MockVector(co)


class MockMesh:
    """Мок-замена bpy.types.Mesh."""

    def __init__(self):
        self.vertices = []
        self.polygons = []
        self.uv_layers = MagicMock()
        self.uv_layers.active = None


class MockObject:
    """Мок-замена bpy.types.Object."""

    def __init__(self, name="TestObj", obj_type="MESH"):
        self.name = name
        self.type = obj_type
        self.matrix_world = MockMatrix.Identity(4)
        self.active_material = None
        self.data = None
        self.location = MockVector((0, 0, 0))
        self.rotation_euler = MockEuler()
        self.scale = MockVector((1, 1, 1))

    def evaluated_get(self, depsgraph):
        return self

    def to_mesh(self):
        mesh = MockMesh()
        mesh.vertices = [
            MockMeshVertex((0, 0, 0)),
            MockMeshVertex((1, 0, 0)),
            MockMeshVertex((0, 1, 0)),
        ]
        mesh.polygons = [
            MockMeshPolygon(
                vertices=[0, 1, 2],
                normal=(0, 0, 1),
                area=0.5,
                loop_indices=[0, 1, 2],
            ),
        ]
        uv_layer = MagicMock()
        uv_layer.data = [
            MockUVLoop((0.0, 0.0)),
            MockUVLoop((1.0, 0.0)),
            MockUVLoop((0.0, 1.0)),
        ]
        mesh.uv_layers.active = MagicMock()
        mesh.uv_layers.active.data = uv_layer.data
        mesh.uv_layers.active.name = "UVMap"
        return mesh

    def to_mesh_clear(self):
        pass

    def copy(self):
        new = MockObject(self.name + "_copy", self.type)
        new.data = self.data
        return new


class MockCollection:
    """Мок-замена bpy.types.Collection."""

    def __init__(self, name="TestCollection"):
        self.name = name
        self.objects = []

    def link(self, obj):
        self.objects.append(obj)

    def __iter__(self):
        return iter(self.objects)

    def __len__(self):
        return len(self.objects)


# ---------------------------------------------------------------------------
# Устанавливаем моки в sys.modules ДО импорта parametric_scatter
# ---------------------------------------------------------------------------

class _MockBPYTypes:
    Image = MockImage
    Object = MockObject
    Collection = MockCollection


class _MockBPYOpsMesh:
    @staticmethod
    def primitive_plane_add(**kwargs):
        pass

    @staticmethod
    def primitive_uv_sphere_add(**kwargs):
        pass


class _MockBPYOps:
    mesh = _MockBPYOpsMesh()


class _MockBPYCollectionDict:
    """Словарь коллекций, поддерживающий 'in', '[]' и '.new()'."""

    def __init__(self):
        self._store = {}

    def __contains__(self, name):
        return name in self._store

    def __getitem__(self, name):
        return self._store[name]

    def __setitem__(self, name, col):
        self._store[name] = col

    def new(self, name):
        col = MockCollection(name)
        self._store[name] = col
        return col

    def get(self, name, default=None):
        return self._store.get(name, default)


class _MockBPYData:
    collections = _MockBPYCollectionDict()
    objects = {}
    images = {}


class _MockBPYContext:
    scene = MagicMock()
    scene.parametric_scatter = MagicMock()

    @staticmethod
    def evaluated_depsgraph_get():
        return MagicMock()


class _MockBPYPrefs:
    addons = {}


# Создаём мок-модуль bpy через type(sys) — это настоящий модуль,
# а не экземпляр класса, что важно для корректной работы import bpy
_MOCK_BPY = type(sys)("bpy")
_MOCK_BPY.is_mock = True
_MOCK_BPY.types = _MockBPYTypes()
_MOCK_BPY.context = _MockBPYContext()
_MOCK_BPY.ops = _MockBPYOps()
_MOCK_BPY.data = _MockBPYData()
_MOCK_BPY.preferences = _MockBPYPrefs()
_MOCK_BPY.utils = MagicMock()
_MOCK_BPY.utils.register_class = MagicMock()
_MOCK_BPY.utils.unregister_class = MagicMock()

_MOCK_MATHUTILS = type(sys)("mathutils")
_MOCK_MATHUTILS.Vector = MockVector
_MOCK_MATHUTILS.Euler = MockEuler
_MOCK_MATHUTILS.Matrix = MockMatrix
_MOCK_MATHUTILS.Quaternion = MockQuaternion

# Не перезаписываем, если уже есть (например, в Blender)
if "bpy" not in sys.modules:
    sys.modules["bpy"] = _MOCK_BPY
if "mathutils" not in sys.modules:
    sys.modules["mathutils"] = _MOCK_MATHUTILS


# ===========================================================================
# Pytest fixtures
# ===========================================================================

@pytest.fixture
def mock_bpy():
    """Возвращает мок-объект bpy."""
    return _MOCK_BPY


@pytest.fixture
def sample_mesh_data():
    """Фикстура с тестовыми данными геометрии поверхности (квадрат 2x2)."""
    vertices = np.array([
        [0.0, 0.0, 0.0],
        [2.0, 0.0, 0.0],
        [2.0, 2.0, 0.0],
        [0.0, 2.0, 0.0],
    ], dtype=np.float64)

    return {
        "vertices": vertices,
        "faces": [[0, 1, 2, 3]],
        "face_uvs": [[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]],
        "centers": np.array([[1.0, 1.0, 0.0]], dtype=np.float64),
        "normals": np.array([[0.0, 0.0, 1.0]], dtype=np.float64),
        "areas": np.array([4.0], dtype=np.float64),
        "uv_layer": "UVMap",
    }


@pytest.fixture
def sample_texture_data():
    """Фикстура с тестовыми данными текстуры 4x4 (шахматная доска)."""
    data = np.zeros((4, 4, 4), dtype=np.float64)
    data[:2, :2] = [1.0, 1.0, 1.0, 1.0]
    data[:2, 2:] = [0.0, 0.0, 0.0, 1.0]
    data[2:, :2] = [0.0, 0.0, 0.0, 1.0]
    data[2:, 2:] = [1.0, 1.0, 1.0, 1.0]
    return data