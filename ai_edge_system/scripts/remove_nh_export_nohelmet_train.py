"""
1) 从 data/final、data/final_add 的 train/valid/test 删除 nh 过采样相关样本（与 oversample_no_helmet 判定一致）。
2) 将两数据集「训练集」中标签含 no-helmet（names 中索引）的样本复制到 data/no_helmet_train_export/<root>/，
   保留原 stem，附加 _ + 8 位随机小写字母与数字。

用法:
  python scripts/remove_nh_export_nohelmet_train.py --dry-run
  python scripts/remove_nh_export_nohelmet_train.py
"""
from __future__ import annotations

import argparse
import secrets
import shutil
import string
from pathlib import Path

from oversample_no_helmet import (
    IMG_EXT,
    count_class_in_label,
    is_oversample_copy_stem,
    load_no_helmet_id,
    stem_to_image,
)


def random_suffix(used: set[str], n: int = 8) -> str:
    alphabet = string.ascii_lowercase + string.digits
    while True:
        s = "".join(secrets.choice(alphabet) for _ in range(n))
        if s not in used:
            used.add(s)
            return s


def delete_nh_pairs(root: Path, dry: bool) -> tuple[int, int]:
    """返回 (删除的标签数, 缺失图片跳过数)。"""
    n_del = 0
    n_skip = 0
    for sp in ("train", "valid", "test"):
        img_dir = root / sp / "images"
        lbl_dir = root / sp / "labels"
        if not lbl_dir.is_dir():
            continue
        for lbl in list(lbl_dir.glob("*.txt")):
            if not is_oversample_copy_stem(lbl.stem):
                continue
            img = stem_to_image(img_dir, lbl.stem) if img_dir.is_dir() else None
            if img is None:
                n_skip += 1
                if not dry:
                    lbl.unlink(missing_ok=True)
                continue
            n_del += 1
            if not dry:
                lbl.unlink(missing_ok=True)
                img.unlink(missing_ok=True)
    return n_del, n_skip


def export_train_nohelmet(
    root: Path,
    dest_root: Path,
    nh_id: int,
    dry: bool,
) -> int:
    """复制 train 中含 no-helmet 框的样本到 dest_root/images、dest_root/labels。"""
    sp = "train"
    img_dir = root / sp / "images"
    lbl_dir = root / sp / "labels"
    out_img = dest_root / "images"
    out_lbl = dest_root / "labels"
    if not lbl_dir.is_dir():
        return 0
    if not dry:
        out_img.mkdir(parents=True, exist_ok=True)
        out_lbl.mkdir(parents=True, exist_ok=True)
    used_stems: set[str] = set()
    n = 0
    for lbl in sorted(lbl_dir.glob("*.txt")):
        if is_oversample_copy_stem(lbl.stem):
            continue
        if count_class_in_label(lbl, nh_id) == 0:
            continue
        img = stem_to_image(img_dir, lbl.stem) if img_dir.is_dir() else None
        if img is None:
            continue
        suf = random_suffix(used_stems)
        new_stem = f"{lbl.stem}_{suf}"
        dst_i = out_img / f"{new_stem}{img.suffix.lower()}"
        dst_t = out_lbl / f"{new_stem}.txt"
        n += 1
        if not dry:
            shutil.copy2(img, dst_i)
            shutil.copy2(lbl, dst_t)
    return n


def main() -> None:
    p = argparse.ArgumentParser(description="删除 nh 样本并导出含 no-helmet 的训练集")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    repo = Path(__file__).resolve().parent.parent
    data_dir = repo / "data"
    roots = ["final", "final_add"]
    export_base = data_dir / "no_helmet_train_export"

    ref_yaml = data_dir / "final" / "data.yaml"
    nh_id = load_no_helmet_id(ref_yaml)

    for rel in roots:
        root = data_dir / rel
        if not root.is_dir():
            print(f"[跳过] 不存在: {root}")
            continue
        d, sk = delete_nh_pairs(root, args.dry_run)
        print(f"=== {rel} 删除 nh 样本: {d} 对, 无图仅删标: {sk}")
        dest = export_base / rel
        n = export_train_nohelmet(root, dest, nh_id, args.dry_run)
        print(f"=== {rel} 导出 train 含 no-helmet -> {dest}: {n} 对\n")

    if args.dry_run:
        print("(dry-run: 未实际删除/复制)")


if __name__ == "__main__":
    main()
