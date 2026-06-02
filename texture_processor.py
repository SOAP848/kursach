
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

# Ленивый импорт bpy — моки подставляются в conftest.py
try:
    import bpy
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Загрузка текстуры
# ---------------------------------------------------------------------------

def load_texture_data(image: bpy.types.Image) -> Optional[np.ndarray]:

    if image is None:
        return None

    # Принудительно обновляем данные изображения
    if image.size[0] == 0 or image.size[1] == 0:
        return None

    width = image.size[0]
    height = image.size[1]

    # Получаем пиксели как плоский массив float
    pixels = np.array(image.pixels, dtype=np.float64)
    if pixels.size == 0:
        return None

    # Определяем число каналов
    # Blender всегда хранит RGBA (4 канала), но Float-изображения
    # могут иметь 1 канал
    if image.is_float and image.channels == 1:
        expected = width * height
        if pixels.size != expected:
            return None
        pixels = pixels.reshape((height, width, 1))
    else:
        expected = width * height * 4
        if pixels.size != expected:
            return None
        pixels = pixels.reshape((height, width, 4))

    return pixels


# ---------------------------------------------------------------------------
# Сэмплирование
# ---------------------------------------------------------------------------

def sample_texture(
    texture_data: np.ndarray,
    uv: Tuple[float, float],
    channel: str = "VALUE",
    interpolation: str = "LINEAR",
) -> float:

    if texture_data is None:
        return 1.0

    height, width, channels = texture_data.shape
    u, v = uv

    # Циклическая адресация (wrap)
    u = u - np.floor(u)
    v = v - np.floor(v)

    if interpolation == "NEAREST":
        x = int(round(u * (width - 1)))
        y = int(round(v * (height - 1)))
        x = np.clip(x, 0, width - 1)
        y = np.clip(y, 0, height - 1)
        pixel = texture_data[y, x]
    else:
        # Билинейная интерполяция
        x = u * (width - 1)
        y = v * (height - 1)

        x0 = int(np.floor(x))
        y0 = int(np.floor(y))
        x1 = min(x0 + 1, width - 1)
        y1 = min(y0 + 1, height - 1)

        fx = x - x0
        fy = y - y0

        # Четыре соседних пикселя
        p00 = texture_data[y0, x0]
        p10 = texture_data[y0, x1]
        p01 = texture_data[y1, x0]
        p11 = texture_data[y1, x1]

        # Билинейная интерполяция
        top = p00 * (1 - fx) + p10 * fx
        bottom = p01 * (1 - fx) + p11 * fx
        pixel = top * (1 - fy) + bottom * fy

    # Извлекаем канал
    return _extract_channel(pixel, channel, channels)


def _extract_channel(
    pixel: np.ndarray, channel: str, num_channels: int
) -> float:

    if num_channels == 1:
        # Одноканальное изображение
        return float(np.clip(pixel[0], 0.0, 1.0))

    # Многоканальное (RGBA)
    channel_map = {"R": 0, "G": 1, "B": 2, "A": 3}

    if channel == "VALUE":
        # Среднее значение RGB (или яркость)
        if num_channels >= 3:
            val = 0.299 * pixel[0] + 0.587 * pixel[1] + 0.114 * pixel[2]
        else:
            val = float(pixel[0])
        return float(np.clip(val, 0.0, 1.0))

    idx = channel_map.get(channel, 0)
    if idx < num_channels:
        return float(np.clip(pixel[idx], 0.0, 1.0))
    return 1.0


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def get_texture_resolution(image: bpy.types.Image) -> Tuple[int, int]:

    if image is None:
        return 0, 0
    return image.size[0], image.size[1]


def generate_preview_texture(
    width: int = 256, height: int = 256
) -> np.ndarray:
    tiles_x = 8
    tiles_y = 8
    cell_w = width // tiles_x
    cell_h = height // tiles_y

    texture = np.ones((height, width, 4), dtype=np.float64)

    for y in range(height):
        for x in range(width):
            tile_x = x // cell_w
            tile_y = y // cell_h
            if (tile_x + tile_y) % 2 == 0:
                texture[y, x] = [0.2, 0.2, 0.2, 1.0]
            else:
                texture[y, x] = [0.8, 0.8, 0.8, 1.0]

    return texture