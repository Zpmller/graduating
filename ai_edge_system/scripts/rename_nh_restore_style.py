"""
将 final / final_add 里过采样样本（当前为 nh + hex 短名）改为保留合并前缀的短名：

  {原前缀}__nh_{8位hex}.jpg

前缀取自同源非 nh 样本的 stem：在 train/valid/test 内用「标签全文」匹配到原始样本，
取 stem 中第一个 __ 前的部分（如 face、fire、cylinder、helmet_industry）。

用法:
  python scripts/rename_nh_restore_style.py --dry-run
  python scripts/rename_nh_restore_style.py
"""
from __future__ import annotations

import argparse
import hashlib
import secrets
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def stem_to_image(img_dir: Path, stem: str) -> Path | None:
    for ext in IMG_EXT:
        p = img_dir / f"{stem}{ext}"
        if p.is_file():
            return p
    for f in img_dir.iterdir():
        if f.is_file() and f.stem == stem and f.suffix.lower() in IMG_EXT:
            return f
    return None


def label_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def is_nh_short_stem(stem: str) -> bool:
    return len(stem) == 10 and stem.startswith("nh") and stem[2:].isalnum()


def prefix_from_merge_stem(stem: str) -> str:
    if "__" in stem:
        return stem.split("__", 1)[0]
    return stem


def process_split(root: Path, split: str, dry: bool) -> tuple[int, int, int]:
    """返回 (成功重命名对, 无匹配跳过, 冲突跳过)。"""
    img_dir = root / split / "images"
    lbl_dir = root / split / "labels"
    if not lbl_dir.is_dir() or not img_dir.is_dir():
        return 0, 0, 0

    # 非 nh 短名：建立 内容哈希 -> stem
    content_hash_to_stem: dict[str, str] = {}
    for lf in lbl_dir.glob("*.txt"):
        if is_nh_short_stem(lf.stem):
            continue
        body = label_text(lf)
        h = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if h not in content_hash_to_stem:
            content_hash_to_stem[h] = lf.stem

    nh_files = sorted(lf for lf in lbl_dir.glob("*.txt") if is_nh_short_stem(lf.stem))
    used_stems = {f.stem for f in img_dir.iterdir() if f.is_file()} | {f.stem for f in lbl_dir.glob("*.txt")}

    ok = skip_nomatch = skip_conflict = 0
    for lf in nh_files:
        body = label_text(lf)
        h = hashlib.sha256(body.encode("utf-8")).hexdigest()
        orig = content_hash_to_stem.get(h)
        if not orig:
            skip_nomatch += 1
            continue
        prefix = prefix_from_merge_stem(orig)
        img = stem_to_image(img_dir, lf.stem)
        if img is None:
            skip_nomatch += 1
            continue
        while True:
            suf = secrets.token_hex(4)
            new_stem = f"{prefix}__nh_{suf}"
            if new_stem not in used_stems:
                used_stems.add(new_stem)
                break
        new_img = img_dir / f"{new_stem}{img.suffix.lower()}"
        new_lbl = lbl_dir / f"{new_stem}.txt"
        if new_img.exists() or new_lbl.exists():
            skip_conflict += 1
            continue
        if not dry:
            img.rename(new_img)
            lf.rename(new_lbl)
        ok += 1

    return ok, skip_nomatch, skip_conflict


def main() -> None:
    p = argparse.ArgumentParser(description="nh 短名改为 前缀__nh_hex 风格")
    p.add_argument("--root", action="append", dest="roots", metavar="DIR", help="data 下目录，默认 final final_add")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    repo = Path(__file__).resolve().parent.parent
    data_dir = repo / "data"
    roots = args.roots or ["final", "final_add"]

    for rel in roots:
        root = data_dir / rel
        if not root.is_dir():
            print(f"[跳过] {root}")
            continue
        print(f"=== {rel} ===")
        tot_ok = tot_n = tot_c = 0
        for sp in ("train", "valid", "test"):
            a, b, c = process_split(root, sp, args.dry_run)
            tot_ok += a
            tot_n += b
            tot_c += c
            print(f"  {sp}: 重命名 {a}, 无匹配 {b}, 冲突 {c}")
        print(f"  合计: 重命名 {tot_ok}\n")

    if args.dry_run:
        print("(dry-run)")


if __name__ == "__main__":
    main()
