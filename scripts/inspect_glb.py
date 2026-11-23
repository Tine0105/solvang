"""Inspect a .glb file: verify magic bytes, bounding box proportions, triangle count, meshes, and materials.

Usage:
    python scripts/inspect_glb.py app/static/models/ferrari.glb
"""
from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path
from typing import Any

NON_BODY_KEYWORDS = (
    'glass', 'window', 'windshield', 'tire', 'tyre', 'rubber', 'wheel', 'rim',
    'chrome', 'brake', 'caliper', 'disc', 'rotor', 'light', 'lamp', 'led',
    'headlight', 'taillight', 'turn_signal', 'projector', 'interior', 'seat',
    'leather', 'carpet', 'dashboard', 'steering', 'grille', 'grill', 'exhaust',
    'mirror_glass', 'plate', 'license', 'badge', 'emblem', 'logo', 'shadow',
    'floor', 'ground', 'plane', 'underbody', 'chassis_bottom',
)

BODY_HINT_KEYWORDS = (
    'body', 'paint', 'carpaint', 'car_paint', 'exterior', 'shell', 'coachwork', 'main_color', 'body_color',
)


def _mat_mul(a: list[float], b: list[float]) -> list[float]:
    out = [0.0] * 16
    for r in range(4):
        for c in range(4):
            out[c * 4 + r] = sum(a[k * 4 + r] * b[c * 4 + k] for k in range(4))
    return out


def _trs_to_mat(t: list[float] | None, r: list[float] | None, s: list[float] | None) -> list[float]:
    tx, ty, tz = t or (0.0, 0.0, 0.0)
    qx, qy, qz, qw = r or (0.0, 0.0, 0.0, 1.0)
    sx, sy, sz = s or (1.0, 1.0, 1.0)

    x2, y2, z2 = qx + qx, qy + qy, qz + qz
    xx, xy, xz = qx * x2, qx * y2, qx * z2
    yy, yz, zz = qy * y2, qy * z2, qz * z2
    wx, wy, wz = qw * x2, qw * y2, qw * z2

    return [
        (1.0 - (yy + zz)) * sx, (xy + wz) * sx, (xz - wy) * sx, 0.0,
        (xy - wz) * sy, (1.0 - (xx + zz)) * sy, (yz + wx) * sy, 0.0,
        (xz + wy) * sz, (yz - wx) * sz, (1.0 - (xx + yy)) * sz, 0.0,
        tx, ty, tz, 1.0,
    ]


