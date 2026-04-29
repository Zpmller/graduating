#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在 edge 层统一数据配置下，对训练好的 YOLO 权重分别在验证集(valid)与测试集(test)上评估。

数据路径由 ai_edge_system/data/data.yaml 中的 val / test 列表指定
（各子数据集下的 valid、test 文件夹）。

用法（在 ai_edge_system 目录下，激活 .venv 后）:
  python scripts/eval_valid_test.py
  python scripts/eval_valid_test.py --weights models/1.pt
  python scripts/eval_valid_test.py --data data/data.yaml --batch 8
  python scripts/eval_valid_test.py --weights models/1.pt --layout-stem
      # 输出写入 models/runs/1/val、models/runs/1/test 与 models/runs/1/eval_metrics.json
  （无 GPU 时默认 device=cpu；有 GPU 时默认 0，可用 --device 覆盖）

输出:
  - 控制台打印 mAP、Precision、Recall 等
  - 权重与训练产物均在 models/ 下；评估曲线默认写入 models/runs/（见 --project）
  - 使用 --layout-stem 时：在 models/runs/<与.pt同名>/ 下生成 val/、test/ 与 eval_metrics.json
  - 未使用 --layout-stem 时 JSON 默认 scripts/eval_runs/eval_metrics.json（可用 --save-json 改）
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch

# PyTorch 2.6+ 默认 torch.load(..., weights_only=True)，Ultralytics 的 .pt 含完整模型反序列化，需 False。
_orig_torch_load = torch.load


def _torch_load_allow_full_checkpoint(*args: Any, **kwargs: Any) -> Any:
    kwargs.setdefault("weights_only", False)
    return _orig_torch_load(*args, **kwargs)


torch.load = _torch_load_allow_full_checkpoint  # type: ignore[method-assign]

from ultralytics import YOLO


def _edge_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_runs_dir(edge: Path) -> Path:
    """评估结果根目录：ai_edge_system/models/runs/"""
    return edge / "models" / "runs"


def _default_eval_device() -> str:
    """有 CUDA 时用首张 GPU，否则 cpu（避免仅安装 torch CPU 版时默认 device=0 报错）。"""
    return "0" if torch.cuda.is_available() else "cpu"


def _to_jsonable(obj: Any) -> Any:
    """将 metrics / numpy 标量等转为可 JSON 序列化的类型。"""
    if obj is None:
        return None
    if hasattr(obj, "item"):
        try:
            return float(obj.item())
        except Exception:
            pass
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, (float, int, str, bool)):
        return obj
    try:
        return float(obj)
    except Exception:
        return str(obj)


def extract_metrics(metrics: Any) -> dict[str, Any]:
    """从 Ultralytics DetMetrics 提取扁平字典。"""
    out: dict[str, Any] = {}
    if hasattr(metrics, "results_dict") and metrics.results_dict:
        out.update(_to_jsonable(dict(metrics.results_dict)))
    # 补充 box 级别常用字段（不同版本可能已在 results_dict 中）
    if hasattr(metrics, "box") and metrics.box is not None:
        box = metrics.box
        for name in ("map50", "map75", "map", "maps"):
            if hasattr(box, name):
                out.setdefault(name, _to_jsonable(getattr(box, name)))
    return out


def run_split(
    model: YOLO,
    data_yaml: Path,
    split: str,
    *,
    imgsz: int,
    batch: int,
    device: str,
    conf: float,
    iou: float,
    plots: bool,
    project: Path,
    name: str,
    workers: int,
) -> Any:
    return model.val(
        data=str(data_yaml),
        split=split,
        imgsz=imgsz,
        batch=batch,
        device=device,
        conf=conf,
        iou=iou,
        plots=plots,
        project=str(project),
        name=name,
        exist_ok=True,
        verbose=True,
        workers=workers,
    )


