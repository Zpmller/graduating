"""
将多个子数据集按 data/data.yaml 的全局 7 类 ID 重映射后合并为单一 YOLO 目录，并在 data/ 下生成同名 zip。

默认仅合并四源（与项目常用 Roboflow 导出一致）:
  - face/Face detection with yolov8.v2i.yolov11
  - fire/Fire
  - gas_cylinder/CylinDeRS
  - helmet/industry_safety.v2i.yolov11

输出:
  data/<out_name>/{train,valid,test}/{images,labels}
  data/<out_name>/data.yaml
  data/<out_name>.zip

用法（在 ai_edge_system 目录下）:
  python scripts/merge_all_datasets.py
  python scripts/merge_all_datasets.py --preset full --out merged_all   # 原先 7 子源合并
  python scripts/merge_all_datasets.py --dry-run
  python scripts/merge_all_datasets.py --clean
  python scripts/merge_all_datasets.py --no-zip
  python scripts/merge_all_datasets.py --validate-only
  python scripts/merge_all_datasets.py --no-validate
"""
from __future__ import annotations

import argparse
import math
import shutil
import zipfile
from collections import defaultdict
from pathlib import Path

# 7 类：无 person；no-helmet 索引为 6
GLOBAL_NAMES = ["face", "fire", "smoke", "sparks", "gas_cylinder", "helmet", "no-helmet"]

# 四源合并：类别对齐 data/data.yaml（nc=7, names 同上）
SOURCES_FOUR: list[dict] = [
    {"id": "face", "root": "face/Face detection with yolov8.v2i.yolov11", "mapping": {0: 0}},
    # Fire/data.yaml: 0=Fire-Smoke,1=fire,2=smoke,3=spark → 合并 Fire-Smoke 框为 fire(1)
    {"id": "fire", "root": "fire/Fire", "mapping": {0: 1, 1: 1, 2: 2, 3: 3}},
    {"id": "cylinder", "root": "gas_cylinder/CylinDeRS", "mapping": {4: 4}},
    # industry_safety：Roboflow 0/1 或已对齐的 5/6/7（见 clean_helmet2_labels.py）
    {
        "id": "helmet_industry",
        "root": "helmet/industry_safety.v2i.yolov11",
        "mapping": {0: 5, 1: 6, 5: 5, 6: 6, 7: 6},
    },
]

# 扩展合并：与旧版 data/data.yaml 多路径一致；缺失目录在合并时会跳过
SOURCES_FULL: list[dict] = [
    {"id": "face", "root": "face/Face detection with yolov8.v2i.yolov11", "mapping": {0: 0}},
    {
        "id": "fire_smoke",
        "root": "fire/Fire and smoke detection.v2i.yolov11",
        "mapping": {1: 1, 2: 2},
    },
    {"id": "spark", "root": "fire/Spark.v2i.yolov11", "mapping": {0: 3, 1: 3, 2: 3, 3: 3}},
    {"id": "cylinder", "root": "gas_cylinder/CylinDeRS", "mapping": {4: 4}},
    {"id": "helmet1", "root": "helmet/helmet1", "mapping": {5: 5, 6: 6, 7: 6}},
    {"id": "helmet2", "root": "helmet/helmet2", "mapping": {0: 5, 1: 6, 5: 5, 6: 6, 7: 6}},
    {"id": "helmet3", "root": "helmet/helmet3", "mapping": {0: 6, 1: 5, 5: 5, 6: 6, 7: 6}},
]


def sources_for_preset(preset: str) -> list[dict]:
    if preset == "four":
        return SOURCES_FOUR
    if preset == "full":
        return SOURCES_FULL
    raise ValueError(f"unknown preset: {preset}")

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
SPLITS = ("train", "valid", "test")

# 归一化坐标允许轻微越界（导出误差）；超过则计为错误
BBOX_WARN_LO, BBOX_WARN_HI = -0.02, 1.02
BBOX_ERR_LO, BBOX_ERR_HI = -0.5, 1.5