def _transform_point(m: list[float], p: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = p
    return (
        m[0] * x + m[4] * y + m[8] * z + m[12],
        m[1] * x + m[5] * y + m[9] * z + m[13],
        m[2] * x + m[6] * y + m[10] * z + m[14],
    )


def inspect_glb(glb_path: str | Path) -> dict[str, Any]:
    path = Path(glb_path)
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError(f'File too small to be a valid GLB: {path}')

    magic, version, _total_len = struct.unpack('<4sII', data[:12])
    if magic != b'glTF':
        raise ValueError(f'Invalid GLB magic header in {path}: {magic!r}')

    offset = 12
    gltf: dict[str, Any] | None = None
    while offset + 8 <= len(data):
        chunk_len, chunk_type = struct.unpack('<I4s', data[offset:offset + 8])
        offset += 8
        chunk_data = data[offset:offset + chunk_len]
        offset += chunk_len
        if chunk_type == b'JSON':
            gltf = json.loads(chunk_data.decode('utf-8'))
            break

    if gltf is None:
        raise ValueError(f'No JSON chunk found in {path}')

    accessors = gltf.get('accessors', [])
    materials_raw = gltf.get('materials', [])
    materials = [m.get('name') or f'Material_{i}' for i, m in enumerate(materials_raw)]
    textures = gltf.get('textures', [])
    meshes_raw = gltf.get('meshes', [])
    nodes = gltf.get('nodes', [])

    # Compute triangle count & per-material surface/vertex weight
    poly_count = 0
    mat_weights: dict[str, float] = {m: 0.0 for m in materials}
    meshes_summary = []

    for i, mesh in enumerate(meshes_raw):
        m_name = mesh.get('name') or f'Mesh_{i}'
        prim_mats = []
        for p in mesh.get('primitives', []):
            mode = p.get('mode', 4)
            if mode != 4:
                continue
            idx_acc = p.get('indices')
            pos_acc = (p.get('attributes') or {}).get('POSITION')
            tris = 0
            if idx_acc is not None and 0 <= idx_acc < len(accessors):
                tris = (accessors[idx_acc].get('count') or 0) // 3
            elif pos_acc is not None and 0 <= pos_acc < len(accessors):
                tris = (accessors[pos_acc].get('count') or 0) // 3
            poly_count += tris

            bbox_vol = 1.0
            if pos_acc is not None and 0 <= pos_acc < len(accessors):
                pmin = accessors[pos_acc].get('min')
                pmax = accessors[pos_acc].get('max')
                if pmin and pmax and len(pmin) == 3 and len(pmax) == 3:
                    dx = abs(pmax[0] - pmin[0])
                    dy = abs(pmax[1] - pmin[1])
                    dz = abs(pmax[2] - pmin[2])
                    bbox_vol = max(0.01, dx * dy + dy * dz + dx * dz)

            mat_idx = p.get('material')
            if mat_idx is not None and 0 <= mat_idx < len(materials):
                mat_name = materials[mat_idx]
                prim_mats.append(mat_name)
                # Weight by triangle count * surface area estimate, penalize if mesh name looks non-body
                mesh_low = m_name.lower()
                penalty = 0.05 if any(k in mesh_low for k in NON_BODY_KEYWORDS) else 1.0
                bonus = 2.5 if any(k in mesh_low for k in ('body', 'exterior', 'shell', 'door', 'hood', 'bumper', 'fender')) else 1.0
                mat_weights[mat_name] = mat_weights.get(mat_name, 0.0) + (tris * bbox_vol * penalty * bonus)
        meshes_summary.append((m_name, prim_mats))

    # Traverse scene nodes to compute world bounding box
    global_min = [math.inf, math.inf, math.inf]
    global_max = [-math.inf, -math.inf, -math.inf]

    def visit_node(node_idx: int, parent_mat: list[float], depth: int = 0) -> None:
        if depth > 64 or not (0 <= node_idx < len(nodes)):
            return
        node = nodes[node_idx]
        if 'matrix' in node and len(node['matrix']) == 16:
            local_mat = [float(x) for x in node['matrix']]
        else:
            local_mat = _trs_to_mat(node.get('translation'), node.get('rotation'), node.get('scale'))
        world_mat = _mat_mul(parent_mat, local_mat)

        mesh_idx = node.get('mesh')
        if mesh_idx is not None and 0 <= mesh_idx < len(meshes_raw):
            for p in meshes_raw[mesh_idx].get('primitives', []):
                pos_acc = (p.get('attributes') or {}).get('POSITION')
                if pos_acc is not None and 0 <= pos_acc < len(accessors):
                    pmin = accessors[pos_acc].get('min')
                    pmax = accessors[pos_acc].get('max')
                    if pmin and pmax and len(pmin) == 3 and len(pmax) == 3:
                        corners = [
                            (pmin[0], pmin[1], pmin[2]), (pmin[0], pmin[1], pmax[2]),
                            (pmin[0], pmax[1], pmin[2]), (pmin[0], pmax[1], pmax[2]),
                            (pmax[0], pmin[1], pmin[2]), (pmax[0], pmin[1], pmax[2]),
                            (pmax[0], pmax[1], pmin[2]), (pmax[0], pmax[1], pmax[2]),
                        ]
                        for c in corners:
                            wx, wy, wz = _transform_point(world_mat, c)
                            global_min[0] = min(global_min[0], wx)
                            global_min[1] = min(global_min[1], wy)
                            global_min[2] = min(global_min[2], wz)
                            global_max[0] = max(global_max[0], wx)
                            global_max[1] = max(global_max[1], wy)
                            global_max[2] = max(global_max[2], wz)

        for child_idx in node.get('children', []):
            visit_node(child_idx, world_mat, depth + 1)

    identity = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    scenes = gltf.get('scenes', [])
    root_nodes = scenes[gltf.get('scene', 0)].get('nodes', []) if scenes else list(range(len(nodes)))
    for rn in root_nodes:
        visit_node(rn, identity)

    if math.isinf(global_min[0]):
        dims = [0.0, 0.0, 0.0]
    else:
        dims = [
            abs(global_max[0] - global_min[0]),
            abs(global_max[1] - global_min[1]),
            abs(global_max[2] - global_min[2]),
        ]

    # Sort horizontal dims vs vertical (Y is usually up in glTF, but check sorted dims)
    sorted_dims = sorted(dims, reverse=True)
    length, width, height = sorted_dims[0], sorted_dims[1], sorted_dims[2]
    lw_ratio = (length / width) if width > 1e-6 else 0.0
    lh_ratio = (length / height) if height > 1e-6 else 0.0

    # Detect body paint material names
    explicit_body = [
        m for m in materials
        if any(k in m.lower() for k in BODY_HINT_KEYWORDS)
        and not any(nk in m.lower() for nk in NON_BODY_KEYWORDS)
    ]
    detection_method = 'keyword'
    if explicit_body:
        body_materials = explicit_body
    else:
        detection_method = 'largest_surface_heuristic'
        candidates = [
            (m, w) for m, w in mat_weights.items()
            if not any(nk in m.lower() for nk in NON_BODY_KEYWORDS)
        ]
        candidates.sort(key=lambda x: x[1], reverse=True)
        body_materials = [candidates[0][0]] if candidates else (materials[:1] if materials else [])

    return {
        'version': version,
        'asset': gltf.get('asset', {}),
        'poly_count': poly_count,
        'materials': materials,
        'material_count': len(materials),
        'texture_count': len(textures),
        'meshes': meshes_summary,
        'bbox_dims': {'length': round(length, 4), 'width': round(width, 4), 'height': round(height, 4)},
        'lw_ratio': round(lw_ratio, 3),
        'lh_ratio': round(lh_ratio, 3),
        'body_material_names': body_materials,
        'body_detection_method': detection_method,
    }


def validate_car_glb(glb_path: str | Path, min_Input_polys: int = 15000) -> tuple[bool, str, dict[str, Any]]:
    try:
        info = inspect_glb(glb_path)
    except Exception as exc:
        return False, f'corrupt_glb: {exc}', {}

    if info['material_count'] < 3:
        return False, f"too_few_materials ({info['material_count']} < 3)", info

    lw = info['lw_ratio']
    lh = info['lh_ratio']
    if not (1.55 <= lw <= 3.15 and 2.0 <= lh <= 4.6):
        return False, f'invalid_bbox_proportion (L/W={lw}, L/H={lh})', info

    if info['poly_count'] > 0 and info['poly_count'] < min_Input_polys:
        return False, f"low_poly_geometry ({info['poly_count']} tris)", info

    return True, 'ok', info


def main() -> int:
    parser = argparse.ArgumentParser(description='Inspect meshes, materials, and proportions of a .glb file.')
    parser.add_argument('glb_file', help='Path to .glb file')
    args = parser.parse_args()

    ok, reason, info = validate_car_glb(args.glb_file, min_Input_polys=1000)
    print(f"GLB v{info.get('version')} — {args.glb_file}")
    print(f"Validation: {'PASS' if ok else 'FAIL'} ({reason})")
    print(f"Asset metadata: {info.get('asset')}")
    print(f"Triangles (uncompressed/indexed): {info.get('poly_count'):,}")
    print(f"Bounding Box (L x W x H): {info.get('bbox_dims')} | L/W={info.get('lw_ratio')} | L/H={info.get('lh_ratio')}")
    print(f"Materials ({info.get('material_count')}), Textures ({info.get('texture_count')})")
    print(f"Detected body_material_names ({info.get('body_detection_method')}): {info.get('body_material_names')}")
    print('\nAll Materials:')
    for idx, name in enumerate(info.get('materials', [])):
        print(f'  [{idx}] {name}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
