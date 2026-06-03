from __future__ import annotations

import math
import random
import sys
from typing import Optional, Tuple

import numpy as np

from . import texture_processor

# Ленивый импорт bpy/mathutils — моки подставляются в conftest.py
try:
    import bpy
    from mathutils import Vector, Matrix, Euler
except ImportError:
    # Fallback: берём из sys.modules (могли быть установлены conftest.py)
    bpy = sys.modules.get("bpy")
    if bpy is None:
        bpy = type(sys)("bpy")  # заглушка
    mu = sys.modules.get("mathutils")
    if mu is not None:
        Vector = mu.Vector
        Matrix = mu.Matrix
        Euler = mu.Euler
    else:
        Vector = lambda *a, **kw: None
        Matrix = lambda *a, **kw: None
        Euler = lambda *a, **kw: None


# ---------------------------------------------------------------------------
# Геометрия поверхности
# ---------------------------------------------------------------------------

def get_mesh_data(obj: bpy.types.Object) -> Optional[dict]:

    if obj is None or obj.type != "MESH":
        return None

    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()

    if not mesh.polygons:
        eval_obj.to_mesh_clear()
        return None

    # Мировая матрица
    world_mat = np.array(obj.matrix_world)

    # Вершины в мировых координатах
    verts_local = np.array([v.co for v in mesh.vertices], dtype=np.float64)
    verts_world = _transform_points(verts_local, world_mat)

    # Полигоны
    faces = []
    face_uvs = []
    centers = []
    normals = []
    areas = []

    uv_layer_data = None
    if mesh.uv_layers.active:
        uv_layer_data = mesh.uv_layers.active.data

    for poly in mesh.polygons:
        vert_indices = list(poly.vertices)
        faces.append(vert_indices)

        # Центр полигона
        poly_verts = verts_world[vert_indices]
        centers.append(poly_verts.mean(axis=0))

        # Нормаль (мировая)
        normal_local = np.array(poly.normal, dtype=np.float64)
        normal_world = _transform_normal(normal_local, world_mat)
        normals.append(normal_world)

        areas.append(_polygon_area_world(poly_verts))

        if uv_layer_data is not None:
            uvs = [
                (uv_layer_data[loop_idx].uv[0], uv_layer_data[loop_idx].uv[1])
                for loop_idx in poly.loop_indices
            ]
            face_uvs.append(uvs)
        else:
            face_uvs.append(None)

    # UV-слой
    uv_layer_name = None
    if mesh.uv_layers.active:
        uv_layer_name = mesh.uv_layers.active.name

    eval_obj.to_mesh_clear()

    return {
        "vertices": verts_world,
        "faces": faces,
        "face_uvs": face_uvs,
        "centers": np.array(centers, dtype=np.float64),
        "normals": np.array(normals, dtype=np.float64),
        "areas": np.array(areas, dtype=np.float64),
        "uv_layer": uv_layer_name,
    }


