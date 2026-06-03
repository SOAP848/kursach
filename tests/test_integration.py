from __future__ import annotations

import sys
import unittest

# Проверяем, запущены ли мы внутри Blender (не pytest-мок из conftest)
try:
    import bpy

    IN_BLENDER = not getattr(bpy, "is_mock", False)
except ImportError:
    IN_BLENDER = False

# Имя аддона зависит от того, как он установлен:
# - как extension: bl_ext.user_default.parametric_scatter
# - как addon: parametric_scatter
ADDON_NAME = "parametric_scatter"
if IN_BLENDER:
    for addon in bpy.context.preferences.addons:
        if ADDON_NAME in addon.module:
            ADDON_NAME = addon.module
            break


def skip_if_not_blender(func):
    """Декоратор: пропустить тест, если не в Blender."""
    return unittest.skipUnless(IN_BLENDER, "Требуется Blender")(func)


@unittest.skipUnless(IN_BLENDER, "Требуется Blender")
class TestAddonRegistration(unittest.TestCase):
    """Тесты регистрации аддона."""

    def setUp(self):
        """Включаем аддон перед каждым тестом."""
        if ADDON_NAME not in bpy.context.preferences.addons:
            bpy.ops.preferences.addon_enable(module=ADDON_NAME)

    def test_addon_enabled(self):
        """Аддон должен быть включён."""
        self.assertIn(
            ADDON_NAME,
            bpy.context.preferences.addons,
        )

    def test_property_group_exists(self):
        """PropertyGroup должна быть зарегистрирована на сцене."""
        self.assertTrue(hasattr(bpy.types.Scene, "parametric_scatter"))

    def test_operators_exist(self):
        """Операторы должны быть зарегистрированы."""
        self.assertTrue(hasattr(bpy.ops, "parametric_scatter"))
        for op_id in ("scatter", "clear_scatter", "create_test_objects"):
            self.assertTrue(
                hasattr(bpy.ops.parametric_scatter, op_id),
                f"Оператор parametric_scatter.{op_id} не найден",
            )

    def test_panel_exists(self):
        """UI-панель должна быть зарегистрирована."""
        self.assertTrue(
            hasattr(bpy.types, "PARAMETRICSCATTER_PT_main"),
        )


@unittest.skipUnless(IN_BLENDER, "Требуется Blender")
class TestCreateTestObjects(unittest.TestCase):
    """Тесты создания тестовых объектов."""

    def setUp(self):
        """Очищаем сцену."""
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)

        if ADDON_NAME not in bpy.context.preferences.addons:
            bpy.ops.preferences.addon_enable(module=ADDON_NAME)

    def test_create_test_objects(self):
        """Создание тестовых объектов."""
        bpy.ops.parametric_scatter.create_test_objects(
            plane_size=5.0,
            sphere_radius=0.2,
        )

        # Проверяем, что объекты созданы
        self.assertIn("Source_Sphere", bpy.data.objects)
        self.assertIn("Target_Plane", bpy.data.objects)

        # Проверяем настройки аддона
        settings = bpy.context.scene.parametric_scatter
        self.assertEqual(settings.source_object.name, "Source_Sphere")
        self.assertEqual(settings.target_object.name, "Target_Plane")
        self.assertEqual(settings.density, 50)


