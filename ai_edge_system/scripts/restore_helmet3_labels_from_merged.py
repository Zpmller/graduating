"""从 data/merged_all 中 helmet3__* 标签恢复 helmet3 目录（并转为 7 类：删 person、no-helmet 7->6）。"""
from __future__ import annotations

from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
MERGED = DATA / "merged_all"
H3 = DATA / "helmet" / "helmet3"
PREFIX = "helmet3__"
SPLITS = ("train", "valid", "test")
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def merged_helmet3_map() -> dict[str, str]:
    m: dict[str, str] = {}
    for sp in SPLITS:
        ld = MERGED / sp / "labels"
        if not ld.is_dir():
            continue
        for lf in ld.glob(f"{PREFIX}*.txt"):
            stem = lf.stem[len(PREFIX) :]
            m[stem] = lf.read_text(encoding="utf-8", errors="ignore")
    return m


def to_7_class(text: str) -> str:
    out: list[str] = []
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) != 5:
            continue
        try:
            c = int(parts[0])
        except ValueError:
            continue
        if c == 6:
            continue
        if c == 7:
            parts[0] = "6"
        out.append(" ".join(parts) + "\n")
    return "".join(out)


def main() -> None:
    if not MERGED.is_dir():
        raise SystemExit(f"缺少 {MERGED}")
    m = merged_helmet3_map()
    print(f"从 merged_all 收集 helmet3 标签: {len(m)} 个 stem")
    n = 0
    for sp in SPLITS:
        img_dir = H3 / sp / "images"
        lbl_dir = H3 / sp / "labels"
        if not img_dir.is_dir():
            continue
        lbl_dir.mkdir(parents=True, exist_ok=True)
        for img in sorted(img_dir.iterdir()):
            if not img.is_file() or img.suffix.lower() not in IMG_EXT:
                continue
            stem = img.stem
            raw = m.get(stem, "")
            body = to_7_class(raw)
            (lbl_dir / f"{stem}.txt").write_text(body, encoding="utf-8")
            n += 1
    print(f"已写回 helmet3 各 split 共 {n} 个标签文件（7 类）")


if __name__ == "__main__":
    main()
