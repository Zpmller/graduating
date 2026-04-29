"""
对数据集中 no-helmet（全局类别 ID 6）过采样：对「至少含一个 no-helmet 框」的样本
整图复制一份（图片 + 标签内容不变），使该类检测框总数约翻倍。

处理目录默认：data/final、data/final_add（可多次传入 --root）。
新生成文件 stem 为：{合并前缀}__nh_{8位hex}（前缀为原 stem 中第一个 __ 前段，如 face、helmet_industry），
短且保留命名风格；已为过采样副本的（含 __nhosdup / __nh_ / nh+hex）会跳过，避免重复翻倍。

用法:
  python scripts/oversample_no_helmet.py --dry-run
  python scripts/oversample_no_helmet.py
"""
from __future__ import annotations

import argparse
import ast
import re
import secrets
import shutil
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def is_oversample_copy_stem(stem: str) -> bool:
    """已是过采样副本则不再复制。"""
    if "__nhosdup" in stem or "__nh_" in stem:
        return True
    return len(stem) == 10 and stem.startswith("nh") and all(c in "0123456789abcdef" for c in stem[2:])


def merge_prefix(stem: str) -> str:
    if "__" in stem:
        return stem.split("__", 1)[0]
    return stem


def load_no_helmet_id(data_yaml: Path) -> int:
    text = data_yaml.read_text(encoding="utf-8")
    m = re.search(r"^\s*names:\s*(\[.*\])\s*$", text, re.MULTILINE)
    if not m:
        raise ValueError(f"无 names: {data_yaml}")
    names = ast.literal_eval(m.group(1))
    if "no-helmet" not in names:
        raise ValueError("names 中无 no-helmet")
    return names.index("no-helmet")


def stem_to_image(img_dir: Path, stem: str) -> Path | None:
    for ext in IMG_EXT:
        p = img_dir / f"{stem}{ext}"
        if p.is_file():
            return p
    for f in img_dir.iterdir():
        if f.is_file() and f.stem == stem and f.suffix.lower() in IMG_EXT:
            return f
    return None


def count_class_in_label(lbl: Path, cid: int) -> int:
    n = 0
    for line in lbl.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        try:
            if int(parts[0]) == cid:
                n += 1
        except ValueError:
            continue
    return n


def count_all_nh(root: Path, splits: tuple[str, ...], nh_id: int) -> int:
    t = 0
    for sp in splits:
        ld = root / sp / "labels"
        if not ld.is_dir():
            continue
        for fp in ld.glob("*.txt"):
            t += count_class_in_label(fp, nh_id)
    return t


def oversample_root(root: Path, nh_id: int, dry: bool) -> tuple[int, int, int]:
    """
    返回 (含 nh 的源文件数, 新建副本对数, 新增 nh 框数)
    """
    n_sources = 0
    n_copies = 0
    nh_added = 0
    for sp in ("train", "valid", "test"):
        img_dir = root / sp / "images"
        lbl_dir = root / sp / "labels"
        if not lbl_dir.is_dir() or not img_dir.is_dir():
            continue
        for lbl in sorted(lbl_dir.glob("*.txt")):
            stem = lbl.stem
            if is_oversample_copy_stem(stem):
                continue
            nh_lines = count_class_in_label(lbl, nh_id)
            if nh_lines == 0:
                continue
            n_sources += 1
            img = stem_to_image(img_dir, stem)
            if img is None:
                continue
            suf = secrets.token_hex(4)
            new_stem = f"{merge_prefix(stem)}__nh_{suf}"
            dst_img = img_dir / f"{new_stem}{img.suffix.lower()}"
            dst_lbl = lbl_dir / f"{new_stem}.txt"
            if dst_img.exists() or dst_lbl.exists():
                continue
            n_copies += 1
            nh_added += nh_lines
            if not dry:
                shutil.copy2(img, dst_img)
                shutil.copy2(lbl, dst_lbl)
    return n_sources, n_copies, nh_added


def main() -> None:
    p = argparse.ArgumentParser(description="no-helmet 过采样（整图复制一份）")
    p.add_argument(
        "--root",
        action="append",
        dest="roots",
        metavar="DIR",
        help="数据集根目录（相对 data/），可多次指定。默认 final 与 final_add",
    )
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    repo = Path(__file__).resolve().parent.parent
    data_dir = repo / "data"
    roots = args.roots or ["final", "final_add"]

    ref_yaml = data_dir / "data.yaml"
    nh_id = load_no_helmet_id(ref_yaml)

    for rel in roots:
        root = data_dir / rel
        if not root.is_dir():
            print(f"[跳过] 不存在: {root}")
            continue
        yaml_local = root / "data.yaml"
        if yaml_local.is_file():
            nh_id = load_no_helmet_id(yaml_local)
        before = count_all_nh(root, ("train", "valid", "test"), nh_id)
        n_src, n_cp, nh_add = oversample_root(root, nh_id, args.dry_run)
        after = before + nh_add if not args.dry_run else before + nh_add

        print(f"=== {rel} ===")
        print(f"  no-helmet 框数: 前 {before}  →  后约 {after} (+{nh_add})")
        print(f"  含 no-helmet 的源样本: {n_src}  新建副本: {n_cp}")
        print()


if __name__ == "__main__":
    main()
