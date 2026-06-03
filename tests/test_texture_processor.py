"""
test_texture_processor.py — Unit-тесты для модуля texture_processor
====================================================================
Тестирует:
  - load_texture_data()
  - sample_texture() с разными каналами и режимами интерполяции
  - _extract_channel()
  - get_texture_resolution()
  - generate_preview_texture()
"""

from __future__ import annotations

import numpy as np
import pytest

from parametric_scatter import texture_processor as tp


class TestLoadTextureData:
    """Тесты загрузки текстур."""

    def test_load_none_returns_none(self):
        """load_texture_data(None) -> None."""
        assert tp.load_texture_data(None) is None

    def test_load_rgba_texture(self, mock_bpy):
        """Загрузка RGBA-текстуры возвращает массив (H, W, 4)."""
        image = mock_bpy.types.Image("Test", 64, 64, 4)
        data = tp.load_texture_data(image)
        assert data is not None
        assert data.shape == (64, 64, 4)
        assert data.dtype == np.float64

    def test_load_float_texture(self, mock_bpy):
        """Загрузка Float-текстуры возвращает массив (H, W, 1)."""
        image = mock_bpy.types.Image("TestFloat", 32, 32, 1)
        data = tp.load_texture_data(image)
        assert data is not None
        assert data.shape == (32, 32, 1)
        assert data.dtype == np.float64


class TestSampleTexture:
    """Тесты сэмплирования текстуры."""

    def test_sample_none_returns_one(self):
        """sample_texture(None, ...) -> 1.0."""
        val = tp.sample_texture(None, (0.5, 0.5))
        assert val == 1.0

    def test_sample_nearest(self, sample_texture_data):
        """NEAREST интерполяция возвращает точное значение пикселя."""
        # (0.1, 0.1) -> пиксель (0, 0) -> [1,1,1,1] -> VALUE = 1.0
        val = tp.sample_texture(
            sample_texture_data, (0.1, 0.1),
            channel="VALUE", interpolation="NEAREST",
        )
        assert val == pytest.approx(1.0)

        # (0.1, 0.6) -> пиксель (0, 2) -> [0,0,0,1] -> VALUE = 0.0
        val = tp.sample_texture(
            sample_texture_data, (0.1, 0.6),
            channel="VALUE", interpolation="NEAREST",
        )
        assert val == pytest.approx(0.0)

    def test_sample_linear(self, sample_texture_data):
        """LINEAR интерполяция возвращает промежуточные значения."""
        # Ровно на границе 4-х пикселей (0.5, 0.5) в текстуре 4x4
        val = tp.sample_texture(
            sample_texture_data, (0.5, 0.5),
            channel="VALUE", interpolation="LINEAR",
        )
        # Ожидаем среднее между 1.0 и 0.0
        assert 0.0 < val < 1.0

    def test_sample_red_channel(self, sample_texture_data):
        """Извлечение R-канала."""
        # Красный канал белого пикселя = 1.0
        val = tp.sample_texture(
            sample_texture_data, (0.1, 0.1),
            channel="R", interpolation="NEAREST",
        )
        assert val == pytest.approx(1.0)

    def test_sample_alpha_channel(self, sample_texture_data):
        """Извлечение A-канала."""
        val = tp.sample_texture(
            sample_texture_data, (0.1, 0.1),
            channel="A", interpolation="NEAREST",
        )
        assert val == pytest.approx(1.0)

    def test_sample_wrap_u(self, sample_texture_data):
        """Циклическая адресация по U (wrap)."""
        # u=1.1 -> u=0.1 -> тот же результат, что и (0.1, 0.1)
        val1 = tp.sample_texture(
            sample_texture_data, (0.1, 0.1),
            channel="VALUE", interpolation="NEAREST",
        )
        val2 = tp.sample_texture(
            sample_texture_data, (1.1, 0.1),
            channel="VALUE", interpolation="NEAREST",
        )
        assert val1 == val2

    def test_sample_wrap_v(self, sample_texture_data):
        """Циклическая адресация по V (wrap)."""
        val1 = tp.sample_texture(
            sample_texture_data, (0.1, 0.1),
            channel="VALUE", interpolation="NEAREST",
        )
        val2 = tp.sample_texture(
            sample_texture_data, (0.1, 1.1),
            channel="VALUE", interpolation="NEAREST",
        )
        assert val1 == val2

    def test_sample_negative_uv(self, sample_texture_data):
        """Отрицательные UV-координаты корректно обрабатываются (wrap)."""
        val = tp.sample_texture(
            sample_texture_data, (-0.1, -0.1),
            channel="VALUE", interpolation="NEAREST",
        )
        # После wrap: (-0.1) -> 0.9 -> пиксель (3, 3) -> 1.0
        assert val == pytest.approx(1.0)


