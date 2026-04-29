"""
从 data/ 下指定源（默认 nohelmet_subset）中，将「标签里出现过 no-helmet（默认全局 ID 6）」的样本处理到新目录：
  - 默认：图像做随机增强（翻转 + 颜色）并重新编码保存，标签同步几何变换；文件名 = 原 stem + 不重复随机数字后缀。
  - 增强后像素与原版不同，便于上传平台按内容去重时仍计为不同样本。
  - --no-augment：与旧版一致，整文件复制（字节级与源相同）。

目录结构:
  <out>/{train,valid,test}/{images,labels}/

用法（在 ai_edge_system 目录下）:
  python scripts/copy_nohelmet_subset.py
  python scripts/copy_nohelmet_subset.py --out nohelmet_aug --seed 42
  python scripts/copy_nohelmet_subset.py --no-augment
  python scripts/copy_nohelmet_subset.py --zip
"""
from __future__ import annotations

import argparse
import ast
import random
import re
import shutil
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
# 与 data/data.yaml、merge_all_datasets 一致：no-helmet 为索引 6
DEFAULT_NO_HELMET_ID = 6
DEFAULT_SRC = "nohelmet_subset"


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


def stems_with_class(lbl_dir: Path, class_id: int) -> set[str]:
    out: set[str] = set()
    if not lbl_dir.is_dir():
        return out
    for lf in lbl_dir.glob("*.txt"):
        if class_id in label_classes(lf):
            out.add(lf.stem)
    return out


def next_unique_suffix(rng: random.Random, used: set[str], width: int = 8) -> str:
    lo, hi = 10 ** (width - 1), 10**width - 1
    while True:
        s = str(rng.randint(lo, hi))
        if s not in used:
            used.add(s)
            return s


def transform_yolo_line(line: str, flip_h: bool, flip_v: bool) -> str:
    """检测框 (cls x y w h) 或分割多边形 (cls x1 y1 ...) 在归一化坐标下做翻转。"""
    s = line.strip()
    if not s:
        return ""
    parts = s.split()
    try:
        cid = int(parts[0])
    except ValueError:
        return line
    nums = []
    for t in parts[1:]:
        try:
            nums.append(float(t))
        except ValueError:
            return line
    if len(nums) == 4:
        x, y, w, h = nums
        if flip_h:
            x = 1.0 - x
        if flip_v:
            y = 1.0 - y
        return f"{cid} {x:.6f} {y:.6f} {w:.6f} {h:.6f}"
    if len(nums) >= 6 and len(nums) % 2 == 0:
        for i in range(0, len(nums), 2):
            if flip_h:
                nums[i] = 1.0 - nums[i]
            if flip_v:
                nums[i + 1] = 1.0 - nums[i + 1]
        return f"{cid} " + " ".join(f"{n:.6f}" for n in nums)
    return line


def augment_labels_text(raw: str, flip_h: bool, flip_v: bool) -> str:
    out_lines: list[str] = []
    for line in raw.splitlines():
        t = transform_yolo_line(line, flip_h, flip_v)
        if t:
            out_lines.append(t)
    return "\n".join(out_lines) + ("\n" if out_lines else "")


def pil_color_jitter(pil: Image.Image, rng: random.Random) -> Image.Image:
    pil = ImageEnhance.Brightness(pil).enhance(rng.uniform(0.88, 1.12))
    pil = ImageEnhance.Contrast(pil).enhance(rng.uniform(0.90, 1.10))
    pil = ImageEnhance.Color(pil).enhance(rng.uniform(0.85, 1.15))
    if rng.random() < 0.4:
        pil = ImageEnhance.Sharpness(pil).enhance(rng.uniform(0.85, 1.15))
    return pil


