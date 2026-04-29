"""统计各子数据集与 merged_ultralytics 的图片数、各类别框数。"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
GLOBAL = [
    "face",
    "fire",
    "smoke",
    "sparks",
    "gas_cylinder",
    "helmet",
    "no-helmet",
]


def count_images(img_dir: Path) -> int:
    if not img_dir.is_dir():
        return 0
    return sum(1 for f in img_dir.iterdir() if f.is_file() and f.suffix.lower() in IMG_EXT)


def count_boxes_raw(lbl_dir: Path) -> tuple[Counter, int, int]:
    """返回 (各类框数, 标签文件数, 框总数)"""
    c: Counter = Counter()
    n_files = 0
    if not lbl_dir.is_dir():
        return c, 0, 0
    for fp in lbl_dir.glob("*.txt"):
        n_files += 1
        for line in fp.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split()
            if not parts:
                continue
            try:
                c[int(parts[0])] += 1
            except ValueError:
                pass
    return c, n_files, sum(c.values())


def map_counts(raw: Counter, mapping: dict[int, int]) -> Counter:
    out: Counter = Counter()
    for k, v in raw.items():
        if k in mapping:
            out[mapping[k]] += v
    return out


MAPS = {
    "Face": {0: 0},
    "Fire/Smoke": {1: 1, 2: 2},
    "Spark": {0: 3, 1: 3, 2: 3, 3: 3},
    "CylinDeRS": {4: 4},
    "Construction": {5: 5, 6: 6, 7: 6},
    "Industry_safety": {0: 5, 1: 6, 5: 5, 6: 6, 7: 6},
    "Helmet3": {0: 6, 1: 5, 5: 5, 6: 6, 7: 6},
}

SOURCES = [
    ("Face", "face/Face detection with yolov8.v2i.yolov11"),
    ("Fire/Smoke", "fire/Fire and smoke detection.v2i.yolov11"),
    ("Spark", "fire/Spark.v2i.yolov11"),
    ("CylinDeRS", "gas_cylinder/CylinDeRS"),
    ("Construction", "helmet/Construction"),
    ("Industry_safety", "helmet/industry_safety.v2i.yolov11"),
    ("Helmet3", "helmet/helmet3"),
]

SPLITS = ("train", "valid", "test")


def main() -> None:
    print("=" * 72)
    print("一、各子数据集（原始类别 ID → 映射到项目 7 类）")
    print("=" * 72)

    sum_all_sources: Counter = Counter()

    for name, rel in SOURCES:
        m = MAPS[name]
        root = DATA / rel
        print(f"\n【{name}】 {rel}")
        tot_img = 0
        total_mapped: Counter = Counter()
        for sp in SPLITS:
            idir = root / sp / "images"
            ldir = root / sp / "labels"
            ni = count_images(idir)
            raw, n_lbl_files, n_boxes = count_boxes_raw(ldir)
            tot_img += ni
            mapped = map_counts(raw, m)
            for k, v in mapped.items():
                total_mapped[k] += v
            print(f"  {sp}: 图片 {ni} | 标签文件 {n_lbl_files} | 框(原始合计) {n_boxes}")
            if raw:
                rs = ", ".join(f"id{k}={raw[k]}" for k in sorted(raw))
                print(f"       原始类别框数: {rs}")
            if mapped:
                gs = ", ".join(f"{GLOBAL[k]}={mapped[k]}" for k in sorted(mapped))
                print(f"       → 全局 7 类: {gs}")
        gs_all = ", ".join(f"{GLOBAL[i]}={total_mapped[i]}" for i in range(len(GLOBAL)))
        tot_boxes_mapped = sum(total_mapped.values())
        print(f"  —— 图片合计 {tot_img} | 映射后框总数 {tot_boxes_mapped} | 按类: {gs_all}")
        for k, v in total_mapped.items():
            sum_all_sources[k] += v

    print("\n" + "-" * 72)
    print("各子集映射后框总数（用于与合成集对照）")
    print("-" * 72)
    for name, rel in SOURCES:
        m = MAPS[name]
        root = DATA / rel
        tm: Counter = Counter()
        for sp in SPLITS:
            raw, _, _ = count_boxes_raw(root / sp / "labels")
            for k, v in map_counts(raw, m).items():
                tm[k] += v
        print(f"  {name:18} 框数 {sum(tm.values()):6}  |  " + ", ".join(f"{GLOBAL[i]}={tm[i]}" for i in range(len(GLOBAL)) if tm[i]))

    print("\n" + "=" * 72)
    print("二、合成数据集 merged_ultralytics（已是全局 0–6）")
    print("=" * 72)
    merged = DATA / "merged_ultralytics"
    if not merged.is_dir():
        print(f"  不存在: {merged}")
        return

    grand_c: Counter = Counter()
    tot_im = 0
    for sp in SPLITS:
        idir = merged / sp / "images"
        ldir = merged / sp / "labels"
        ni = count_images(idir)
        tot_im += ni
        c, _, nb = count_boxes_raw(ldir)
        for k, v in c.items():
            grand_c[k] += v
        print(f"  {sp}: 图片 {ni} | 框总数 {nb}")
    print(f"\n  图片总计: {tot_im} | 框总计: {sum(grand_c.values())}")
    print("  各类别框数:")
    for i in range(len(GLOBAL)):
        print(f"    {i} {GLOBAL[i]}: {grand_c[i]}")

    print("\n" + "=" * 72)
    print("三、验证：子集映射后求和 vs 合成集")
    print("=" * 72)
    exp_total = sum(sum_all_sources.values())
    got_total = sum(grand_c.values())
    ok = True
    for i in range(len(GLOBAL)):
        a, b = sum_all_sources[i], grand_c[i]
        match = "OK" if a == b else "MISMATCH"
        if a != b:
            ok = False
        print(f"  {GLOBAL[i]:14} 子集合计 {a:6}  合成集 {b:6}  {match}")
    print(f"\n  框总数: 子集合计 {exp_total}  合成集 {got_total}  ", end="")
    if ok and exp_total == got_total:
        print("一致。")
    else:
        print("不一致（请检查合并脚本是否最新、或重新运行 merge）。")


if __name__ == "__main__":
    main()