class TestExtractChannel:
    """Тесты извлечения канала из пикселя."""

    @pytest.fixture
    def rgba_pixel(self):
        return np.array([0.2, 0.4, 0.6, 1.0], dtype=np.float64)

    @pytest.fixture
    def mono_pixel(self):
        return np.array([0.75], dtype=np.float64)

    def test_red(self, rgba_pixel):
        assert tp._extract_channel(rgba_pixel, "R", 4) == pytest.approx(0.2)

    def test_green(self, rgba_pixel):
        assert tp._extract_channel(rgba_pixel, "G", 4) == pytest.approx(0.4)

    def test_blue(self, rgba_pixel):
        assert tp._extract_channel(rgba_pixel, "B", 4) == pytest.approx(0.6)

    def test_alpha(self, rgba_pixel):
        assert tp._extract_channel(rgba_pixel, "A", 4) == pytest.approx(1.0)

    def test_value_rgba(self, rgba_pixel):
        """VALUE = 0.299*R + 0.587*G + 0.114*B."""
        expected = 0.299 * 0.2 + 0.587 * 0.4 + 0.114 * 0.6
        assert tp._extract_channel(rgba_pixel, "VALUE", 4) == pytest.approx(expected)

    def test_mono(self, mono_pixel):
        """Одноканальный пиксель."""
        assert tp._extract_channel(mono_pixel, "R", 1) == pytest.approx(0.75)
        assert tp._extract_channel(mono_pixel, "VALUE", 1) == pytest.approx(0.75)

    def test_clip_negative(self):
        """Клиппинг отрицательных значений."""
        pixel = np.array([-0.5, 0.0, 0.0, 1.0], dtype=np.float64)
        assert tp._extract_channel(pixel, "R", 4) == pytest.approx(0.0)

    def test_clip_overflow(self):
        """Клиппинг значений > 1.0."""
        pixel = np.array([1.5, 0.0, 0.0, 1.0], dtype=np.float64)
        assert tp._extract_channel(pixel, "R", 4) == pytest.approx(1.0)


class TestGetTextureResolution:
    """Тесты get_texture_resolution."""

    def test_none_returns_zero(self):
        assert tp.get_texture_resolution(None) == (0, 0)

    def test_valid_image(self, mock_bpy):
        image = mock_bpy.types.Image("Test", 1920, 1080, 4)
        assert tp.get_texture_resolution(image) == (1920, 1080)


class TestGeneratePreviewTexture:
    """Тесты generate_preview_texture."""

    def test_shape(self):
        tex = tp.generate_preview_texture(256, 256)
        assert tex.shape == (256, 256, 4)

    def test_values_in_range(self):
        tex = tp.generate_preview_texture(64, 64)
        assert tex.min() >= 0.0
        assert tex.max() <= 1.0

    def test_checkerboard_pattern(self):
        """Проверяем, что шахматная доска имеет 2 разных цвета."""
        tex = tp.generate_preview_texture(16, 16)
        unique_colors = np.unique(tex.reshape(-1, 4), axis=0)
        assert len(unique_colors) == 2  # чёрный и белый

    def test_alpha_is_one(self):
        """Альфа-канал всегда 1.0."""
        tex = tp.generate_preview_texture(16, 16)
        assert np.all(tex[:, :, 3] == 1.0)
