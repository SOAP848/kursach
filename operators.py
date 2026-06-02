from __future__ import annotations

import traceback

from . import scatter_core

# Ленивый импорт bpy — моки подставляются в conftest.py до загрузки модуля
try:
    import bpy
    from bpy.types import Operator
    from bpy.props import StringProperty, FloatProperty
    from mathutils import Vector
except ImportError:
    Operator = object
    StringProperty = lambda **kw: ""
    FloatProperty = lambda **kw: 0.0
    Vector = lambda *a, **kw: None


# ---------------------------------------------------------------------------
# Оператор рассеивания
# ---------------------------------------------------------------------------

class PARAMETRICSCATTER_OT_scatter(Operator):

    bl_idname = "parametric_scatter.scatter"
    bl_label = "Scatter Objects"
    bl_description = "Запустить рассеивание объектов по поверхности"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        settings = getattr(context.scene, "parametric_scatter", None)
        if settings is None:
            return False
        return (
            settings.source_object is not None
            and settings.target_object is not None
        )

    def execute(self, context):
        settings = context.scene.parametric_scatter

        try:
            scatter_core.run_scatter(settings)
            self.report(
                {"INFO"},
                f"Рассеивание завершено. Результат в коллекции "
                f"'{settings.collection_name}'.",
            )
            return {"FINISHED"}
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        except Exception as e:
            self.report({"ERROR"}, f"Неожиданная ошибка: {e}")
            traceback.print_exc()
            return {"CANCELLED"}


# ---------------------------------------------------------------------------
# Оператор очистки
# ---------------------------------------------------------------------------

class PARAMETRICSCATTER_OT_clear_scatter(Operator):
    """Удаляет все объекты в целевой коллекции рассеивания."""

    bl_idname = "parametric_scatter.clear_scatter"
    bl_label = "Clear Scatter"
    bl_description = "Удалить все рассеянные объекты"
    bl_options = {"REGISTER", "UNDO"}

    collection_name: StringProperty(
        name="Collection Name",
        description="Имя коллекции для очистки",
        default="Scatter_Result",
    )

    @classmethod
    def poll(cls, context):
        settings = getattr(context.scene, "parametric_scatter", None)
        if settings is None:
            return False
        return settings.collection_name in bpy.data.collections

    def execute(self, context):
        settings = getattr(context.scene, "parametric_scatter", None)
        collection_name = (
            settings.collection_name
            if settings is not None
            else self.collection_name
        )

        if collection_name not in bpy.data.collections:
            self.report({"WARNING"}, f"Коллекция '{collection_name}' не найдена.")
            return {"CANCELLED"}

        collection = bpy.data.collections[collection_name]

        # Удаляем все объекты в коллекции
        objects_to_remove = list(collection.objects)
        for obj in objects_to_remove:
            bpy.data.objects.remove(obj, do_unlink=True)

        # Удаляем коллекцию
        bpy.data.collections.remove(collection)

        self.report({"INFO"}, f"Коллекция '{collection_name}' удалена.")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Оператор создания тестовых объектов
# ---------------------------------------------------------------------------

class PARAMETRICSCATTER_OT_create_test_objects(Operator):
    bl_idname = "parametric_scatter.create_test_objects"
    bl_label = "Create Test Objects"
    bl_description = "Создать тестовые Source (сфера) и Target (плоскость) объекты"
    bl_options = {"REGISTER", "UNDO"}

    plane_size: FloatProperty(
        name="Plane Size",
        description="Размер целевой плоскости",
        default=5.0,
        min=1.0,
        max=100.0,
    )

    sphere_radius: FloatProperty(
        name="Sphere Radius",
        description="Радиус source-сферы",
        default=0.2,
        min=0.01,
        max=10.0,
    )

    def execute(self, context):
        # Удаляем старые тестовые объекты, если есть
        for obj_name in ["Source_Sphere", "Target_Plane"]:
            if obj_name in bpy.data.objects:
                obj = bpy.data.objects[obj_name]
                bpy.data.objects.remove(obj, do_unlink=True)

        # Создаём Target — плоскость
        bpy.ops.mesh.primitive_plane_add(
            size=self.plane_size,
            location=(0.0, 0.0, 0.0),
        )
        target_obj = context.active_object
        target_obj.name = "Target_Plane"

        # Создаём Source — сферу
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=self.sphere_radius,
            location=(0.0, 0.0, 2.0),  # над плоскостью
        )
        source_obj = context.active_object
        source_obj.name = "Source_Sphere"

        # Настраиваем аддон
        settings = context.scene.parametric_scatter
        settings.source_object = source_obj
        settings.target_object = target_obj
        settings.density = 50
        settings.scale_min = 0.3
        settings.scale_max = 0.8
        settings.collection_name = "Scatter_Result"

        self.report(
            {"INFO"},
            "Созданы Source_Sphere и Target_Plane. Нажмите Scatter!",
        )
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Регистрация
# ---------------------------------------------------------------------------

CLASSES = [
    PARAMETRICSCATTER_OT_scatter,
    PARAMETRICSCATTER_OT_clear_scatter,
    PARAMETRICSCATTER_OT_create_test_objects,
]


def register():

    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():

    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)