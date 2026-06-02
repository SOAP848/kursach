"""
test_scatter_core.py — Unit-тесты для модуля scatter_core
============================================================
Тестирует:
  - get_mesh_data()
  - generate_points() с разными параметрами
  - _sample_triangle()
  - _poisson_disc_filter()
  - compute_transforms()
  - create_scatter_objects()
  - run_scatter()
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from parametric_scatter import scatter_core as sc


class TestGetMeshData:
    """Тесты сбора геометрии поверхности."""

    def test_none_object_returns_none(self):
        assert sc.get_mesh_data(None) is None

    def test_non_mesh_returns_none(self, mock_bpy):
        obj = mock_bpy.types.Object("Empty", "EMPTY")
        assert sc.get_mesh_data(obj) is None

class TestSampleTriangle:
    """Тесты _sample_triangle()."""

    @pytest.fixture
    def triangle(self):
        return np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ], dtype=np.float64)

    def test_zero_count(self, triangle):
        """count=0 -> пустой массив."""
        pts = sc._sample_triangle(triangle, 0, 0.0)
        assert len(pts) == 0

    def test_single_point(self, triangle):
        """count=1 -> одна точка внутри треугольника."""
        pts = sc._sample_triangle(triangle, 1, 0.0)
        assert pts.shape == (1, 3)

    def test_all_points_inside(self, triangle):
        """Все точки должны быть внутри треугольника (u+v <= 1)."""
        pts = sc._sample_triangle(triangle, 100, 0.0)
        # Барицентрические координаты: w = 1 - u - v >= 0
        for pt in pts:
            # Точка должна быть выпуклой комбинацией вершин
            # Проверяем через барицентрические координаты
            v0, v1, v2 = triangle
            # Решаем: pt = v0 + u*(v1-v0) + v*(v2-v0)
            u_vec = v1 - v0
            v_vec = v2 - v0
            w_vec = pt - v0
            # Для треугольника на плоскости XY
            if abs(u_vec[0]) > 1e-6:
                u = w_vec[0] / u_vec[0]
                v = (w_vec[1] - u * u_vec[1]) / v_vec[1] if abs(v_vec[1]) > 1e-6 else 0
            else:
                u = w_vec[1] / u_vec[1] if abs(u_vec[1]) > 1e-6 else 0
                v = (w_vec[0] - u * u_vec[0]) / v_vec[0] if abs(v_vec[0]) > 1e-6 else 0
            assert u >= -1e-6
            assert v >= -1e-6
            assert u + v <= 1.0 + 1e-6

    def test_jitter_produces_variation(self, triangle):
        """Jitter > 0 даёт разные результаты при разных сидах."""
        np.random.seed(0)
        pts1 = sc._sample_triangle(triangle, 50, 0.5)
        np.random.seed(1)
        pts2 = sc._sample_triangle(triangle, 50, 0.5)
        # Jitter может дать разное количество точек из-за клиппинга,
        # поэтому сравниваем только первые N точек, где N = min(len)
        n = min(len(pts1), len(pts2))
        assert n > 0, "Должна быть хотя бы одна точка для сравнения"
        assert not np.allclose(pts1[:n], pts2[:n])


class TestPoissonDiscFilter:
    """Тесты _poisson_disc_filter()."""

    def test_empty_or_single(self):
        pts, _ = sc._poisson_disc_filter(np.empty((0, 3)), 0.5, 0)
        assert len(pts) == 0
        pts, _ = sc._poisson_disc_filter(np.array([[0, 0, 0]]), 0.5, 0)
        assert len(pts) == 1

    def test_min_distance(self):
        """Все точки должны быть на расстоянии >= radius друг от друга."""
        rng = np.random.RandomState(42)
        points = rng.rand(100, 3) * 10
        filtered, _ = sc._poisson_disc_filter(points, 1.0, 42)

        for i in range(len(filtered)):
            for j in range(i + 1, len(filtered)):
                dist = np.linalg.norm(filtered[i] - filtered[j])
                assert dist >= 1.0 - 1e-6, (
                    f"Точки {i} и {j} на расстоянии {dist} < 1.0"
                )

    def test_reproducible(self):
        """Одинаковый seed -> одинаковый результат."""
        rng = np.random.RandomState(0)
        points = rng.rand(50, 3) * 5
        result1, _ = sc._poisson_disc_filter(points, 0.5, 123)
        result2, _ = sc._poisson_disc_filter(points, 0.5, 123)
        assert np.allclose(result1, result2)


class TestGeneratePoints:
    """Тесты generate_points()."""

    def test_empty_mesh_returns_empty(self):
        """Нулевая площадь -> пустой массив."""
        data = {
            "vertices": np.empty((0, 3)),
            "faces": [],
            "centers": np.empty((0, 3)),
            "normals": np.empty((0, 3)),
            "areas": np.array([0.0]),
            "uv_layer": None,
        }
        pts, _ = sc.generate_points(data, 10)
        assert len(pts) == 0

    def test_basic_generation(self, sample_mesh_data):
        """Базовая генерация точек на квадрате 2x2."""
        pts, _ = sc.generate_points(
            sample_mesh_data, density=10,
            use_poisson_disc=False, random_seed=42,
        )
        assert len(pts) > 0
        # Все точки должны быть на плоскости Z=0
        assert np.allclose(pts[:, 2], 0.0, atol=1e-6)

    def test_points_within_bounds(self, sample_mesh_data):
        """Точки должны быть в пределах квадрата [0,2]x[0,2]."""
        pts, _ = sc.generate_points(
            sample_mesh_data, density=50,
            use_poisson_disc=False, random_seed=0,
        )
        assert pts[:, 0].min() >= -0.1
        assert pts[:, 0].max() <= 2.1
        assert pts[:, 1].min() >= -0.1
        assert pts[:, 1].max() <= 2.1

    def test_density_multiplier(self, sample_mesh_data):
        """Увеличение множителя плотности даёт больше точек."""
        pts_low, _ = sc.generate_points(
            sample_mesh_data, density=10, density_multiplier=0.5,
            use_poisson_disc=False, random_seed=0,
        )
        pts_high, _ = sc.generate_points(
            sample_mesh_data, density=10, density_multiplier=2.0,
            use_poisson_disc=False, random_seed=0,
        )
        assert len(pts_high) >= len(pts_low)

    def test_poisson_disc_reduces_count(self, sample_mesh_data):
        """Poisson-disc фильтр уменьшает количество точек."""
        pts_no_poisson, _ = sc.generate_points(
            sample_mesh_data, density=100,
            use_poisson_disc=False, random_seed=42,
        )
        pts_poisson, _ = sc.generate_points(
            sample_mesh_data, density=100,
            use_poisson_disc=True, poisson_radius=0.5,
            random_seed=42,
        )
        assert len(pts_poisson) <= len(pts_no_poisson)

    def test_reproducible_seed(self, sample_mesh_data):
        """Одинаковый seed -> одинаковые точки."""
        pts1, _ = sc.generate_points(
            sample_mesh_data, density=20,
            use_poisson_disc=False, random_seed=999,
        )
        pts2, _ = sc.generate_points(
            sample_mesh_data, density=20,
            use_poisson_disc=False, random_seed=999,
        )
        assert np.allclose(pts1, pts2)


class TestComputeTransforms:
    """Тесты compute_transforms()."""

    @pytest.fixture
    def mesh_data(self):
        return {
            "vertices": np.array([
                [0, 0, 0], [2, 0, 0], [2, 2, 0], [0, 2, 0],
            ], dtype=np.float64),
            "faces": [[0, 1, 2, 3]],
            "face_uvs": [[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]],
            "centers": np.array([[1.0, 1.0, 0.0]], dtype=np.float64),
            "normals": np.array([[0.0, 0.0, 1.0]], dtype=np.float64),
            "areas": np.array([4.0], dtype=np.float64),
            "uv_layer": None,
        }

    def test_basic_transforms(self, mesh_data):
        """Базовая генерация трансформаций."""
        points = np.array([
            [0.5, 0.5, 0.0],
            [1.0, 1.0, 0.0],
            [1.5, 1.5, 0.0],
        ], dtype=np.float64)

        transforms = sc.compute_transforms(
            points, mesh_data,
            scale_min=0.5, scale_max=1.0,
            rotation_min=0, rotation_max=math.tau,
            align_to_normal=False,
            random_seed=42,
        )

        assert len(transforms) == 3
        for tf in transforms:
            assert "location" in tf
            assert "rotation" in tf
            assert "scale" in tf

class TestTransformPoints:
    """Тесты _transform_points()."""

    def test_identity_matrix(self):
        """Единичная матрица не меняет точки."""
        points = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float64)
        matrix = np.eye(4, dtype=np.float64)
        result = sc._transform_points(points, matrix)
        assert np.allclose(result, points)
    def test_scale(self):
        """Матрица масштабирования."""
        points = np.array([[1, 1, 1]], dtype=np.float64)
        matrix = np.array([
            [2, 0, 0, 0],
            [0, 3, 0, 0],
            [0, 0, 4, 0],
            [0, 0, 0, 1],
        ], dtype=np.float64)
        result = sc._transform_points(points, matrix)
        assert np.allclose(result, [[2, 3, 4]])


class TestTransformNormal:
    """Тесты _transform_normal()."""

    def test_identity(self):
        """Единичная матрица не меняет нормаль."""
        normal = np.array([0, 0, 1], dtype=np.float64)
        matrix = np.eye(4, dtype=np.float64)
        result = sc._transform_normal(normal, matrix)
        assert np.allclose(result, [0, 0, 1])

    def test_rotation(self):
        """Поворот нормали."""
        normal = np.array([0, 0, 1], dtype=np.float64)
        # Поворот на 90° вокруг X
        c = np.cos(np.pi / 2)
        s = np.sin(np.pi / 2)
        matrix = np.array([
            [1, 0, 0, 0],
            [0, c, -s, 0],
            [0, s, c, 0],
            [0, 0, 0, 1],
        ], dtype=np.float64)
        result = sc._transform_normal(normal, matrix)
        assert np.allclose(result, [0, -1, 0], atol=1e-6)


class TestRunScatter:
    """Тесты run_scatter()."""

    def test_missing_source_raises(self, mock_bpy):
        """Без source -> ValueError."""
        settings = MagicMock()
        settings.source_object = None
        settings.target_object = mock_bpy.types.Object("Target", "MESH")

        with pytest.raises(ValueError, match="Source"):
            sc.run_scatter(settings)

    def test_missing_target_raises(self, mock_bpy):
        """Без target -> ValueError."""
        settings = MagicMock()
        settings.source_object = mock_bpy.types.Object("Source", "MESH")
        settings.target_object = None

        with pytest.raises(ValueError, match="Target"):
            sc.run_scatter(settings)


# Нужен для MagicMock в test_run_scatter
from unittest.mock import MagicMock