def _transform_points(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:

    ones = np.ones((points.shape[0], 1), dtype=np.float64)
    homogenous = np.hstack([points, ones])  # (N, 4)
    # homogenous @ matrix.T -> (N, 4)
    transformed = homogenous @ matrix.T
    return transformed[:, :3] / transformed[:, 3:4]


def _polygon_area_world(verts: np.ndarray) -> float:
    if len(verts) < 3:
        return 0.0

    origin = verts[0]
    area = 0.0
    for i in range(1, len(verts) - 1):
        e1 = verts[i] - origin
        e2 = verts[i + 1] - origin
        area += np.linalg.norm(np.cross(e1, e2)) * 0.5
    return float(area)


def _transform_normal(normal: np.ndarray, matrix: np.ndarray) -> np.ndarray:

    rot_mat = matrix[:3, :3]
    # (inv(rot_mat).T @ normal.reshape(3, 1)).flatten()
    inv_rot = np.linalg.inv(rot_mat)
    normal_transformed = (inv_rot.T @ normal.reshape(3, 1)).flatten()
    norm = np.linalg.norm(normal_transformed)
    if norm > 0:
        normal_transformed /= norm
    return normal_transformed


# ---------------------------------------------------------------------------
# Генерация точек
# ---------------------------------------------------------------------------

def generate_points(
    mesh_data: dict,
    density: int,
    density_multiplier: float = 1.0,
    density_map: Optional[bpy.types.Image] = None,
    density_channel: str = "VALUE",
    use_poisson_disc: bool = True,
    poisson_radius: float = 0.3,
    jitter: float = 0.3,
    random_seed: int = 0,
) -> Tuple[np.ndarray, np.ndarray]:

    random.seed(random_seed)
    np.random.seed(random_seed)

    centers = mesh_data["centers"]
    areas = mesh_data["areas"]
    total_area = areas.sum()

    if total_area <= 0:
        return (
            np.empty((0, 3), dtype=np.float64),
            np.empty((0,), dtype=np.int32),
        )

    # Загружаем карту плотности, если есть
    density_texture = None
    if density_map is not None:
        density_texture = texture_processor.load_texture_data(density_map)

    # Вычисляем количество точек на полигон
    points_per_face = []
    for i, (center, area) in enumerate(zip(centers, areas)):
        # Базовое количество точек для этого полигона
        count = max(1, int(area * density * density_multiplier))

        # Модуляция картой плотности
        if density_texture is not None:
            uv = _project_uv(center, mesh_data, i)
            tex_value = texture_processor.sample_texture(
                density_texture, uv, channel=density_channel
            )
            count = max(0, int(count * tex_value))

        points_per_face.append(count)

    # Генерируем точки на каждом полигоне
    all_points = []
    all_face_indices = []

    for i, count in enumerate(points_per_face):
        if count <= 0:
            continue

        face = mesh_data["faces"][i]
        face_verts = mesh_data["vertices"][face]

        if len(face) == 3:
            # Треугольник
            pts = _sample_triangle(face_verts, count, jitter)
        elif len(face) == 4:
            # Четырёхугольник — разбиваем на 2 треугольника
            tri1 = face_verts[:3]
            tri2 = face_verts[[0, 2, 3]]
            pts1 = _sample_triangle(tri1, count // 2 + count % 2, jitter)
            pts2 = _sample_triangle(tri2, count // 2, jitter)
            pts = np.vstack([pts1, pts2]) if len(pts1) and len(pts2) else (
                pts1 if len(pts1) else pts2
            )
        else:
            # N-угольник — триангуляция через центр
            poly_center = centers[i]
            pts_list = []
            for j in range(len(face)):
                v0 = face_verts[j]
                v1 = face_verts[(j + 1) % len(face)]
                tri = np.array([poly_center, v0, v1], dtype=np.float64)
                tri_pts = _sample_triangle(tri, max(1, count // len(face)), jitter)
                pts_list.append(tri_pts)
            pts = np.vstack(pts_list) if pts_list else np.empty((0, 3), dtype=np.float64)

        if len(pts):
            all_points.append(pts)
            all_face_indices.append(np.full(len(pts), i, dtype=np.int32))

    if not all_points:
        return (
            np.empty((0, 3), dtype=np.float64),
            np.empty((0,), dtype=np.int32),
        )

    points = np.vstack(all_points)
    face_indices = np.concatenate(all_face_indices)

    # Poisson-disc фильтрация
    if use_poisson_disc and poisson_radius > 0 and len(points) > 1:
        points, face_indices = _poisson_disc_filter(
            points, poisson_radius, random_seed, face_indices
        )

    return points, face_indices


def _sample_triangle(
    tri_verts: np.ndarray, count: int, jitter: float
) -> np.ndarray:
    if count <= 0:
        return np.empty((0, 3), dtype=np.float64)

    v0, v1, v2 = tri_verts

    # Базовые точки на равномерной сетке в барицентрических координатах
    grid_size = max(1, int(math.ceil(math.sqrt(count))))
    u = np.linspace(0, 1, grid_size + 1)[:-1]
    v = np.linspace(0, 1, grid_size + 1)[:-1]
    uu, vv = np.meshgrid(u, v)
    uu = uu.flatten()
    vv = vv.flatten()

    # Отбрасываем точки вне треугольника (u + v > 1)
    mask = (uu + vv) <= 1
    uu = uu[mask]
    vv = vv[mask]

    # Jitter
    if jitter > 0:
        step = 1.0 / grid_size
        uu += np.random.uniform(-step * jitter, step * jitter, size=uu.shape)
        vv += np.random.uniform(-step * jitter, step * jitter, size=vv.shape)
        # Клиппинг
        uu = np.clip(uu, 0, 1)
        vv = np.clip(vv, 0, 1)
        mask2 = (uu + vv) <= 1
        uu = uu[mask2]
        vv = vv[mask2]

    # Конвертация в декартовы координаты
    ww = 1.0 - uu - vv
    points = (
        v0[np.newaxis, :] * ww[:, np.newaxis]
        + v1[np.newaxis, :] * uu[:, np.newaxis]
        + v2[np.newaxis, :] * vv[:, np.newaxis]
    )

    # Если точек больше, чем нужно — сэмплируем
    if len(points) > count:
        indices = np.random.choice(len(points), count, replace=False)
        points = points[indices]

    return points


def _poisson_disc_filter(
    points: np.ndarray,
    radius: float,
    seed: int,
    face_indices: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray]:

    if face_indices is None:
        face_indices = np.zeros(len(points), dtype=np.int32)

    if len(points) <= 1:
        return points, face_indices

    rng = np.random.RandomState(seed)
    order = rng.permutation(len(points))
    sorted_pts = points[order]
    sorted_faces = face_indices[order]

    accepted_pts = [sorted_pts[0]]
    accepted_faces = [sorted_faces[0]]
    radius_sq = radius * radius

    for pt, face_idx in zip(sorted_pts[1:], sorted_faces[1:]):
        dists = np.sum(
            (np.array(accepted_pts) - pt[np.newaxis, :]) ** 2, axis=1
        )
        if np.all(dists >= radius_sq):
            accepted_pts.append(pt)
            accepted_faces.append(face_idx)

    return (
        np.array(accepted_pts, dtype=np.float64),
        np.array(accepted_faces, dtype=np.int32),
    )


def _barycentric_coords(
    point: np.ndarray, tri_verts: np.ndarray
) -> Tuple[float, float, float]:
    a, b, c = tri_verts
    v0 = b - a
    v1 = c - a
    v2 = point - a
    d00 = np.dot(v0, v0)
    d01 = np.dot(v0, v1)
    d11 = np.dot(v1, v1)
    d20 = np.dot(v2, v0)
    d21 = np.dot(v2, v1)
    denom = d00 * d11 - d01 * d01
    if abs(denom) < 1e-12:
        return 1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w
    return float(u), float(v), float(w)


def _interpolate_uv(
    point: np.ndarray,
    face_verts: np.ndarray,
    face_uvs: list,
) -> Tuple[float, float]:
    if not face_uvs or len(face_uvs) != len(face_verts):
        return 0.5, 0.5

    if len(face_verts) == 3:
        w0, w1, w2 = _barycentric_coords(point, face_verts)
        u = w0 * face_uvs[0][0] + w1 * face_uvs[1][0] + w2 * face_uvs[2][0]
        v = w0 * face_uvs[0][1] + w1 * face_uvs[1][1] + w2 * face_uvs[2][1]
        return float(u), float(v)

    if len(face_verts) == 4:
        tri1 = face_verts[:3]
        tri2 = face_verts[[0, 2, 3]]
        uv1 = face_uvs[:3]
        uv2 = [face_uvs[0], face_uvs[2], face_uvs[3]]
        u1, v1 = _interpolate_uv(point, tri1, uv1)
        u2, v2 = _interpolate_uv(point, tri2, uv2)
        return (u1 + u2) * 0.5, (v1 + v2) * 0.5

    poly_center = face_verts.mean(axis=0)
    best_uv = (0.5, 0.5)
    best_dist = float("inf")
    for j in range(len(face_verts)):
        tri = np.array(
            [poly_center, face_verts[j], face_verts[(j + 1) % len(face_verts)]],
            dtype=np.float64,
        )
        uv_center = (
            (face_uvs[j][0] + face_uvs[(j + 1) % len(face_uvs)][0]) * 0.5,
            (face_uvs[j][1] + face_uvs[(j + 1) % len(face_uvs)][1]) * 0.5,
        )
        tri_uvs = [uv_center, face_uvs[j], face_uvs[(j + 1) % len(face_uvs)]]
        candidate = _interpolate_uv(point, tri, tri_uvs)
        dist = np.linalg.norm(point - tri.mean(axis=0))
        if dist < best_dist:
            best_dist = dist
            best_uv = candidate
    return best_uv


def _project_uv(
    point: np.ndarray, mesh_data: dict, face_index: int
) -> Tuple[float, float]:
    face_uvs_list = mesh_data.get("face_uvs")
    if not face_uvs_list:
        return 0.5, 0.5

    face_index = int(np.clip(face_index, 0, len(face_uvs_list) - 1))
    face_uvs = face_uvs_list[face_index]
    if face_uvs is None:
        return 0.5, 0.5

    face = mesh_data["faces"][face_index]
    face_verts = mesh_data["vertices"][face]
    return _interpolate_uv(point, face_verts, face_uvs)


# ---------------------------------------------------------------------------
# Трансформации
# ---------------------------------------------------------------------------

def compute_transforms(
    points: np.ndarray,
    mesh_data: dict,
    face_indices: Optional[np.ndarray] = None,
    scale_min: float = 0.5,
    scale_max: float = 2.0,
    scale_map: Optional[bpy.types.Image] = None,
    scale_channel: str = "VALUE",
    scale_map_influence: float = 1.0,
    rotation_min: float = 0.0,
    rotation_max: float = math.tau,
    rotation_map: Optional[bpy.types.Image] = None,
    rotation_channel: str = "VALUE",
    rotation_map_influence: float = 1.0,
    align_to_normal: bool = True,
    random_seed: int = 0,
) -> list:

    random.seed(random_seed)
    np.random.seed(random_seed)

    # Загружаем текстуры
    scale_texture = None
    if scale_map is not None:
        scale_texture = texture_processor.load_texture_data(scale_map)

    rotation_texture = None
    if rotation_map is not None:
        rotation_texture = texture_processor.load_texture_data(rotation_map)

    # Для каждой точки находим ближайший полигон (упрощённо — по центру)
    # В реальном сценарии нужно хранить индекс полигона для каждой точки
    centers = mesh_data["centers"]
    normals = mesh_data["normals"]

    if face_indices is None:
        face_indices = np.zeros(len(points), dtype=np.int32)

    transforms = []

    for i, pt in enumerate(points):
        face_idx = int(face_indices[i])
        # Позиция
        location = Vector(pt)

        # ---- Масштаб ----
        scale_val = random.uniform(scale_min, scale_max)

        if scale_texture is not None:
            uv = _project_uv(pt, mesh_data, face_idx)
            tex_val = texture_processor.sample_texture(
                scale_texture, uv, channel=scale_channel
            )
            # Интерполяция между random и текстурой
            tex_scale = scale_min + (scale_max - scale_min) * tex_val
            scale_val = scale_val * (1 - scale_map_influence) + tex_scale * scale_map_influence

        scale = Vector((scale_val, scale_val, scale_val))

        # ---- Поворот ----
        rot_angle = random.uniform(rotation_min, rotation_max)

        if rotation_texture is not None:
            uv = _project_uv(pt, mesh_data, face_idx)
            tex_val = texture_processor.sample_texture(
                rotation_texture, uv, channel=rotation_channel
            )
            tex_angle = rotation_min + (rotation_max - rotation_min) * tex_val
            rot_angle = rot_angle * (1 - rotation_map_influence) + tex_angle * rotation_map_influence

        # Поворот вокруг Z (вверх) + опционально выравнивание по нормали
        if align_to_normal:
            # Находим ближайшую нормаль
            dists = np.sum((centers - pt[np.newaxis, :]) ** 2, axis=1)
            nearest = np.argmin(dists)
            normal = Vector(normals[nearest])

            # Строим матрицу поворота: Z → normal
            up = Vector((0.0, 0.0, 1.0))
            if normal.length > 0 and abs(normal.dot(up)) < 0.9999:
                q = up.rotation_difference(normal)
                rot_mat = q.to_matrix()
            else:
                rot_mat = Matrix.Identity(3)

            # Дополнительный поворот вокруг локальной Z (rot_angle уже в радианах)
            rot_z = Matrix.Rotation(rot_angle, 3, "Z")
            rotation = (rot_mat @ rot_z).to_euler()
        else:
            rotation = Euler((0.0, 0.0, rot_angle), "XYZ")

        transforms.append({
            "location": location,
            "rotation": rotation,
            "scale": scale,
        })

    return transforms


# ---------------------------------------------------------------------------
# Создание объектов в сцене
# ---------------------------------------------------------------------------

def create_scatter_objects(
    source_obj: bpy.types.Object,
    transforms: list,
    collection_name: str = "Scatter_Result",
) -> bpy.types.Collection:

    # Создаём или получаем коллекцию
    if collection_name in bpy.data.collections:
        collection = bpy.data.collections[collection_name]
    else:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

    # Очищаем коллекцию
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    for tf in transforms:
        obj = source_obj.copy()
        obj.data = source_obj.data.copy()
        obj.location = tf["location"]
        obj.rotation_euler = tf["rotation"]
        obj.scale = tf["scale"]

        # Случайный оттенок для визуализации (опционально)
        if obj.active_material:
            pass  # можно добавить рандомизацию материала

        collection.objects.link(obj)

    return collection


# ---------------------------------------------------------------------------
# Главная функция рассеивания
# ---------------------------------------------------------------------------

def run_scatter(settings) -> bool:

    source = settings.source_object
    target = settings.target_object

    if not source or not target:
        raise ValueError("Source и Target объекты должны быть указаны.")

    # 1. Получаем геометрию
    mesh_data = get_mesh_data(target)
    if mesh_data is None:
        raise ValueError("Не удалось получить геометрию целевого объекта.")

    # 2. Генерируем точки
    points, face_indices = generate_points(
        mesh_data=mesh_data,
        density=settings.density,
        density_multiplier=settings.density_multiplier,
        density_map=settings.density_map,
        density_channel=settings.density_channel,
        use_poisson_disc=settings.use_poisson_disc,
        poisson_radius=settings.poisson_radius,
        jitter=settings.jitter,
        random_seed=settings.random_seed,
    )

    if len(points) == 0:
        raise ValueError("Не сгенерировано ни одной точки. Проверьте настройки плотности.")

    # 3. Вычисляем трансформации
    transforms = compute_transforms(
        points=points,
        mesh_data=mesh_data,
        face_indices=face_indices,
        scale_min=settings.scale_min,
        scale_max=settings.scale_max,
        scale_map=settings.scale_map,
        scale_channel=settings.scale_channel,
        scale_map_influence=settings.scale_map_influence,
        rotation_min=settings.rotation_min,
        rotation_max=settings.rotation_max,
        rotation_map=settings.rotation_map,
        rotation_channel=settings.rotation_channel,
        rotation_map_influence=settings.rotation_map_influence,
        align_to_normal=settings.align_to_normal,
        random_seed=settings.random_seed,
    )

    # 4. Создаём объекты
    create_scatter_objects(
        source_obj=source,
        transforms=transforms,
        collection_name=settings.collection_name,
    )

    return True