def polygon_norm_to_bbox_xywh(coords: list[float]) -> tuple[float, float, float, float] | None:
    """归一化多边形顶点 → YOLO 检测框 (xc, yc, w, h)。"""
    if len(coords) < 6 or len(coords) % 2 != 0:
        return None
    xs = coords[0::2]
    ys = coords[1::2]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    w, h = xmax - xmin, ymax - ymin
    if w <= 0 or h <= 0:
        return None
    return (xmin + xmax) / 2, (ymin + ymax) / 2, w, h


def parse_yolo_line(parts: list[str]) -> tuple[int, float, float, float, float] | None:
    """
    单行 YOLO：5 列检测框，或 1+2k 列分割多边形（转为外接矩形框）。
    无法解析则返回 None。
    """
    if len(parts) < 2:
        return None
    try:
        cid = int(parts[0])
    except ValueError:
        return None
    nums: list[float] = []
    for t in parts[1:]:
        try:
            nums.append(float(t))
        except ValueError:
            return None
    if len(parts) == 5:
        x, y, w, h = nums
        return cid, x, y, w, h
    poly = polygon_norm_to_bbox_xywh(nums)
    if poly is None:
        return None
    return cid, poly[0], poly[1], poly[2], poly[3]


def validate_sources(data_dir: Path, sources: list[dict]) -> tuple[int, int]:
    """
    检查各子集 labels：类别须在合并 mapping 内、每行 5 列、数值合法。
    打印报告，返回 (error_count, warn_count)。
    """
    errors = 0
    warns = 0

    print("======== 标注检查（合并前，相对各子集原始类别 ID） ========")

    for src in sources:
        sid = src["id"]
        mapping: dict[int, int] = src["mapping"]
        allowed = set(mapping.keys())
        print(f"\n--- [{sid}] {src['root']} ---")
        print(f"    允许的原始类别 ID: {sorted(allowed)}")
        print(f"    映射到全局: " + ", ".join(f"{k}->{GLOBAL_NAMES[mapping[k]]}({mapping[k]})" for k in sorted(allowed)))

        raw_class_counts: dict[int, int] = defaultdict(int)
        unknown_class: dict[int, int] = defaultdict(int)
        bad_lines = 0
        bbox_warns = 0
        bbox_errs = 0
        n_files = 0
        n_boxes = 0
        example_unknown: list[str] = []

        for sp in SPLITS:
            lbl_dir = data_dir / src["root"] / sp / "labels"
            if not lbl_dir.is_dir():
                continue
            for lf in sorted(lbl_dir.glob("*.txt")):
                n_files += 1
                text = lf.read_text(encoding="utf-8", errors="ignore")
                for line_no, line in enumerate(text.splitlines(), 1):
                    parts = line.strip().split()
                    if not parts:
                        continue
                    parsed = parse_yolo_line(parts)
                    if parsed is None:
                        bad_lines += 1
                        errors += 1
                        if bad_lines <= 3:
                            print(f"    [错误] 无法解析行: {lf.relative_to(data_dir)} 第{line_no}行")
                        continue
                    cid, x, y, w, h = parsed
                    if cid not in allowed:
                        unknown_class[cid] += 1
                        errors += 1
                        if len(example_unknown) < 5:
                            example_unknown.append(f"{lf.name}:{line_no} cls={cid}")
                        continue
                    if w <= 0 or h <= 0 or not all(math.isfinite(v) for v in (x, y, w, h)):
                        bbox_errs += 1
                        errors += 1
                        continue
                    oob_hard = False
                    for v in (x, y, w, h):
                        if v < BBOX_ERR_LO or v > BBOX_ERR_HI:
                            oob_hard = True
                            break
                    if oob_hard:
                        bbox_errs += 1
                        errors += 1
                        continue
                    for v in (x, y, w, h):
                        if v < BBOX_WARN_LO or v > BBOX_WARN_HI:
                            bbox_warns += 1

                    raw_class_counts[cid] += 1
                    n_boxes += 1

        if n_files == 0:
            print("    (无 labels 目录或为空，已跳过)")
            continue

        print(f"    标签文件数: {n_files}, 合法标注框: {n_boxes}")
        if raw_class_counts:
            dist = ", ".join(f"{k}:{raw_class_counts[k]}" for k in sorted(raw_class_counts.keys()))
            print(f"    原始类别计数: {dist}")
        if unknown_class:
            u = ", ".join(f"{k}:{unknown_class[k]}" for k in sorted(unknown_class.keys()))
            print(f"    [错误] 未在映射表中的类别及出现次数: {u}")
            for ex in example_unknown:
                print(f"            例: {ex}")
        if bad_lines:
            print(f"    [错误] 格式错误行数: {bad_lines}")
        if bbox_errs:
            print(f"    [错误] bbox 数值异常行数: {bbox_errs}")
        if bbox_warns:
            print(f"    [警告] bbox 轻微越界行数: {bbox_warns}（仍可用）")
        warns += bbox_warns
        if not unknown_class and not bad_lines and not bbox_errs:
            msg = "    结论: 类别与行格式检查通过。"
            if bbox_warns:
                msg += "（存在轻微越界警告）"
            print(msg)

    print()
    print(f"======== 检查结束: 错误={errors}, 警告={warns} ========")
    return errors, warns


