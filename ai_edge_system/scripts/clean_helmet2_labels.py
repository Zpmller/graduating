"""
将 industry_safety（Roboflow nc=4）标签 ID 改为项目 data/data.yaml 的全局类别编号。

默认根目录: data/helmet/industry_safety.v2i.yolov11
原 ID → 全局 ID（与 data/data.yaml 中 names 下标一致）：
  0 Helmet   -> helmet
  1 NOHelmet -> no-helmet
  2 NOVest、3 Vest → 无对应全局类：不写框；若该图仅剩此类则写空标签文件
已含磁盘上的 5/7 时：5→helmet，7→no-helmet

完成后写回数据集内 data.yaml：nc / names 与项目根目录 data/data.yaml 一致。

用法:
  python scripts/clean_helmet2_labels.py
  python scripts/clean_helmet2_labels.py --dataset-root data/helmet/helmet2/industry_safety.v2i.yolov11
  python scripts/clean_helmet2_labels.py --dry-run
"""
from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path

# Roboflow 原始 0–3，或已对齐全局的 5/6，或旧盘上的 7→no-helmet
RAW_TO_GLOBAL_NAME_KEYS = (
    (0, "helmet"),
    (1, "no-helmet"),
    (5, "helmet"),
    (6, "no-helmet"),
    (7, "no-helmet"),
)

EPS = 1e-6


def load_project_yaml(data_yaml: Path) -> tuple[int, list[str]]:
    """读取项目 data/data.yaml 的 nc 与 names（与训练配置一致）。"""
    text = data_yaml.read_text(encoding="utf-8")
    nc_m = re.search(r"^\s*nc:\s*(\d+)\s*$", text, re.MULTILINE)
    if not nc_m:
        raise ValueError(f"未解析到 nc: {data_yaml}")
    nm_m = re.search(r"^\s*names:\s*(\[.*\])\s*$", text, re.MULTILINE)
    if not nm_m:
        raise ValueError(f"未解析到 names: {data_yaml}")
    nc = int(nc_m.group(1))
    names = ast.literal_eval(nm_m.group(1))
    return nc, names


def build_raw_to_global_id(names: list[str]) -> dict[int, int]:
    idx = {n: i for i, n in enumerate(names)}
    m: dict[int, int] = {}
    for raw, key in RAW_TO_GLOBAL_NAME_KEYS:
        if key not in idx:
            raise KeyError(f"项目 names 中缺少 {key!r}")
        m[raw] = idx[key]
    return m


def render_dataset_yaml(project_yaml: Path) -> str:
    nc, names = load_project_yaml(project_yaml)
    return f"""# 与上级目录 data/data.yaml 的 nc、names 一致（本集标签中通常仅含 helmet、no-helmet 两类 ID）
train: ../train/images
val: ../valid/images
test: ../test/images

nc: {nc}
names: {names}
"""


def clean_line(parts: list[str], class_map: dict[int, int]) -> str | None:
    if len(parts) != 5:
        return None
    try:
        cid = int(parts[0])
    except ValueError:
        return None
    if cid not in class_map:
        return None
    try:
        x, y, w, h = map(float, parts[1:5])
    except ValueError:
        return None

    x = min(max(x, 0.0), 1.0)
    y = min(max(y, 0.0), 1.0)
    w = min(max(w, EPS), 1.0)
    h = min(max(h, EPS), 1.0)
    half_w, half_h = w / 2.0, h / 2.0
    x = min(max(x, half_w), 1.0 - half_w)
    y = min(max(y, half_h), 1.0 - half_h)

    new_c = class_map[cid]
    return f"{new_c} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n"


def process_file(path: Path, class_map: dict[int, int], dry: bool) -> tuple[int, int, bool]:
    """返回 (保留行数, 丢弃行数, 是否变为空文件)。"""
    text = path.read_text(encoding="utf-8", errors="ignore")
    kept: list[str] = []
    removed = 0
    for line in text.splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        out = clean_line(parts, class_map)
        if out is None:
            removed += 1
            continue
        kept.append(out)

    new_body = "".join(kept)
    became_empty = len(kept) == 0 and removed > 0
    if not dry:
        path.write_text(new_body, encoding="utf-8")
    return len(kept), removed, became_empty


def main() -> None:
    parser = argparse.ArgumentParser(description="清洗 helmet2 / industry_safety 标签")
    parser.add_argument(
        "--dataset-root",
        type=str,
        default=None,
        help="数据集根目录（含 train/valid/test/labels），默认 data/helmet/industry_safety.v2i.yolov11",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--no-yaml",
        action="store_true",
        help="不写回 data.yaml（仅改 labels）",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    project_yaml = repo_root / "data" / "data.yaml"
    base = repo_root / "data" / "helmet" / "industry_safety.v2i.yolov11"
    root = Path(args.dataset_root) if args.dataset_root else base

    nc, names = load_project_yaml(project_yaml)
    class_map = build_raw_to_global_id(names)

    print(f"项目配置: {project_yaml}")
    print(f"  nc={nc}, names 与训练一致")
    print(f"目录: {root}")
    print(f"原 ID -> 全局 ID: {class_map}（2/3 等无映射类丢弃；该图无保留框则写空 txt）")
    print(f"dry_run={args.dry_run}\n")

    total_kept = total_removed = 0
    n_empty_files = 0
    for sp in ("train", "valid", "test"):
        lbl_dir = root / sp / "labels"
        if not lbl_dir.is_dir():
            print(f"[跳过] 无 {lbl_dir}")
            continue
        n = 0
        for fp in sorted(lbl_dir.glob("*.txt")):
            k, r, empty = process_file(fp, class_map, args.dry_run)
            total_kept += k
            total_removed += r
            if empty:
                n_empty_files += 1
            n += 1
        print(f"{sp}/labels: {n} 个 txt")

    print(f"\n合计 保留框 {total_kept}, 丢弃行 {total_removed}（多为 NOVest/Vest）")
    print(f"变为空标签文件数: {n_empty_files}")
    if args.dry_run:
        print("(dry-run: 未写回)")
        return

    if not args.no_yaml:
        yaml_path = root / "data.yaml"
        yaml_path.write_text(render_dataset_yaml(project_yaml), encoding="utf-8")
        print(f"已更新: {yaml_path}")


if __name__ == "__main__":
    main()
