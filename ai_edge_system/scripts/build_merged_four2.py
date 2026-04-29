"""
从 data/merged_four1 的 valid、test 中按「每个类别」各随机抽取一定比例样本，
将对应图片与标签原样复制到 data/merged_four2/train（不改名、不改内容）。

不修改 merged_four2 中已有的 train（仅追加复制）、valid、test，也不改写 data.yaml。

用法（在 ai_edge_system 目录下）:
  python scripts/build_merged_four2.py
  python scripts/build_merged_four2.py --ratio 0.1 --seed 42
  python scripts/build_merged_four2.py --zip   # 可选：打包整个 merged_four2
"""
from __future__ import annotations

import argparse
import math
import random
import shutil
import zipfile
from collections import defaultdict
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
NC = 7


def stem_to_image(src_images: Path, stem: str) -> Path | None:
    for ext in IMG_EXT:
        p = src_images / f"{stem}{ext}"
        if p.is_file():
            return p
    for f in src_images.iterdir():
        if f.is_file() and f.stem == stem and f.suffix.lower() in IMG_EXT:
            return f
    return None


def label_classes(lbl_path: Path) -> set[int]:
    out: set[int] = set()
    if not lbl_path.is_file():
        return out
    for line in lbl_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        try:
            out.add(int(parts[0]))
        except ValueError:
            continue
    return out


def stems_per_class(lbl_dir: Path) -> dict[int, list[str]]:
    by_c: dict[int, list[str]] = defaultdict(list)
    if not lbl_dir.is_dir():
        return by_c
    for lf in lbl_dir.glob("*.txt"):
        stem = lf.stem
        for c in label_classes(lf):
            if 0 <= c < NC:
                by_c[c].append(stem)
    for c in by_c:
        by_c[c] = sorted(set(by_c[c]))
    return by_c


def sample_stems_union(by_c: dict[int, list[str]], ratio: float, rng: random.Random) -> set[str]:
    chosen: set[str] = set()
    for c in range(NC):
        stems = by_c.get(c, [])
        if not stems:
            continue
        k = min(len(stems), max(1, math.ceil(len(stems) * ratio)))
        picked = rng.sample(stems, k)
        chosen.update(picked)
    return chosen


def copy_split_subset(
    src_root: Path,
    split: str,
    stems: set[str],
    dst_images: Path,
    dst_labels: Path,
) -> int:
    """按原文件名复制图片与 .txt，不修改内容。"""
    src_img = src_root / split / "images"
    src_lbl = src_root / split / "labels"
    n = 0
    for stem in sorted(stems):
        lbl = src_lbl / f"{stem}.txt"
        if not lbl.is_file():
            continue
        img = stem_to_image(src_img, stem)
        if img is None:
            continue
        shutil.copy2(img, dst_images / img.name)
        shutil.copy2(lbl, dst_labels / lbl.name)
        n += 1
    return n


def zip_folder(data_dir: Path, folder_name: str) -> Path:
    src = data_dir / folder_name
    primary = data_dir / f"{folder_name}.zip"
    alt = data_dir / f"{folder_name}_packed.zip"
    target = primary
    try:
        if primary.is_file():
            primary.unlink()
    except OSError:
        target = alt
        if alt.is_file():
            try:
                alt.unlink()
            except OSError:
                pass
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in src.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(data_dir).as_posix())
    return target


def main() -> None:
    p = argparse.ArgumentParser(description="从 merged_four1 抽样追加复制到 merged_four2/train")
    p.add_argument("--src", type=str, default="merged_four1", help="源目录名（位于 data/ 下）")
    p.add_argument("--dst", type=str, default="merged_four2", help="目标数据集根目录（位于 data/ 下）")
    p.add_argument("--ratio", type=float, default=0.1, help="每个类别在该划分内抽取比例（ceil，每类至少 1 张若有样本）")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--zip", action="store_true", help="完成后打包 data/merged_four2.zip（可选）")
    args = p.parse_args()

    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / "data"
    src_root = data_dir / args.src
    dst_root = data_dir / args.dst

    if not src_root.is_dir():
        raise SystemExit(f"源目录不存在: {src_root}")

    rng = random.Random(args.seed)
    by_valid = stems_per_class(src_root / "valid" / "labels")
    by_test = stems_per_class(src_root / "test" / "labels")
    u_valid = sample_stems_union(by_valid, args.ratio, rng)
    u_test = sample_stems_union(by_test, args.ratio, rng)

    dst_img = dst_root / "train" / "images"
    dst_lbl = dst_root / "train" / "labels"
    dst_img.mkdir(parents=True, exist_ok=True)
    dst_lbl.mkdir(parents=True, exist_ok=True)

    n_v = copy_split_subset(src_root, "valid", u_valid, dst_img, dst_lbl)
    n_t = copy_split_subset(src_root, "test", u_test, dst_img, dst_lbl)

    print(f"源: {src_root}")
    print(f"追加到: {dst_root / 'train'}")
    print(f"ratio={args.ratio}, seed={args.seed}")
    print(f"自 valid 抽样 stem 数 {len(u_valid)}，复制成功 {n_v} 对（图+标签，原名）")
    print(f"自 test  抽样 stem 数 {len(u_test)}，复制成功 {n_t} 对（图+标签，原名）")
    print(f"合计新增约 {n_v + n_t} 对（若 valid/test 有同名 stem 会覆盖为最后一次复制）")

    if args.zip:
        zpath = zip_folder(data_dir, args.dst)
        print(f"zip: {zpath}")


if __name__ == "__main__":
    main()