def remap_label_lines(text: str, mapping: dict[int, int]) -> str:
    out_lines: list[str] = []
    for line in text.splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        parsed = parse_yolo_line(parts)
        if parsed is None:
            continue
        cid, x, y, w, h = parsed
        if cid not in mapping:
            continue
        nid = mapping[cid]
        out_lines.append(f"{nid} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")
    return "".join(out_lines)


def merge_one_split(
    data_dir: Path,
    out_dir: Path,
    split: str,
    dry_run: bool,
    sources: list[dict],
) -> tuple[int, int]:
    img_n = 0
    lbl_n = 0
    images_out = out_dir / split / "images"
    labels_out = out_dir / split / "labels"
    if not dry_run:
        images_out.mkdir(parents=True, exist_ok=True)
        labels_out.mkdir(parents=True, exist_ok=True)

    for src in sources:
        src_root = data_dir / src["root"]
        mapping = src["mapping"]
        prefix = src["id"]
        img_dir = src_root / split / "images"
        lbl_dir = src_root / split / "labels"
        if not img_dir.is_dir():
            print(f"  [跳过] 无目录: {img_dir}")
            continue

        for img_path in sorted(img_dir.iterdir()):
            if not img_path.is_file() or img_path.suffix.lower() not in IMG_EXT:
                continue
            stem = img_path.stem
            new_base = f"{prefix}__{stem}"
            new_img_name = new_base + img_path.suffix.lower()
            dst_img = images_out / new_img_name
            lbl_path = lbl_dir / f"{stem}.txt"
            dst_lbl = labels_out / f"{new_base}.txt"

            if dry_run:
                img_n += 1
                if lbl_path.is_file():
                    lbl_n += 1
                continue

            shutil.copy2(img_path, dst_img)
            img_n += 1

            if lbl_path.is_file():
                raw = lbl_path.read_text(encoding="utf-8", errors="ignore")
                remapped = remap_label_lines(raw, mapping)
                dst_lbl.write_text(remapped, encoding="utf-8")
                lbl_n += 1
            else:
                dst_lbl.write_text("", encoding="utf-8")

    return img_n, lbl_n


