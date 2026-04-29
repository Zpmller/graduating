"""
清洗 helmet3 数据集 YOLO 标签：裁剪坐标到 [0,1]、去掉无效框、映射到项目统一类别 ID。

数据来源 Roboflow: names: ['head', 'helmet', 'person'] 对应原 id 0,1,2

默认映射到全局 7 类 (data/data.yaml，无 person；no-helmet 为类 6):
  head   -> 6 (no-helmet)
  helmet -> 5 (helmet)
  person -> 丢弃
  已清洗的 5/6/7（旧 8 类）-> 5 / 丢弃 person / 6(no-helmet)

用法:
  python scripts/clean_helmet3_labels.py
  python scripts/clean_helmet3_labels.py --dry-run
"""
from __future__ import annotations

import argparse
from pathlib import Path

# 原 ID -> 全局 ID（7 类）；2(person)、6(旧 person) 不在表中即丢弃
DEFAULT_MAP = {0: 6, 1: 5, 5: 5, 7: 6}

EPS = 1e-6


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

    # 中心 + 宽高 -> 裁剪到合法 YOLO 归一化范围
    x = min(max(x, 0.0), 1.0)
    y = min(max(y, 0.0), 1.0)
    w = min(max(w, EPS), 1.0)
    h = min(max(h, EPS), 1.0)
    # 保证框在图像内
    half_w, half_h = w / 2.0, h / 2.0
    x = min(max(x, half_w), 1.0 - half_w)
    y = min(max(y, half_h), 1.0 - half_h)

    new_c = class_map[cid]
    return f"{new_c} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n"


def process_file(path: Path, class_map: dict[int, int], dry: bool) -> tuple[int, int, int]:
    """返回 (保留行数, 删除行数, 重映射行数)"""
    text = path.read_text(encoding="utf-8", errors="ignore")
    kept: list[str] = []
    removed = 0
    remapped = 0
    for line in text.splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        old = None
        try:
            old = int(parts[0])
        except ValueError:
            removed += 1
            continue
        if old in class_map and old != class_map[old]:
            remapped += 1
        out = clean_line(parts, class_map)
        if out is None:
            removed += 1
            continue
        kept.append(out)

    new_body = "".join(kept)
    if not dry:
        path.write_text(new_body, encoding="utf-8")
    return len(kept), removed, remapped


def main() -> None:
    parser = argparse.ArgumentParser(description="清洗 helmet3 标签")
    parser.add_argument(
        "--dataset-root",
        type=str,
        default=None,
        help="helmet3 根目录，默认 data/helmet/helmet3",
    )
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写回")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent / "data" / "helmet" / "helmet3"
    root = Path(args.dataset_root) if args.dataset_root else base
    splits = ["train", "valid", "test"]

    print(f"目录: {root}")
    print(f"类别映射 (原->全局): {DEFAULT_MAP}")
    print(f"dry_run={args.dry_run}\n")

    total_kept = total_removed = total_remapped = 0
    for sp in splits:
        lbl_dir = root / sp / "labels"
        if not lbl_dir.is_dir():
            print(f"[跳过] 无 {lbl_dir}")
            continue
        for fp in sorted(lbl_dir.glob("*.txt")):
            k, r, m = process_file(fp, DEFAULT_MAP, args.dry_run)
            total_kept += k
            total_removed += r
            total_remapped += m
        print(f"{sp}/labels: 已处理 {len(list(lbl_dir.glob('*.txt')))} 个 txt")

    print(f"\n合计 保留框 {total_kept}, 丢弃行 {total_removed}, 发生 ID 变更的框 {total_remapped}")
    if args.dry_run:
        print("(dry-run: 未写回文件)")


if __name__ == "__main__":
    main()