@unittest.skipUnless(IN_BLENDER, "Требуется Blender")
class TestScatterOperation(unittest.TestCase):
    """Тесты полного цикла рассеивания."""

    def setUp(self):
        """Подготовка сцены."""
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)

        if ADDON_NAME not in bpy.context.preferences.addons:
            bpy.ops.preferences.addon_enable(module=ADDON_NAME)

        # Создаём тестовые объекты
        bpy.ops.mesh.primitive_plane_add(size=5.0, location=(0, 0, 0))
        self.target = bpy.context.active_object
        self.target.name = "TestTarget"

        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(0, 0, 2))
        self.source = bpy.context.active_object
        self.source.name = "TestSource"

        # Настраиваем аддон
        settings = bpy.context.scene.parametric_scatter
        settings.source_object = self.source
        settings.target_object = self.target
        settings.density = 30
        settings.scale_min = 0.3
        settings.scale_max = 0.8
        settings.use_poisson_disc = False
        settings.collection_name = "TestScatterResult"

    def test_scatter_creates_objects(self):
        """Рассеивание создаёт объекты в коллекции."""
        bpy.ops.parametric_scatter.scatter()

        self.assertIn("TestScatterResult", bpy.data.collections)
        collection = bpy.data.collections["TestScatterResult"]
        self.assertGreater(len(collection.objects), 0)

    def test_scatter_objects_have_varied_transforms(self):
        """Объекты имеют разные трансформации."""
        bpy.ops.parametric_scatter.scatter()

        collection = bpy.data.collections["TestScatterResult"]
        scales = set()
        for obj in collection.objects:
            scales.add(tuple(round(s, 2) for s in obj.scale))

        # Должно быть больше одного уникального масштаба
        self.assertGreater(len(scales), 1)

    def test_scatter_objects_on_surface(self):
        """Объекты находятся на поверхности (Z ≈ 0)."""
        bpy.ops.parametric_scatter.scatter()

        collection = bpy.data.collections["TestScatterResult"]
        for obj in collection.objects:
            self.assertAlmostEqual(obj.location.z, 0.0, delta=0.1)

    def test_clear_removes_objects(self):
        """Очистка удаляет коллекцию и объекты."""
        bpy.ops.parametric_scatter.scatter()
        self.assertIn("TestScatterResult", bpy.data.collections)

        bpy.ops.parametric_scatter.clear_scatter(
            collection_name="TestScatterResult"
        )
        self.assertNotIn("TestScatterResult", bpy.data.collections)


@unittest.skipUnless(IN_BLENDER, "Требуется Blender")
class TestScatterWithTextures(unittest.TestCase):
    """Тесты рассеивания с текстурными картами."""

    def setUp(self):
        """Подготовка сцены с текстурами."""
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)

        if ADDON_NAME not in bpy.context.preferences.addons:
            bpy.ops.preferences.addon_enable(module=ADDON_NAME)

        # Создаём тестовую текстуру
        import numpy as np
        pixels = np.zeros((64, 64, 4), dtype=np.float32)
        pixels[:32, :, :] = 1.0  # верхняя половина белая
        pixels[32:, :, :] = 0.0  # нижняя половина чёрная
        pixels = pixels.flatten()

        self.density_image = bpy.data.images.new(
            "TestDensityMap", width=64, height=64, alpha=True,
        )
        self.density_image.pixels = pixels.tolist()

        # Создаём объекты
        bpy.ops.mesh.primitive_plane_add(size=5.0, location=(0, 0, 0))
        self.target = bpy.context.active_object
        self.target.name = "TexturedTarget"

        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(0, 0, 2))
        self.source = bpy.context.active_object
        self.source.name = "TexturedSource"

        # Настройки
        settings = bpy.context.scene.parametric_scatter
        settings.source_object = self.source
        settings.target_object = self.target
        settings.density = 100
        settings.density_map = self.density_image
        settings.density_channel = "VALUE"
        settings.use_poisson_disc = False
        settings.collection_name = "TexturedScatter"

    def tearDown(self):
        """Очистка текстур."""
        if self.density_image:
            bpy.data.images.remove(self.density_image)

    def test_scatter_with_density_map(self):
        """Рассеивание с картой плотности работает."""
        try:
            bpy.ops.parametric_scatter.scatter()
        except Exception as e:
            self.fail(f"Рассеивание с картой плотности упало: {e}")

        self.assertIn("TexturedScatter", bpy.data.collections)
        collection = bpy.data.collections["TexturedScatter"]
        self.assertGreater(len(collection.objects), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
