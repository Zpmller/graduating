"""
将 final / final_add 中带 __nhosdup 的长文件名改为短名（nh + 8 位 hex），
图片与同名 .txt 同步重命名，避免压缩/解压路径过长丢文件。

默认处理: data/final、data/final_add 下 train/valid/test。

用法:
  python scripts/shorten_nhosdup_names.py --dry-run
  python scripts/shorten_nhosdup_names.py
"""
from __future__ import annotations

import argparse
import secrets
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
MARKER = "__nhosdup"


def stem_to_image(img_dir: Path, stem: str) -> Path | None:
    for ext in IMG_EXT:
        p = img_dir / f"{stem}{ext}"
        if p.is_file():
            return p
    for f in img_dir.iterdir():
        if f.is_file() and f.stem == stem and f.suffix.lower() in IMG_EXT:
            return f
    return None


def unique_stem(used: set[str]) -> str:
    while True:
        s = "nh" + secrets.token_hex(4)
        if s not in used:
            used.add(s)
            return s


def process_split(root: Path, split: str, dry: bool) -> tuple[int, int]:
    """返回 (重命名对数, 跳过数)。"""
    img_dir = root / split / "images"
    lbl_dir = root / split / "labels"
    if not lbl_dir.is_dir() or not img_dir.is_dir():
        return 0, 0
    targets = sorted(lf for lf in lbl_dir.glob("*.txt") if MARKER in lf.stem)
    used: set[str] = {f.stem for f in img_dir.iterdir() if f.is_file()}
    used |= {f.stem for f in lbl_dir.glob("*.txt")}
    n_done = 0
    n_skip = 0
    for lbl in targets:
        stem = lbl.stem
        img = stem_to_image(img_dir, stem)
        if img is None:
            n_skip += 1
            continue
        new_stem = unique_stem(used)
        new_img = img_dir / f"{new_stem}{img.suffix.lower()}"
        new_lbl = lbl_dir / f"{new_stem}.txt"
        if new_img.exists() or new_lbl.exists():
            n_skip += 1
            continue
        if not dry:
            img.rename(new_img)
            lbl.rename(new_lbl)
        n_done += 1
    return n_done, n_skip


def main() -> None:
    p = argparse.ArgumentParser(description="缩短 __nhosdup 样本文件名")
    p.add_argument(
        "--root",
        action="append",
        dest="roots",
        metavar="DIR",
        help="data 下目录名，可多次。默认 final、final_add",
    )
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    repo = Path(__file__).resolve().parent.parent
    data_dir = repo / "data"
    roots = args.roots or ["final", "final_add"]

    for rel in roots:
        root = data_dir / rel
        if not root.is_dir():
            print(f"[跳过] 不存在: {root}")
            continue
        print(f"=== {rel} ===")
        total_done = total_skip = 0
        for sp in ("train", "valid", "test"):
            d, s = process_split(root, sp, args.dry_run)
            total_done += d
            total_skip += s
            print(f"  {sp}: 重命名 {d} 对, 跳过 {s}")
        print(f"  小计: {total_done} 对\n")

    if args.dry_run:
        print("(dry-run: 未改文件名)")


if __name__ == "__main__":
    main()
