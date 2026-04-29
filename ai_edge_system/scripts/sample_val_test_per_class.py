"""
从合并数据集（默认 merged_four）的 valid、test 中，按「每个类别」各随机抽取一定比例样本，
复制到新目录；文件名在原有 stem 后追加不重复的随机数字后缀，标签内容不变。

目录结构:
  <out>/{valid,test}/{images,labels}/  与 YOLO 习惯一致

用法（在 ai_edge_system 目录下）:
  python scripts/sample_val_test_per_class.py
  python scripts/sample_val_test_per_class.py --out sampled_eval_10pct --ratio 0.1 --seed 42
  python scripts/sample_val_test_per_class.py --zip
"""
from __future__ import annotations

import argparse
import ast
import math
import random
import re
import shutil
import zipfile
from collections import defaultdict
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
NC = 7


def load_project_yaml(data_yaml: Path) -> tuple[int, list[str]]:
    text = data_yaml.read_text(encoding="utf-8")
    nc_m = re.search(r"^\s*nc:\s*(\d+)\s*$", text, re.MULTILINE)
    nm_m = re.search(r"^\s*names:\s*(\[.*\])\s*$", text, re.MULTILINE)
    if not nc_m or not nm_m:
        raise ValueError(f"无法解析 nc/names: {data_yaml}")
    return int(nc_m.group(1)), ast.literal_eval(nm_m.group(1))


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


def next_unique_suffix(rng: random.Random, used: set[str], width: int = 8) -> str:
    lo, hi = 10 ** (width - 1), 10**width - 1
    while True:
        s = str(rng.randint(lo, hi))
        if s not in used:
            used.add(s)
            return s


def copy_split_renamed(
    src_root: Path,
    split: str,
    stems: set[str],
    dst_root: Path,
    rng: random.Random,
) -> int:
    src_img = src_root / split / "images"
    src_lbl = src_root / split / "labels"
    di = dst_root / split / "images"
    dl = dst_root / split / "labels"
    di.mkdir(parents=True, exist_ok=True)
    dl.mkdir(parents=True, exist_ok=True)
    used_suffixes: set[str] = set()
    n = 0
    for stem in sorted(stems):
        lbl = src_lbl / f"{stem}.txt"
        if not lbl.is_file():
            continue
        img = stem_to_image(src_img, stem)
        if img is None:
            continue
        suf = next_unique_suffix(rng, used_suffixes)
        new_stem = f"{stem}_{suf}"
        ext = img.suffix.lower()
        shutil.copy2(img, di / f"{new_stem}{ext}")
        shutil.copy2(lbl, dl / f"{new_stem}.txt")
        n += 1
    return n


def write_yaml(dst: Path, project_yaml: Path) -> None:
    nc, names = load_project_yaml(project_yaml)
    (dst / "data.yaml").write_text(
        f"""# 从 merged_four 的 valid/test 按类抽样复制；文件名 = 原 stem + 随机数字后缀
train: train/images
val: valid/images
test: test/images

nc: {nc}
names: {names}
""",
        encoding="utf-8",
    )


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
    p = argparse.ArgumentParser(description="valid/test 按类抽样复制并重命名（随机数字后缀）")
    p.add_argument("--src", type=str, default="merged_four", help="源数据集目录名（位于 data/ 下）")
    p.add_argument("--out", type=str, default="sampled_val_test_10pct", help="输出目录名（位于 data/ 下）")
    p.add_argument("--ratio", type=float, default=0.1, help="各类别在该划分内抽样比例（ceil，每类至少 1 张若有样本）")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--zip", action="store_true", help="打包为 data/<out>.zip")
    args = p.parse_args()

    repo = Path(__file__).resolve().parent.parent
    data_dir = repo / "data"
    src_root = data_dir / args.src
    dst_root = data_dir / args.out
    project_yaml = data_dir / "data.yaml"

    if not src_root.is_dir():
        raise SystemExit(f"源不存在: {src_root}")
    if not project_yaml.is_file():
        raise SystemExit(f"缺少项目配置: {project_yaml}")

    rng = random.Random(args.seed)
    by_v = stems_per_class(src_root / "valid" / "labels")
    by_t = stems_per_class(src_root / "test" / "labels")
    u_v = sample_stems_union(by_v, args.ratio, rng)
    u_t = sample_stems_union(by_t, args.ratio, rng)

    dst_root.mkdir(parents=True, exist_ok=True)
    (dst_root / "train" / "images").mkdir(parents=True, exist_ok=True)
    (dst_root / "train" / "labels").mkdir(parents=True, exist_ok=True)

    nv = copy_split_renamed(src_root, "valid", u_v, dst_root, rng)
    nt = copy_split_renamed(src_root, "test", u_t, dst_root, rng)

    write_yaml(dst_root, project_yaml)

    print(f"源: {src_root}")
    print(f"输出: {dst_root}")
    print(f"ratio={args.ratio}, seed={args.seed}")
    print(f"valid: 抽样 stem 数 {len(u_v)}, 复制 {nv} 对（stem_随机8位数字.扩展名）")
    print(f"test:  抽样 stem 数 {len(u_t)}, 复制 {nt} 对")
    print(f"已写 {dst_root / 'data.yaml'}（train 目录为空占位，训练请用主 data.yaml 或删 train 行）")

    if args.zip:
        zp = zip_folder(data_dir, args.out)
        print(f"zip: {zp}")


if __name__ == "__main__":
    main()
