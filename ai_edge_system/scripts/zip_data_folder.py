"""
将 data/ 下某一数据集目录打包为 zip（Python zipfile 流式写入，适合大目录）。

- --manifest 在 data/ 下生成 <folder>_manifest.txt（相对 data/ 的路径，一行一个），
  上传服务器后可 wc -l 与本地对照。

用法:
  python scripts/zip_data_folder.py --folder final --manifest
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description="打包 data/ 下子目录为 zip")
    p.add_argument("--folder", type=str, required=True, help="data 下的目录名，如 final")
    p.add_argument(
        "--out",
        type=str,
        default=None,
        help="输出 zip 文件名（位于 data/ 下），默认 <folder>.zip",
    )
    p.add_argument(
        "--manifest",
        action="store_true",
        help="在 data/ 生成 <folder>_manifest.txt 文件清单",
    )
    args = p.parse_args()

    repo = Path(__file__).resolve().parent.parent
    data_dir = repo / "data"
    src = data_dir / args.folder
    if not src.is_dir():
        raise SystemExit(f"不存在: {src}")

    zip_name = args.out or f"{args.folder}.zip"
    out_path = data_dir / zip_name

    try:
        if out_path.is_file():
            out_path.unlink()
    except OSError as e:
        raise SystemExit(f"无法删除旧 zip: {out_path}\n{e}") from e

    manifest_lines: list[str] = []
    n_files = 0

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(src.rglob("*")):
            if not path.is_file():
                continue
            arc = path.relative_to(data_dir).as_posix()
            manifest_lines.append(arc)
            zf.write(path, arc)
            n_files += 1

    if args.manifest:
        man_path = data_dir / f"{args.folder}_manifest.txt"
        man_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
        print(f"清单: {man_path}  ({len(manifest_lines)} 行)")

    print(f"已写入: {out_path}")
    print(f"  包含文件数: {n_files}")


if __name__ == "__main__":
    main()