def write_data_yaml(out_dir: Path, preset: str) -> None:
    note = "四源合并: face + fire/Fire + CylinDeRS + industry_safety" if preset == "four" else "多源合并（--preset full）"
    content = f"""# {note}
# 全局类别与 data/data.yaml 一致；由 scripts/merge_all_datasets.py 生成

path: .
train: train/images
val: valid/images
test: test/images

nc: {len(GLOBAL_NAMES)}
names: {GLOBAL_NAMES}
"""
    (out_dir / "data.yaml").write_text(content, encoding="utf-8")


def print_label_stats(merged_root: Path) -> None:
    """统计合并目录下各 txt 中的 YOLO 标注行（目标框数量）。"""
    by_class: dict[int, int] = defaultdict(int)
    by_split_class: dict[str, dict[int, int]] = {s: defaultdict(int) for s in SPLITS}
    by_prefix_class: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    total_boxes = 0
    empty_label_files = 0
    label_files = 0

    for sp in SPLITS:
        lbl_dir = merged_root / sp / "labels"
        if not lbl_dir.is_dir():
            continue
        for lf in lbl_dir.iterdir():
            if lf.suffix.lower() != ".txt" or not lf.is_file():
                continue
            label_files += 1
            text = lf.read_text(encoding="utf-8", errors="ignore")
            segs = lf.stem.split("__", 1)
            prefix = segs[0] if len(segs) == 2 else "unknown"
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if not lines:
                empty_label_files += 1
            for line in lines:
                toks = line.split()
                if not toks:
                    continue
                try:
                    c = int(toks[0])
                except ValueError:
                    continue
                by_class[c] += 1
                by_split_class[sp][c] += 1
                by_prefix_class[prefix][c] += 1
                total_boxes += 1

    print()
    print("======== 标签框统计（合并后） ========")
    print(f"标签文件数: {label_files}")
    print(f"空标签文件数（无标注行）: {empty_label_files}")
    print(f"标注框总数: {total_boxes}")
    if total_boxes == 0:
        print("(无标注框)")
        return

    print()
    print("--- 按类别（全局 ID） ---")
    for cid in range(len(GLOBAL_NAMES)):
        n = by_class.get(cid, 0)
        pct = 100.0 * n / total_boxes
        print(f"  [{cid}] {GLOBAL_NAMES[cid]:<14} {n:>10}  ({pct:5.2f}%)")

    print()
    print("--- 按划分 train / valid / test（各类框数） ---")
    header = f"{'split':<8}" + "".join(f" {GLOBAL_NAMES[i][:6]:>7}" for i in range(len(GLOBAL_NAMES))) + f" {'sum':>10}"
    print(header)
    print("-" * len(header))
    for sp in SPLITS:
        row = f"{sp:<8}"
        ssum = 0
        for cid in range(len(GLOBAL_NAMES)):
            n = by_split_class[sp].get(cid, 0)
            ssum += n
            row += f" {n:>7}"
        row += f" {ssum:>10}"
        print(row)

    print()
    print("--- 按数据源（文件名前缀，各类框数） ---")
    prefixes = sorted(by_prefix_class.keys())
    w = max(len(p) for p in prefixes) if prefixes else 10
    h2 = f"{'source':<{w}}" + "".join(f" {GLOBAL_NAMES[i][:6]:>7}" for i in range(len(GLOBAL_NAMES))) + f" {'sum':>10}"
    print(h2)
    print("-" * len(h2))
    for prefix in prefixes:
        row = f"{prefix:<{w}}"
        ssum = 0
        for cid in range(len(GLOBAL_NAMES)):
            n = by_prefix_class[prefix].get(cid, 0)
            ssum += n
            row += f" {n:>7}"
        row += f" {ssum:>10}"
        print(row)


