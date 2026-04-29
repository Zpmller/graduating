"""
将 Spark 与 helmet1、helmet2 合并到单一 YOLO 目录（与 data/data.yaml 的 7 类命名一致）。

输出: data/spark_helmet12_merged/{train,valid,test}/{images,labels}
      data/spark_helmet12_merged/data.yaml

用法（在 ai_edge_system 目录下）:
  python scripts/merge_spark_helmet12.py
  python scripts/merge_spark_helmet12.py --dry-run
  python scripts/merge_spark_helmet12.py --clean
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

GLOBAL_NAMES = ["face", "fire", "smoke", "sparks", "gas_cylinder", "helmet", "no-helmet"]

SOURCES: list[dict] = [
    {
        "id": "spark",
        "root": "fire/Spark.v2i.yolov11",
        "mapping": {0: 3, 1: 3, 2: 3, 3: 3},
    },
    {
        "id": "helmet1",
        "root": "helmet/helmet1",
        "mapping": {5: 5, 6: 6, 7: 6},
    },
    {
        "id": "helmet2",
        "root": "helmet/helmet2",
        "mapping": {0: 5, 1: 6, 5: 5, 6: 6, 7: 6},
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
    sources: list[dict],
    dry_run: bool,
) -> tuple[int, int]:
    img_n = 0
    lbl_n = 0
    images_out = out_dir / split / "images"
    labels_out = out_dir / split / "labels"
    if not dry_run:
        images_out.mkdir(parents=True, exist_ok=True)
        labels_out.mkdir(parents=True, exist_ok=True)

    for src in sources:
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
    content = f"""# Spark + helmet1 + helmet2 合并数据集
# 由 scripts/merge_spark_helmet12.py 生成

path: .
train: train/images
val: valid/images
test: test/images

nc: {len(GLOBAL_NAMES)}
names: {GLOBAL_NAMES}
"""
    (out_dir / "data.yaml").write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="合并 Spark、helmet1、helmet2 为单一 YOLO 目录")
    parser.add_argument("--dry-run", action="store_true", help="仅统计，不写入文件")
    parser.add_argument(
        "--out",
        type=str,
        default="spark_helmet12_merged",
        help="输出子目录名（位于 data/ 下），默认 spark_helmet12_merged",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="若输出目录已存在则先删除再写入（避免重复执行产生重复样本）",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    ai_edge = script_dir.parent
    data_dir = ai_edge / "data"
    out_dir = data_dir / args.out

    print(f"数据根目录: {data_dir}")
    print(f"输出目录: {out_dir}")
    print(f"dry_run={args.dry_run}")
    print()

    if not args.dry_run and args.clean and out_dir.is_dir():
        shutil.rmtree(out_dir)
        print(f"已删除旧输出目录: {out_dir}\n")

    total_img = 0
    total_lbl = 0
    for sp in SPLITS:
        print(f"=== {sp} ===")
        ni, nl = merge_one_split(data_dir, out_dir, sp, SOURCES, args.dry_run)
        print(f"  图片: {ni}, 标签文件: {nl}")
        total_img += ni
        total_lbl += nl

    print()
    print(f"合计图片: {total_img}, 标签文件: {total_lbl}")

    if not args.dry_run:
        write_data_yaml(out_dir)
        print(f"已写入: {out_dir / 'data.yaml'}")
        print()
        print("训练示例:")
        print(f"  yolo train data={out_dir / 'data.yaml'} ...")
    else:
        print("(dry-run: 未创建文件)")


if __name__ == "__main__":
    main()
