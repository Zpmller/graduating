"""
清洗 Spark 数据集（Spark.v2i.yolov11）YOLO 标签：

- valid 中曾出现 id 1/2/3 混用，与单类 sparks 不一致；统一为全局 sparks = 3
- train/test 一般为 id 3，一并规范化
- 坐标裁剪到合法 YOLO 归一化范围

用法:
  cd ai_edge_system
  python scripts/clean_spark_labels.py
  python scripts/clean_spark_labels.py --dry-run
"""
from __future__ import annotations

import argparse
from pathlib import Path

# 任意出现的类别号 -> 全局 sparks（与 data/data.yaml 索引 3 一致）
DEFAULT_MAP = {0: 3, 1: 3, 2: 3, 3: 3}

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

    x = min(max(x, 0.0), 1.0)
    y = min(max(y, 0.0), 1.0)
    w = min(max(w, EPS), 1.0)
    h = min(max(h, EPS), 1.0)
    half_w, half_h = w / 2.0, h / 2.0
    x = min(max(x, half_w), 1.0 - half_w)
    y = min(max(y, half_h), 1.0 - half_h)

    new_c = class_map[cid]
    return f"{new_c} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n"


def process_file(path: Path, class_map: dict[int, int], dry: bool) -> tuple[int, int]:
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
    if not dry:
        path.write_text(new_body, encoding="utf-8")
    return len(kept), removed


def main() -> None:
    parser = argparse.ArgumentParser(description="清洗 Spark.v2i 标签")
    parser.add_argument(
        "--dataset-root",
        type=str,
        default=None,
        help="Spark 数据集根目录，默认 data/fire/Spark.v2i.yolov11",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent / "data" / "fire" / "Spark.v2i.yolov11"
    root = Path(args.dataset_root) if args.dataset_root else base

    print(f"目录: {root}")
    print(f"类别映射 -> 全局 sparks(3): {DEFAULT_MAP}")
    print(f"dry_run={args.dry_run}\n")

    total_kept = total_removed = 0
    for sp in ("train", "valid", "test"):
        lbl_dir = root / sp / "labels"
        if not lbl_dir.is_dir():
            print(f"[跳过] 无 {lbl_dir}")
            continue
        n_files = 0
        for fp in sorted(lbl_dir.glob("*.txt")):
            k, r = process_file(fp, DEFAULT_MAP, args.dry_run)
            total_kept += k
            total_removed += r
            n_files += 1
        print(f"{sp}/labels: {n_files} 个 txt")

    print(f"\n合计 保留框 {total_kept}, 丢弃行 {total_removed}")
    if args.dry_run:
        print("(dry-run: 未写回)")


if __name__ == "__main__":
    main()