def zip_merged_folder(data_dir: Path, folder_name: str) -> Path:
    """在 data/ 下生成 zip；若 merged_all.zip 被占用则写入 merged_all_packed.zip。"""
    src = data_dir / folder_name
    primary = data_dir / f"{folder_name}.zip"
    alt = data_dir / f"{folder_name}_packed.zip"
    target = primary
    try:
        if primary.is_file():
            primary.unlink()
    except OSError:
        target = alt
        try:
            if alt.is_file():
                alt.unlink()
        except OSError:
            pass
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in src.rglob("*"):
            if path.is_file():
                arc = path.relative_to(data_dir).as_posix()
                zf.write(path, arc)
    if target != primary:
        print(
            f"提示: 无法覆盖 {primary.name}（可能被其它程序打开），已写入 {target.name}",
            flush=True,
        )
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="按全局 7 类合并子数据集并打包 zip")
    parser.add_argument("--dry-run", action="store_true", help="仅统计，不写入")
    parser.add_argument(
        "--preset",
        type=str,
        choices=("four", "full"),
        default="four",
        help="four=仅四源（默认）；full=原先 fire 拆分 + helmet1/2/3",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="输出目录名（位于 data/ 下）；默认 merged_four / merged_all 随 preset",
    )
    parser.add_argument("--clean", action="store_true", help="输出目录已存在则先删除")
    parser.add_argument("--no-zip", action="store_true", help="不生成 zip")
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="不合并，仅对已有输出目录打印标签统计",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="仅检查各子数据集标注是否与合并映射一致，不合并",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="跳过合并前标注检查",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="检查有错误时仍继续合并（不推荐）",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / "data"
    out_name = args.out or ("merged_four" if args.preset == "four" else "merged_all")
    out_dir = data_dir / out_name
    sources = sources_for_preset(args.preset)

    print(f"数据根目录: {data_dir}")
    print(f"preset={args.preset} 子源数={len(sources)}")
    print(f"输出目录: {out_dir}")
    print(f"dry_run={args.dry_run}")
    print()

    if args.stats_only:
        if not out_dir.is_dir():
            raise SystemExit(f"目录不存在: {out_dir}")
        print_label_stats(out_dir)
        return

    if args.validate_only:
        err, _wrn = validate_sources(data_dir, sources)
        raise SystemExit(1 if err else 0)

    if not args.no_validate:
        val_err, _val_warn = validate_sources(data_dir, sources)
        if val_err and not args.force:
            print(
                "\n标注检查未通过，已中止。请修正标签或映射后重试；"
                "若仍要合并可使用 --force（会丢失未映射类别框）。",
                flush=True,
            )
            raise SystemExit(1)
        if val_err and args.force:
            print("\n[警告] 使用 --force 继续合并，未映射类别将在合并时被静默丢弃。", flush=True)
        print()

    if not args.dry_run and args.clean:
        zip_path = data_dir / f"{out_name}.zip"
        if out_dir.is_dir():
            shutil.rmtree(out_dir)
            print(f"已删除旧输出目录: {out_dir}")
        if zip_path.is_file():
            try:
                zip_path.unlink()
                print(f"已删除旧压缩包: {zip_path}")
            except OSError:
                print(f"警告: 无法删除旧压缩包（占用中）: {zip_path}，打包时将尝试使用备用文件名", flush=True)
        print()

    total_img = 0
    total_lbl = 0
    for sp in SPLITS:
        print(f"=== {sp} ===")
        ni, nl = merge_one_split(data_dir, out_dir, sp, args.dry_run, sources)
        print(f"  图片: {ni}, 标签文件: {nl}")
        total_img += ni
        total_lbl += nl

    print()
    print(f"合计图片: {total_img}, 标签文件: {total_lbl}")

    if args.dry_run:
        print("(dry-run: 未创建文件)")
        return

    write_data_yaml(out_dir, args.preset)
    print(f"已写入: {out_dir / 'data.yaml'}")

    if not args.no_zip:
        zp = zip_merged_folder(data_dir, out_name)
        print(f"已压缩: {zp}")
    else:
        print("(已跳过 zip)")

    print_label_stats(out_dir)

    print()
    print("训练示例:")
    print(f"  yolo train data={out_dir / 'data.yaml'} ...")


if __name__ == "__main__":
    main()