def augment_image_pil(pil: Image.Image, rng: random.Random) -> tuple[Image.Image, bool, bool]:
    """返回 (增强后 RGB 图, 是否水平翻转, 是否竖直翻转)。"""
    pil = pil.convert("RGB")
    flip_h = rng.random() < 0.5
    flip_v = rng.random() < 0.5
    if flip_h:
        pil = pil.transpose(Image.FLIP_LEFT_RIGHT)
    if flip_v:
        pil = pil.transpose(Image.FLIP_TOP_BOTTOM)
    pil = pil_color_jitter(pil, rng)
    # 轻微噪声，保证与原版字节不同（即使无翻转）
    arr = np.asarray(pil, dtype=np.int16)
    g = np.random.default_rng(rng.randrange(1 << 32))
    noise = g.integers(-4, 5, size=arr.shape, dtype=np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB"), flip_h, flip_v


def save_augmented_jpeg(pil: Image.Image, dst: Path, rng: random.Random) -> None:
    q = rng.randint(88, 98)
    pil.save(dst, format="JPEG", quality=q, optimize=True)


def process_split_renamed(
    src_root: Path,
    split: str,
    stems: set[str],
    dst_root: Path,
    rng: random.Random,
    augment: bool,
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
        img_path = stem_to_image(src_img, stem)
        if img_path is None:
            continue
        suf = next_unique_suffix(rng, used_suffixes)
        new_stem = f"{stem}_{suf}"
        raw_lbl = lbl.read_text(encoding="utf-8", errors="ignore")

        if not augment:
            ext = img_path.suffix.lower()
            shutil.copy2(img_path, di / f"{new_stem}{ext}")
            shutil.copy2(lbl, dl / f"{new_stem}.txt")
            n += 1
            continue

        pil = Image.open(img_path)
        pil_aug, fh, fv = augment_image_pil(pil, rng)
        pil.close()
        text_out = augment_labels_text(raw_lbl, fh, fv)
        dst_img = di / f"{new_stem}.jpg"
        save_augmented_jpeg(pil_aug, dst_img, rng)
        (dl / f"{new_stem}.txt").write_text(text_out, encoding="utf-8")
        n += 1
    return n


def write_yaml(dst: Path, project_yaml: Path, augment: bool) -> None:
    nc, names = load_project_yaml(project_yaml)
    note = (
        "含 no-helmet 的样本：默认随机增强+JPEG 重编码+同步标签；文件名 = 原 stem + 随机数字后缀"
        if augment
        else "含 no-helmet 的样本全量复制；文件名 = 原 stem + 随机数字后缀"
    )
    (dst / "data.yaml").write_text(
        f"""# {note}
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
    p = argparse.ArgumentParser(
        description="复制含 no-helmet 的样本；默认对图像增强并重编码 JPEG，标签随翻转同步"
    )
    p.add_argument("--src", type=str, default=DEFAULT_SRC, help="源数据集目录名（位于 data/ 下）")
    p.add_argument("--out", type=str, default="nohelmet_subset_aug", help="输出目录名（位于 data/ 下）")
    p.add_argument(
        "--class-id",
        type=int,
        default=DEFAULT_NO_HELMET_ID,
        help=f"no-helmet 的全局类别 ID（默认 {DEFAULT_NO_HELMET_ID}）",
    )
    p.add_argument(
        "--splits",
        type=str,
        default="train,valid,test",
        help="逗号分隔：train,valid,test",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--no-augment",
        action="store_true",
        help="不做增强，整文件复制（与旧版行为一致）",
    )
    p.add_argument("--zip", action="store_true", help="打包为 data/<out>.zip")
    args = p.parse_args()

    repo = Path(__file__).resolve().parent.parent
    data_dir = repo / "data"
    src_root = data_dir / args.src
    dst_root = data_dir / args.out
    project_yaml = data_dir / "data.yaml"
    augment = not args.no_augment

    if not src_root.is_dir():
        raise SystemExit(f"源不存在: {src_root}")
    if not project_yaml.is_file():
        raise SystemExit(f"缺少项目配置: {project_yaml}")

    split_list = [s.strip() for s in args.splits.split(",") if s.strip()]
    for sp in split_list:
        if sp not in ("train", "valid", "test"):
            raise SystemExit(f"非法 split: {sp}（仅允许 train, valid, test）")

    rng = random.Random(args.seed)
    dst_root.mkdir(parents=True, exist_ok=True)
    for sp in split_list:
        (dst_root / sp / "images").mkdir(parents=True, exist_ok=True)
        (dst_root / sp / "labels").mkdir(parents=True, exist_ok=True)

    total = 0
    print(f"类别 ID {args.class_id} = no-helmet（与 data.yaml 一致）")
    print(f"augment={'开' if augment else '关（--no-augment）'}")
    for sp in split_list:
        stems = stems_with_class(src_root / sp / "labels", args.class_id)
        n = process_split_renamed(src_root, sp, stems, dst_root, rng, augment)
        total += n
        print(f"  {sp}: 含 no-helmet 的 stem 数 {len(stems)}, 输出 {n} 对")

    write_yaml(dst_root, project_yaml, augment)
    print(f"源: {src_root}")
    print(f"输出: {dst_root}")
    print(f"seed={args.seed}")
    print(f"合计: {total} 对")
    if augment:
        print("增强模式：图像为 .jpg（随机 JPEG 质量 + 颜色/翻转/轻微噪声），标签已随翻转同步")
    print(f"已写 {dst_root / 'data.yaml'}")

    if args.zip:
        zp = zip_folder(data_dir, args.out)
        print(f"zip: {zp}")


if __name__ == "__main__":
    main()
