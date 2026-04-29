#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清洗 Roboflow 导出的 Spark YOLO 数据集（Spark.v2i.yolov11）：
  - 删除无法解码的图片及对应标签
  - 删除无对应图片的孤立 .txt
  - 删除无对应标签的图片（避免 Ultralytics 扫描告警）
  - 校验 YOLO 行：5 列、类别合法、xywh 在合理范围内；非法行丢弃
  - 将单类 sparks 的类别 ID 0 映射为项目 8 类中的全局 ID 3（与 data/data.yaml 一致）

用法（在 ai_edge_system 目录下）:
  python scripts/clean_spark_dataset.py --dry-run
  python scripts/clean_spark_dataset.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

# 相对 ai_edge_system
DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "data" / "fire" / "Spark.v2i.yolov11"
SPLITS = ("train", "valid", "test")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
# 合并到 data.yaml 后 sparks 在 names 中的索引
GLOBAL_SPARKS_CLASS_ID = 3
LOCAL_SPARK_CLASS_ID = 0


def _try_read_image(path: Path) -> bool:
    try:
        import cv2

        img = cv2.imread(str(path))
        return img is not None and img.size > 0
    except Exception:
        pass
    try:
        from PIL import Image

        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:
        return False


def _parse_valid_lines(text: str) -> list[str]:
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 5:
            continue
        try:
            cls = int(parts[0])
            x, y, w, h = map(float, parts[1:5])
        except ValueError:
            continue
        if cls not in (LOCAL_SPARK_CLASS_ID, GLOBAL_SPARKS_CLASS_ID):
            continue
        if w <= 0 or h <= 0:
            continue
        if not (-0.05 <= x <= 1.05 and -0.05 <= y <= 1.05):
            continue
        if w > 1.5 or h > 1.5:
            continue
        x = min(1.0, max(0.0, x))
        y = min(1.0, max(0.0, y))
        w = min(1.0, max(0.001, w))
        h = min(1.0, max(0.001, h))
        out.append(f"{GLOBAL_SPARKS_CLASS_ID} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")
    return out


def clean_split(split_dir: Path, *, dry_run: bool) -> dict[str, int]:
    img_dir = split_dir / "images"
    lbl_dir = split_dir / "labels"
    stats = {
        "removed_corrupt_images": 0,
        "removed_images_no_label": 0,
        "removed_orphan_labels": 0,
        "rewritten_labels": 0,
        "images_ok": 0,
    }
    if not img_dir.is_dir() or not lbl_dir.is_dir():
        return stats

    images = [p for p in img_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES]

    for img_path in images:
        stem = img_path.stem
        lbl_path = lbl_dir / f"{stem}.txt"

        if not _try_read_image(img_path):
            if not dry_run:
                img_path.unlink(missing_ok=True)
                lbl_path.unlink(missing_ok=True)
            stats["removed_corrupt_images"] += 1
            continue

        if not lbl_path.is_file():
            if not dry_run:
                img_path.unlink(missing_ok=True)
            stats["removed_images_no_label"] += 1
            continue

        text = lbl_path.read_text(encoding="utf-8", errors="replace")
        new_lines = _parse_valid_lines(text)
        stats["images_ok"] += 1
        new_body = "".join(new_lines)
        if new_body != text:
            stats["rewritten_labels"] += 1
            if not dry_run:
                if new_lines:
                    lbl_path.write_text(new_body, encoding="utf-8")
                else:
                    lbl_path.write_text("", encoding="utf-8")

    for lbl_path in lbl_dir.glob("*.txt"):
        stem = lbl_path.stem
        if any((img_dir / f"{stem}{sfx}").is_file() for sfx in IMAGE_SUFFIXES):
            continue
        if not dry_run:
            lbl_path.unlink(missing_ok=True)
        stats["removed_orphan_labels"] += 1

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="清洗 Spark.v2i.yolov11 并映射类别到全局 sparks=3")
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=DEFAULT_ROOT,
        help="数据集根目录（含 train/valid/test）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写盘、不删文件")
    args = parser.parse_args()
    root = args.dataset_root.resolve()
    if not root.is_dir():
        raise SystemExit(f"目录不存在: {root}")

    print(f"数据集根: {root}")
    print(f"类别映射: 本地 {LOCAL_SPARK_CLASS_ID} / 已映射 {GLOBAL_SPARKS_CLASS_ID} -> 全局 {GLOBAL_SPARKS_CLASS_ID} (sparks)")
    print(f"模式: {'DRY-RUN' if args.dry_run else '应用更改'}")
    print()

    total: dict[str, int] = {}
    for sp in SPLITS:
        d = root / sp
        if not d.is_dir():
            print(f"[跳过] 无目录: {d}")
            continue
        s = clean_split(d, dry_run=args.dry_run)
        for k, v in s.items():
            total[k] = total.get(k, 0) + v
        print(f"{sp}: {s}")

    print()
    print("合计:", total)


if __name__ == "__main__":
    main()