def main() -> None:
    root = _edge_root()
    parser = argparse.ArgumentParser(description="YOLO 在 valid / test 上的评估脚本")
    parser.add_argument(
        "--weights",
        type=Path,
        default=root
        / "models"
        / "runs"
        / "mining_safety_v1"
        / "weights"
        / "best.pt",
        help="权重路径（.pt 放在 models/ 下任意位置），默认 models/runs/mining_safety_v1/weights/best.pt",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=root / "data" / "data.yaml",
        help="数据集 yaml（需含 val 与 test）",
    )
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="0 / cpu / 0,1；默认自动：有 CUDA 用 0，否则 cpu",
    )
    parser.add_argument("--conf", type=float, default=0.001, help="val 时常用较低 conf 以算全 mAP")
    parser.add_argument("--iou", type=float, default=0.5)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="不生成 PR/F1 等曲线图（默认会生成，写入 project/name-val、name-test）",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        help="Ultralytics 输出目录，默认 models/runs",
    )
    parser.add_argument("--name-val", type=str, default="eval_val", help="验证集评估 run 名称")
    parser.add_argument("--name-test", type=str, default="eval_test", help="测试集评估 run 名称")
    parser.add_argument(
        "--save-json",
        type=Path,
        default=root / "scripts" / "eval_runs" / "eval_metrics.json",
        help="将指标写入该 JSON（默认 scripts/eval_runs/eval_metrics.json）",
    )
    parser.add_argument("--no-save-json", action="store_true", help="不写入 JSON 文件")
    parser.add_argument(
        "--skip-val",
        action="store_true",
        help="跳过验证集，仅跑 test",
    )
    parser.add_argument(
        "--skip-test",
        action="store_true",
        help="跳过测试集，仅跑 val",
    )
    parser.add_argument(
        "--layout-stem",
        action="store_true",
        help="在 models/runs/<权重主文件名>/ 下输出：val/、test/ 与 eval_metrics.json（可用 --runs-root 改 runs 根目录）",
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=None,
        help="与 --layout-stem 配合，runs 根目录，默认 models/runs",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="自定义评估输出根目录（与 --layout-stem 二选一优先使用本项）：val/、test/、eval_metrics.json",
    )
    args = parser.parse_args()
    plots = not args.no_plots
    device = args.device if args.device is not None else _default_eval_device()

    if args.project is None:
        args.project = _default_runs_dir(root)

    weights = args.weights.resolve()
    data_yaml = args.data.resolve()
    if not weights.is_file():
        raise FileNotFoundError(f"未找到权重: {weights}")
    if not data_yaml.is_file():
        raise FileNotFoundError(f"未找到 data yaml: {data_yaml}")

    if args.output_dir is not None:
        out_root = args.output_dir.expanduser().resolve()
        out_root.mkdir(parents=True, exist_ok=True)
        args.project = out_root
        args.name_val = "val"
        args.name_test = "test"
        if not args.no_save_json:
            args.save_json = out_root / "eval_metrics.json"
    elif args.layout_stem:
        runs_root = (
            args.runs_root.expanduser().resolve()
            if args.runs_root is not None
            else _default_runs_dir(root)
        )
        runs_root.mkdir(parents=True, exist_ok=True)
        out_root = (runs_root / weights.stem).resolve()
        out_root.mkdir(parents=True, exist_ok=True)
        args.project = out_root
        args.name_val = "val"
        args.name_test = "test"
        if not args.no_save_json:
            args.save_json = out_root / "eval_metrics.json"

    print(f"权重: {weights}")
    print(f"数据: {data_yaml}")
    print(f"设备: {device}")
    model = YOLO(str(weights))

    report: dict[str, Any] = {"weights": str(weights), "data": str(data_yaml), "splits": {}}

    if not args.skip_val:
        print("\n>>> 正在评估验证集 (split=val) ...\n")
        m_val = run_split(
            model,
            data_yaml,
            "val",
            imgsz=args.imgsz,
            batch=args.batch,
            device=device,
            conf=args.conf,
            iou=args.iou,
            plots=plots,
            project=args.project,
            name=args.name_val,
            workers=args.workers,
        )
        report["splits"]["val"] = extract_metrics(m_val)
        print("\n[验证集] 主要指标:", json.dumps(report["splits"]["val"], ensure_ascii=False, indent=2))

    if not args.skip_test:
        print("\n>>> 正在评估测试集 (split=test) ...\n")
        m_test = run_split(
            model,
            data_yaml,
            "test",
            imgsz=args.imgsz,
            batch=args.batch,
            device=device,
            conf=args.conf,
            iou=args.iou,
            plots=plots,
            project=args.project,
            name=args.name_test,
            workers=args.workers,
        )
        report["splits"]["test"] = extract_metrics(m_test)
        print("\n[测试集] 主要指标:", json.dumps(report["splits"]["test"], ensure_ascii=False, indent=2))

    if not args.no_save_json:
        out_json = args.save_json.resolve()
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n已保存 JSON: {out_json}")

    if plots:
        written = []
        if not args.skip_val:
            written.append(args.name_val)
        if not args.skip_test:
            written.append(args.name_test)
        if written:
            proj = args.project.resolve()
            print("\n曲线与可视化目录:")
            for n in written:
                print(f"  {proj / n}")


if __name__ == "__main__":
    main()
