import math

# Импорт bpy — ленивый, чтобы моки могли подставиться при тестировании
try:
    import bpy
    from bpy.props import (
        BoolProperty,
        FloatProperty,
        IntProperty,
        PointerProperty,
        StringProperty,
        EnumProperty,
    )
    from bpy.types import PropertyGroup, Panel, Operator, AddonPreferences

    _HAS_BPY = True
except ImportError:
    _HAS_BPY = False

from . import scatter_core, texture_processor, ui_panel, operators

bl_info = {
    "name": "Parametric Scatter",
    "author": "SOAP848",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Scatter",
    "description": (
        "Параметрическое размещение объектов с управлением "
        "плотностью, масштабом и поворотом по текстурным картам"
    ),
    "category": "Object",
}


# ---------------------------------------------------------------------------
# Property Groups
# ---------------------------------------------------------------------------

if _HAS_BPY:

    class ScatterSettings(PropertyGroup):
        """Настройки рассеивания, сохраняемые в blend-файле."""

        source_object: PointerProperty(
            name="Source Object",
            description="Объект, который будет рассеиваться",
            type=bpy.types.Object,
            poll=lambda self, obj: obj.type == "MESH",
        )

        target_object: PointerProperty(
            name="Target Object",
            description="Поверхность, по которой рассеиваются объекты",
            type=bpy.types.Object,
            poll=lambda self, obj: obj.type == "MESH",
        )

        density_map: PointerProperty(
            name="Density Map",
            description="Текстура для управления плотностью (RGB / Float)",
            type=bpy.types.Image,
        )

        scale_map: PointerProperty(
            name="Scale Map",
            description="Текстура для управления масштабом (RGB / Float)",
            type=bpy.types.Image,
        )

        rotation_map: PointerProperty(
            name="Rotation Map",
            description="Текстура для управления поворотом (RGB / Float)",
            type=bpy.types.Image,
        )

        # ---- Density ----
        density: IntProperty(
            name="Density",
            description="Количество объектов на единицу площади",
            default=10,
            min=1,
            max=1000,
        )

        density_multiplier: FloatProperty(
            name="Density Multiplier",
            description="Множитель плотности (применяется поверх карты)",
            default=1.0,
            min=0.0,
            max=10.0,
            soft_min=0.0,
            soft_max=5.0,
        )

        # ---- Scale ----
        scale_min: FloatProperty(
            name="Scale Min",
            description="Минимальный масштаб",
            default=0.5,
            min=0.01,
            max=10.0,
        )

        scale_max: FloatProperty(
            name="Scale Max",
            description="Максимальный масштаб",
            default=2.0,
            min=0.01,
            max=10.0,
        )

        scale_map_influence: FloatProperty(
            name="Scale Map Influence",
            description="Влияние карты масштаба (0 — только min/max, 1 — полное)",
            default=1.0,
            min=0.0,
            max=1.0,
            subtype="FACTOR",
        )

        # ---- Rotation ----
        rotation_min: FloatProperty(
            name="Rotation Min",
            description="Минимальный угол поворота (градусы)",
            default=0.0,
            min=-math.tau,
            max=math.tau,
            subtype="ANGLE",
        )

        rotation_max: FloatProperty(
            name="Rotation Max",
            description="Максимальный угол поворота (градусы)",
            default=math.tau,
            min=-math.tau,
            max=math.tau,
            subtype="ANGLE",
        )

        rotation_map_influence: FloatProperty(
            name="Rotation Map Influence",
            description="Влияние карты поворота (0 — только min/max, 1 — полное)",
            default=1.0,
            min=0.0,
            max=1.0,
            subtype="FACTOR",
        )

        # ---- Alignment ----
        align_to_normal: BoolProperty(
            name="Align to Normal",
            description="Выравнивать объекты по нормали поверхности",
            default=True,
        )

        random_seed: IntProperty(
            name="Random Seed",
            description="Сид генератора случайных чисел для воспроизводимости",
            default=0,
            min=0,
            max=999999,
        )

        # ---- Output ----
        collection_name: StringProperty(
            name="Collection",
            description="Имя коллекции для сгенерированных объектов",
            default="Scatter_Result",
        )

        # ---- Texture channel ----
        density_channel: EnumProperty(
            name="Density Channel",
            description="Канал текстуры плотности",
            items=[
                ("R", "Red", "Красный канал"),
                ("G", "Green", "Зелёный канал"),
                ("B", "Blue", "Синий канал"),
                ("A", "Alpha", "Альфа-канал"),
                ("VALUE", "Value", "Среднее значение (RGB→Float)"),
            ],
            default="VALUE",
        )

        scale_channel: EnumProperty(
            name="Scale Channel",
            description="Канал текстуры масштаба",
            items=[
                ("R", "Red", "Красный канал"),
                ("G", "Green", "Зелёный канал"),
                ("B", "Blue", "Синий канал"),
                ("A", "Alpha", "Альфа-канал"),
                ("VALUE", "Value", "Среднее значение (RGB→Float)"),
            ],
            default="VALUE",
        )

        rotation_channel: EnumProperty(
            name="Rotation Channel",
            description="Канал текстуры поворота",
            items=[
                ("R", "Red", "Красный канал"),
                ("G", "Green", "Зелёный канал"),
                ("B", "Blue", "Синий канал"),
                ("A", "Alpha", "Альфа-канал"),
                ("VALUE", "Value", "Среднее значение (RGB→Float)"),
            ],
            default="VALUE",
        )

        # ---- Advanced ----
        use_poisson_disc: BoolProperty(
            name="Poisson Disc Sampling",
            description="Использовать Poisson-disc сэмплинг для более равномерного распределения",
            default=True,
        )

        poisson_radius: FloatProperty(
            name="Poisson Radius",
            description="Минимальное расстояние между объектами (Poisson-disc)",
            default=0.3,
            min=0.01,
            max=10.0,
        )

        jitter: FloatProperty(
            name="Jitter",
            description="Величина случайного смещения от идеальной сетки",
            default=0.3,
            min=0.0,
            max=1.0,
            subtype="FACTOR",
        )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

if _HAS_BPY:
    CLASSES = [
        ScatterSettings,
        operators.PARAMETRICSCATTER_OT_scatter,
        operators.PARAMETRICSCATTER_OT_clear_scatter,
        operators.PARAMETRICSCATTER_OT_create_test_objects,
        ui_panel.PARAMETRICSCATTER_PT_main,
    ]

    def register():
        for cls in CLASSES:
            bpy.utils.register_class(cls)

        bpy.types.Scene.parametric_scatter = PointerProperty(type=ScatterSettings)

    def unregister():
        for cls in reversed(CLASSES):
            bpy.utils.unregister_class(cls)

        del bpy.types.Scene.parametric_scatter

    if __name__ == "__main__":
        register()