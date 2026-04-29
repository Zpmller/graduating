"""
检查 YOLO 数据集目录：每个标签是否有对应图片、各 split 图/签数量，
并输出远程训练时易错点说明。

用法:
  python scripts/verify_yolo_dataset.py --root data/final
"""
from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def parse_yaml_simple(p: Path) -> dict:
    t = p.read_text(encoding="utf-8")
    out: dict = {}
    for key in ("path", "train", "val", "test"):
        m = re.search(rf"^\s*{key}:\s*(.+?)\s*$", t, re.MULTILINE)
        if m:
            out[key] = m.group(1).strip().strip("'\"")
    return out


def stem_to_image(img_dir: Path, stem: str) -> Path | None:
    for ext in IMG_EXT:
        q = img_dir / f"{stem}{ext}"
        if q.is_file():
            return q
    for f in img_dir.iterdir():
        if f.is_file() and f.stem == stem and f.suffix.lower() in IMG_EXT:
            return f
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="校验 YOLO 数据集路径与图签成对")
    ap.add_argument("--root", type=str, required=True, help="数据集根目录（含 data.yaml）")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent.parent
    root = (repo / args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"不存在: {root}")

    yml = root / "data.yaml"
    if not yml.is_file():
        raise SystemExit(f"缺少 data.yaml: {yml}")

    cfg = parse_yaml_simple(yml)
    path_field = cfg.get("path", ".")
    base = (root / path_field).resolve() if path_field not in (".", "") else root

    split_rels: list[tuple[str, str]] = []
    if "train" in cfg:
        split_rels.append(("train", cfg["train"]))
    if "val" in cfg:
        split_rels.append(("val", cfg["val"]))
    if "test" in cfg:
        split_rels.append(("test", cfg["test"]))

    print(f"数据集根: {root}")
    print(f"data.yaml path: {path_field!r}  → 基准目录: {base}")
    print()

    missing_img: list[str] = []
    missing_lbl: list[str] = []
    tot_lbl = tot_img_files = tot_empty = 0

    for name, rel in split_rels:
        idir = (base / rel).resolve()
        lbl_rel = str(rel).replace("/images", "/labels").replace("\\images", "\\labels")
        ldir = (base / lbl_rel).resolve()
        if not idir.is_dir():
            print(f"[错误] 无图片目录: {idir}")
            continue
        if not ldir.is_dir():
            print(f"[错误] 无标签目录: {ldir}")
            continue

        imgs = {f for f in idir.iterdir() if f.is_file() and f.suffix.lower() in IMG_EXT}
        tot_img_files += len(imgs)

        for lf in ldir.glob("*.txt"):
            tot_lbl += 1
            if not lf.read_text(encoding="utf-8", errors="ignore").strip():
                tot_empty += 1
            st = lf.stem
            if stem_to_image(idir, st) is None:
                missing_img.append(str(lf.relative_to(root)))

        for imf in imgs:
            lt = ldir / f"{imf.stem}.txt"
            if not lt.is_file():
                missing_lbl.append(str(imf.relative_to(root)))

        print(f"  [{name}] images={len(imgs)}  labels={len(list(ldir.glob('*.txt')))}  dir={idir.name}")

    print()
    print("--- 配对检查 ---")
    print(f"  图片文件总数: {tot_img_files}  标签文件: {tot_lbl}  空标签: {tot_empty}")
    print(f"  缺对应图的标签: {len(missing_img)}  缺对应标签的图: {len(missing_lbl)}")
    if missing_img[:8]:
        print("  缺图(示例):", missing_img[:8])
    if missing_lbl[:8]:
        print("  缺标签(示例):", missing_lbl[:8])

    print()
    print("--- 上传后仍找不到时逐项查 ---")
    print("  1) 解压后是否存在与本地相同的相对结构: <根>/train/images、<根>/valid/images、<根>/data.yaml")
    print("  2) Linux 目录名大小写必须与 yaml 一致: valid 不能写成 Valid。")
    print("  3) 训练命令里 data= 要用服务器上的绝对路径，例如:")
    print(f"       yolo train data={root.as_posix()}/data.yaml")
    print("  4) 若用 Docker/挂载，确认挂载路径与 data= 一致。")
    print("  5) 打包并生成清单: python scripts/zip_data_folder.py --folder final --manifest")
    print()


if __name__ == "__main__":
    main()
