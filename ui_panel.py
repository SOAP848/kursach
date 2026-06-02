"""
ui_panel.py — Пользовательский интерфейс Parametric Scatter
=============================================================
Панель во вкладке View3D > Sidebar > Scatter.
"""

from __future__ import annotations

# Ленивый импорт bpy — моки подставляются в conftest.py
try:
    import bpy
    from bpy.types import Panel
except ImportError:
    Panel = object


# ---------------------------------------------------------------------------
# Панель
# ---------------------------------------------------------------------------

class PARAMETRICSCATTER_PT_main(Panel):
    """Основная панель Parametric Scatter в 3D Viewport."""

    bl_label = "Parametric Scatter"
    bl_idname = "PARAMETRICSCATTER_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Scatter"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        """Отрисовка UI панели."""
        layout = self.layout
        settings = context.scene.parametric_scatter

        # ---- Source & Target ----
        box = layout.box()
        box.label(text="Objects", icon="OBJECT_DATA")

        col = box.column(align=True)
        col.prop(settings, "source_object", text="Source")
        col.prop(settings, "target_object", text="Target")

        # ---- Density ----
        box = layout.box()
        box.label(text="Density", icon="MOD_PARTICLES")

        col = box.column(align=True)
        col.prop(settings, "density")
        col.prop(settings, "density_multiplier", slider=True)

        col.separator()
        col.label(text="Density Map:")
        col.prop(settings, "density_map", text="")
        if settings.density_map:
            col.prop(settings, "density_channel", text="Channel")

        # ---- Scale ----
        box = layout.box()
        box.label(text="Scale", icon="FULLSCREEN_ENTER")

        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(settings, "scale_min", text="Min")
        row.prop(settings, "scale_max", text="Max")

        col.separator()
        col.label(text="Scale Map:")
        col.prop(settings, "scale_map", text="")
        if settings.scale_map:
            col.prop(settings, "scale_channel", text="Channel")
            col.prop(settings, "scale_map_influence", slider=True)

        # ---- Rotation ----
        box = layout.box()
        box.label(text="Rotation", icon="ORIENTATION_GIMBAL")

        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(settings, "rotation_min", text="Min")
        row.prop(settings, "rotation_max", text="Max")

        col.separator()
        col.label(text="Rotation Map:")
        col.prop(settings, "rotation_map", text="")
        if settings.rotation_map:
            col.prop(settings, "rotation_channel", text="Channel")
            col.prop(settings, "rotation_map_influence", slider=True)

        # ---- Alignment ----
        box = layout.box()
        box.label(text="Alignment", icon="SNAP_NORMAL")

        col = box.column(align=True)
        col.prop(settings, "align_to_normal")

        # ---- Advanced ----
        box = layout.box()
        box.label(text="Advanced", icon="SETTINGS")

        col = box.column(align=True)
        col.prop(settings, "use_poisson_disc")
        if settings.use_poisson_disc:
            col.prop(settings, "poisson_radius")
        col.prop(settings, "jitter", slider=True)
        col.prop(settings, "random_seed")

        # ---- Output ----
        box = layout.box()
        box.label(text="Output", icon="OUTLINER_COLLECTION")

        col = box.column(align=True)
        col.prop(settings, "collection_name", text="Collection")

        # ---- Action Buttons ----
        layout.separator()

        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator(
            "parametric_scatter.scatter",
            text="Scatter",
            icon="PARTICLE_POINT",
        )

        row = layout.row(align=True)
        row.scale_y = 1.0
        row.operator(
            "parametric_scatter.clear_scatter",
            text="Clear",
            icon="TRASH",
        )

        layout.separator()
        layout.operator(
            "parametric_scatter.create_test_objects",
            text="Create Test Objects",
            icon="MESH_CUBE",
        )


# ---------------------------------------------------------------------------
# Регистрация
# ---------------------------------------------------------------------------

CLASSES = [
    PARAMETRICSCATTER_PT_main,
]


def register():
    """Регистрирует UI-классы."""
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    """Отменяет регистрацию UI-классов."""
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)