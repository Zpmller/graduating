"""
1) helmet1：删除所有 person 框（原全局类 ID 6），图片保留。
2) helmet3：从 train 按固定间隔划分出一部分到 test（使 train/valid/test 均存在）。

勿在已有 5/6/7 全局标签的 helmet3 上直接运行旧版 clean_helmet3（会误删）。
若标签被清空，可用 scripts/restore_helmet3_labels_from_merged.py 从 merged_all 恢复后再改 7 类。

用法（在 ai_edge_system 下）:
  python scripts/prep_helmet_no_person_and_helmet3_test.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
DATA = Path(__file__).resolve().parent.parent / "data"


def strip_class_from_labels(lbl_dir: Path, drop_ids: set[int]) -> tuple[int, int]:
    """返回 (删除行数, 涉及文件数)"""
    removed_lines = 0
    touched = 0
    if not lbl_dir.is_dir():
        return 0, 0
    for fp in lbl_dir.glob("*.txt"):
        text = fp.read_text(encoding="utf-8", errors="ignore")
        out: list[str] = []
        changed = False
        for line in text.splitlines():
            parts = line.strip().split()
            if len(parts) != 5:
                if parts:
                    out.append(line.rstrip() + "\n")
                continue
            try:
                cid = int(parts[0])
            except ValueError:
                out.append(line.rstrip() + "\n")
                continue
            if cid in drop_ids:
                removed_lines += 1
                changed = True
                continue
            out.append(line.rstrip() + "\n")
        if changed:
            touched += 1
            fp.write_text("".join(out), encoding="utf-8")
    return removed_lines, touched


def helmet3_train_to_test(root: Path, every_n: int = 8) -> tuple[int, int]:
    """每 every_n 张从 train 移 1 张到 test。返回 (移动图片数, 移动标签数)"""
    train_img = root / "train" / "images"
    train_lbl = root / "train" / "labels"
    test_img = root / "test" / "images"
    test_lbl = root / "test" / "labels"
    test_img.mkdir(parents=True, exist_ok=True)
    test_lbl.mkdir(parents=True, exist_ok=True)

    imgs = sorted(p for p in train_img.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXT)
    moved_i = moved_l = 0
    for i, p in enumerate(imgs):
        if i % every_n != 0:
            continue
        dest = test_img / p.name
        if dest.exists():
            continue
        shutil.move(str(p), dest)
        moved_i += 1
        stem = p.stem
        lf = train_lbl / f"{stem}.txt"
        df = test_lbl / f"{stem}.txt"
        if lf.is_file():
            shutil.move(str(lf), df)
        else:
            df.write_text("", encoding="utf-8")
        moved_l += 1
    return moved_i, moved_l


def main() -> None:
    h1 = DATA / "helmet" / "helmet1"
    h3 = DATA / "helmet" / "helmet3"

    print("=== helmet1: 删除类 6 (person) 标注行 ===")
    total_r = total_t = 0
    for sp in ("train", "valid", "test"):
        r, t = strip_class_from_labels(h1 / sp / "labels", {6})
        total_r += r
        total_t += t
        print(f"  {sp}: 删 {r} 行, 改写 {t} 个 txt")
    print(f"  合计删行 {total_r}\n")

    print("=== helmet3: train -> test 划分（每 8 张取 1 张）===")
    mi, ml = helmet3_train_to_test(h3, every_n=8)
    print(f"  移动图片 {mi}, 标签 {ml}")
    print("\n下一步请执行: python scripts/clean_helmet3_labels.py")


if __name__ == "__main__":
    main()
