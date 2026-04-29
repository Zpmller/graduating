"""
对 merged_four 与「副本」训练集中、标签含 no-helmet（默认类 6）的图片做 SHA256，
同一哈希多份时保留 merged_four 下的一份，删除其余路径下的文件（及同名 .txt 标签）。

默认扫描:
  data/merged_four/train
  data/nohelmet_subset/train
  data/nohelmet_subset_v2/train

用法（在 ai_edge_system 目录下）:
  python scripts/dedupe_nohelmet_train_by_hash.py
  python scripts/dedupe_nohelmet_train_by_hash.py --apply
"""
from __future__ import annotations

import argparse
import hashlib
from collections import defaultdict
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
NO_HELMET_ID = 6


def label_has_class(lbl: Path, cid: int) -> bool:
    if not lbl.is_file():
        return False
    for line in lbl.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        try:
            if int(parts[0]) == cid:
                return True
        except ValueError:
            continue
    return False


def sha256_file(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def collect_nohelmet_train_images(root_name: str, data_root: Path) -> list[tuple[str, Path]]:
    """返回 [(root_name, image_path), ...]，仅含标签中存在 class 6 的图。"""
    img_dir = data_root / "train" / "images"
    lbl_dir = data_root / "train" / "labels"
    if not img_dir.is_dir() or not lbl_dir.is_dir():
        return []
    out: list[tuple[str, Path]] = []
    for img in sorted(img_dir.iterdir()):
        if not img.is_file() or img.suffix.lower() not in IMG_EXT:
            continue
        stem = img.stem
        lbl = lbl_dir / f"{stem}.txt"
        if not label_has_class(lbl, NO_HELMET_ID):
            continue
        out.append((root_name, img))
    return out


def prefer_keep(paths: list[Path], merged_anchor: str) -> Path:
    """优先保留 merged_anchor 目录下、路径最短的那份（一般为未加随机后缀的原始文件）。"""
    merged = [p for p in paths if merged_anchor in p.as_posix()]
    if merged:
        return min(merged, key=lambda p: (len(p.name), len(str(p))))
    return min(paths, key=lambda p: (len(p.name), str(p)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--roots",
        type=str,
        default="merged_four,nohelmet_subset,nohelmet_subset_v2",
        help="逗号分隔：data 下子目录名",
    )
    ap.add_argument("--merged-name", type=str, default="merged_four", help="保留副本时优先保留该目录下的文件")
    ap.add_argument("--apply", action="store_true", help="执行删除（默认仅统计与预览）")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent.parent
    data_dir = repo / "data"
    root_names = [x.strip() for x in args.roots.split(",") if x.strip()]

    all_items: list[tuple[str, Path]] = []
    for name in root_names:
        items = collect_nohelmet_train_images(name, data_dir / name)
        print(f"[{name}] 含 no-helmet 的训练图: {len(items)}")
        all_items.extend(items)

    by_hash: dict[str, list[Path]] = defaultdict(list)
    for _rn, img in all_items:
        try:
            h = sha256_file(img)
        except OSError as e:
            print(f"  跳过（读失败）: {img} ({e})")
            continue
        by_hash[h].append(img)

    dup_groups = {h: paths for h, paths in by_hash.items() if len(paths) > 1}
    triple_or_more = sum(1 for ps in dup_groups.values() if len(ps) >= 3)
    print(f"\n唯一哈希数: {len(by_hash)}")
    print(f"重复哈希组数（>=2 个路径）: {len(dup_groups)}")
    print(f"其中组内文件数 >=3 的组数: {triple_or_more}")

    to_delete: list[Path] = []
    for h, paths in sorted(dup_groups.items(), key=lambda x: -len(x[1])):
        uniq_roots = {p.parts[p.parts.index("data") + 1] if "data" in p.parts else "" for p in paths}
        keep = prefer_keep(paths, args.merged_name)
        for p in paths:
            if p != keep:
                to_delete.append(p)

    print(f"\n将删除图片数（去重后路径数）: {len(to_delete)}")
    if not args.apply:
        print("未指定 --apply，仅预览。确认删除请: python scripts/dedupe_nohelmet_train_by_hash.py --apply")
        for h, paths in list(dup_groups.items())[:15]:
            print(f"\n哈希 ...{h[-12:]}  共 {len(paths)} 个文件")
            keep = prefer_keep(paths, args.merged_name)
            for p in paths:
                mark = "保留" if p == keep else "删"
                print(f"  [{mark}] {p}")
        if len(dup_groups) > 15:
            print(f"\n... 另有 {len(dup_groups) - 15} 组未展开")
        return

    deleted_img = 0
    deleted_lbl = 0
    err = 0
    for img in to_delete:
        lbl = img.parent.parent / "labels" / f"{img.stem}.txt"
        try:
            img.unlink()
            deleted_img += 1
        except OSError as e:
            print(f"删图失败 {img}: {e}")
            err += 1
            continue
        if lbl.is_file():
            try:
                lbl.unlink()
                deleted_lbl += 1
            except OSError as e:
                print(f"删标签失败 {lbl}: {e}")
                err += 1

    print(f"\n已删除: 图片 {deleted_img}, 标签 {deleted_lbl}, 错误 {err}")


if __name__ == "__main__":
    main()
