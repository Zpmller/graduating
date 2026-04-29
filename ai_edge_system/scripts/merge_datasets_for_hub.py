"""
将 ai_edge_system/data 下多个 YOLO 子数据集合并为单一目录，便于上传到 Ultralytics HUB 等只支持一个数据集的平台。

输出: data/merged_ultralytics/{train,valid,test}/{images,labels}
      data/merged_ultralytics/data.yaml

用法:
  cd ai_edge_system
  python scripts/merge_datasets_for_hub.py

可选:
  python scripts/merge_datasets_for_hub.py --dry-run   # 只打印统计，不复制
"""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

# 与 data/data.yaml 中 names 顺序一致: 0..6（7 类，无 person）
GLOBAL_NAMES = ["face", "fire", "smoke", "sparks", "gas_cylinder", "helmet", "no-helmet"]

# 各子数据集：根目录相对于 data/；train/valid/test 下为 images 与 labels
# mapping: 该数据集 txt 中的类别 ID -> 全局 ID
SOURCES: list[dict] = [
    {
        "id": "face",
        "root": "face/Face detection with yolov8.v2i.yolov11",
        "mapping": {0: 0},
    },
    {
        "id": "fire_smoke",
        "root": "fire/Fire and smoke detection.v2i.yolov11",
        # Roboflow 导出中 Fire/Smoke 在部分版本里为 1/2（与 data.yaml 中 Fire=0,Smoke=1 的索引不完全一致，以实际 txt 为准）
        "mapping": {1: 1, 2: 2},
    },
    {
        "id": "spark",
        "root": "fire/Spark.v2i.yolov11",
        # 已由 clean_spark_dataset.py / clean_spark_labels.py 统一为全局 sparks=3；兼容未清洗的 0/1/2/3
        "mapping": {0: 3, 1: 3, 2: 3, 3: 3},
    },
    {
        "id": "cylinder",
        "root": "gas_cylinder/CylinDeRS",
        "mapping": {4: 4},
    },
    {
        "id": "helmet",
        "root": "helmet/Construction",
        "mapping": {5: 5, 6: 6, 7: 6},
    },
    {
        "id": "helmet_industry",
        "root": "helmet/industry_safety.v2i.yolov11",
        "mapping": {0: 5, 1: 6, 5: 5, 6: 6, 7: 6},
    },
    {
        "id": "helmet3",
        "root": "helmet/helmet3",
        "mapping": {0: 6, 1: 5, 5: 5, 6: 6, 7: 6},
    },
]

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
SPLITS = ("train", "valid", "test")


def remap_label_lines(text: str, mapping: dict[int, int]) -> str:
    out_lines: list[str] = []
    for line in text.splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        try:
            cid = int(parts[0])
        except ValueError:
            continue
        if cid not in mapping:
            continue
        parts[0] = str(mapping[cid])
        out_lines.append(" ".join(parts) + "\n")
    return "".join(out_lines)


def merge_one_split(
    data_dir: Path,
    out_dir: Path,
    split: str,
    dry_run: bool,
) -> tuple[int, int]:
    """返回 (复制的图片数, 复制的标签文件数)"""
    img_n = 0
    lbl_n = 0
    images_out = out_dir / split / "images"
    labels_out = out_dir / split / "labels"
    if not dry_run:
        images_out.mkdir(parents=True, exist_ok=True)
        labels_out.mkdir(parents=True, exist_ok=True)

    for src in SOURCES:
        src_root = data_dir / src["root"]
        mapping = src["mapping"]
        prefix = src["id"]
        img_dir = src_root / split / "images"
        lbl_dir = src_root / split / "labels"
        if not img_dir.is_dir():
            print(f"  [跳过] 无目录: {img_dir}")
            continue

        for img_path in sorted(img_dir.iterdir()):
            if not img_path.is_file() or img_path.suffix.lower() not in IMG_EXT:
                continue
            stem = img_path.stem
            new_base = f"{prefix}__{stem}"
            new_img_name = new_base + img_path.suffix.lower()
            dst_img = images_out / new_img_name
            lbl_path = lbl_dir / f"{stem}.txt"
            dst_lbl = labels_out / f"{new_base}.txt"

            if dry_run:
                img_n += 1
                if lbl_path.is_file():
                    lbl_n += 1
                continue

            shutil.copy2(img_path, dst_img)
            img_n += 1

            if lbl_path.is_file():
                raw = lbl_path.read_text(encoding="utf-8", errors="ignore")
                remapped = remap_label_lines(raw, mapping)
                dst_lbl.write_text(remapped, encoding="utf-8")
                lbl_n += 1
            else:
                dst_lbl.write_text("", encoding="utf-8")

    return img_n, lbl_n


def write_data_yaml(out_dir: Path) -> None:
    content = f"""# 合并后的单一数据集（供 Ultralytics HUB / 单数据集训练使用）
# 由 scripts/merge_datasets_for_hub.py 生成

path: .
train: train/images
val: valid/images
test: test/images

nc: {len(GLOBAL_NAMES)}
names: {GLOBAL_NAMES}
"""
    (out_dir / "data.yaml").write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="合并多子数据集为单一 YOLO 目录")
    parser.add_argument("--dry-run", action="store_true", help="仅统计，不写入文件")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    ai_edge = script_dir.parent
    data_dir = ai_edge / "data"
    out_dir = data_dir / "merged_ultralytics"

    print(f"数据根目录: {data_dir}")
    print(f"输出目录: {out_dir}")
    print(f"dry_run={args.dry_run}")
    print()

    total_img = 0
    total_lbl = 0
    for sp in SPLITS:
        print(f"=== {sp} ===")
        ni, nl = merge_one_split(data_dir, out_dir, sp, args.dry_run)
        print(f"  图片: {ni}, 标签文件: {nl}")
        total_img += ni
        total_lbl += nl

    print()
    print(f"合计图片: {total_img}, 标签文件: {total_lbl}")

    if not args.dry_run:
        write_data_yaml(out_dir)
        print(f"已写入: {out_dir / 'data.yaml'}")
        print()
        print("上传到 HUB 或本地训练时可使用:")
        print(f"  data={out_dir / 'data.yaml'}")
    else:
        print("(dry-run: 未创建文件)")


if __name__ == "__main__":
    main()
