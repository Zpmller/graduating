#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evaluate gas-cylinder detection and monocular distance estimates.

The dataset has no measured distance labels, so this script derives a
reproducible pseudo ground truth from the human YOLO boxes using the same
single-view geometry used by the runtime distance module.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import shutil
import sys
import time
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _patch_torch_load() -> None:
    """Allow Ultralytics checkpoints saved as full model objects to load."""
    try:
        import torch
    except Exception:
        return

    if getattr(torch.load, "_allow_full_checkpoint_patch", False):
        return

    original_load = torch.load

    def patched_load(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("weights_only", False)
        try:
            return original_load(*args, **kwargs)
        except TypeError:
            kwargs.pop("weights_only", None)
            return original_load(*args, **kwargs)

    patched_load._allow_full_checkpoint_patch = True  # type: ignore[attr-defined]
    torch.load = patched_load  # type: ignore[method-assign]


_patch_torch_load()

from src.core.detector import Detector
from src.logic.distance import DistanceEstimator


CYLINDER_CLASS_ID = 4
CYLINDER_CLASS_NAME = "gas_cylinder"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass
class FixedCamera:
    focal_length_x: float = 640.0
    focal_length_y: float = 640.0
    cx: float = 320.0
    cy: float = 320.0


@dataclass
class CylinderObject:
    index: int
    box: list[float]
    depth_m: float | None
    point3d: tuple[float, float, float] | None
    conf: float | None = None


@dataclass
class ImageContext:
    image_path: Path
    gt_objects: list[CylinderObject]
    pred_objects: list[CylinderObject]
    matches: list[tuple[int, int, float]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate gas-cylinder detection and monocular distance."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "data" / "gas_cylinder" / "CylinDeRS",
        help="CylinDeRS dataset root.",
    )
    parser.add_argument("--split", type=str, default="test", help="Dataset split.")
    parser.add_argument(
        "--weights",
        type=Path,
        default=ROOT / "models" / "best.pt",
        help="YOLO .pt weights.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "distance",
        help="Output directory.",
    )
    parser.add_argument("--conf", type=float, default=0.25, help="YOLO confidence.")
    parser.add_argument(
        "--iou",
        type=float,
        default=0.5,
        help="IoU threshold for TP/FP/FN matching.",
    )
    parser.add_argument(
        "--height-m",
        type=float,
        default=1.25,
        help="Assumed real gas-cylinder height in meters.",
    )
    parser.add_argument("--focal", type=float, default=640.0, help="fx/fy in pixels.")
    parser.add_argument("--cx", type=float, default=320.0, help="Camera cx in pixels.")
    parser.add_argument("--cy", type=float, default=320.0, help="Camera cy in pixels.")
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help="Inference device: auto, cpu, 0, 0,1, etc.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of images for smoke tests.",
    )
    parser.add_argument(
        "--top-examples",
        type=int,
        default=6,
        help="Number of high-error examples to draw.",
    )
    return parser.parse_args()


def choose_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import torch

        return "0" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def list_images(images_dir: Path, limit: int | None) -> list[Path]:
    images = sorted(
        p for p in images_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )
    if limit is not None:
        images = images[: max(0, limit)]
    return images


def yolo_to_xyxy(parts: list[str], width: int, height: int) -> list[float]:
    x_center = float(parts[1]) * width
    y_center = float(parts[2]) * height
    box_w = float(parts[3]) * width
    box_h = float(parts[4]) * height
    x1 = max(0.0, x_center - box_w / 2.0)
    y1 = max(0.0, y_center - box_h / 2.0)
    x2 = min(float(width), x_center + box_w / 2.0)
    y2 = min(float(height), y_center + box_h / 2.0)
    return [x1, y1, x2, y2]


def read_gt_boxes(label_path: Path, width: int, height: int) -> list[list[float]]:
    if not label_path.exists():
        return []

    boxes: list[list[float]] = []
    for line in label_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        try:
            class_id = int(float(parts[0]))
        except ValueError:
            continue
        if class_id != CYLINDER_CLASS_ID:
            continue
        boxes.append(yolo_to_xyxy(parts, width, height))
    return boxes


def make_estimator(args: argparse.Namespace) -> DistanceEstimator:
    camera = FixedCamera(
        focal_length_x=float(args.focal),
        focal_length_y=float(args.focal),
        cx=float(args.cx),
        cy=float(args.cy),
    )
    estimator = DistanceEstimator(camera)
    estimator.REAL_HEIGHTS[CYLINDER_CLASS_NAME] = float(args.height_m) * 100.0
    return estimator


def enrich_objects(
    boxes: list[list[float]],
    estimator: DistanceEstimator,
    confs: list[float] | None = None,
) -> list[CylinderObject]:
    objects: list[CylinderObject] = []
    confs = confs or [None] * len(boxes)  # type: ignore[list-item]
    for idx, (box, conf) in enumerate(zip(boxes, confs)):
        det = {"box": box, "class_name": CYLINDER_CLASS_NAME}
        depth = estimator.estimate_depth(box, CYLINDER_CLASS_NAME)
        point = estimator.get_3d_coordinates(box, depth) if depth is not None else None
        objects.append(CylinderObject(idx, box, depth, point, conf))
    return objects


def box_iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def greedy_match(
    gt_objects: list[CylinderObject],
    pred_objects: list[CylinderObject],
    iou_threshold: float,
) -> list[tuple[int, int, float]]:
    candidates: list[tuple[float, int, int]] = []
    for gt in gt_objects:
        for pred in pred_objects:
            iou = box_iou(gt.box, pred.box)
            if iou >= iou_threshold:
                candidates.append((iou, gt.index, pred.index))

    matches: list[tuple[int, int, float]] = []
    used_gt: set[int] = set()
    used_pred: set[int] = set()
    for iou, gt_idx, pred_idx in sorted(candidates, reverse=True):
        if gt_idx in used_gt or pred_idx in used_pred:
            continue
        used_gt.add(gt_idx)
        used_pred.add(pred_idx)
        matches.append((gt_idx, pred_idx, iou))
    return matches


def point_distance(a: tuple[float, float, float] | None, b: tuple[float, float, float] | None) -> float | None:
    if a is None or b is None:
        return None
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def finite_or_none(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (np.floating, np.integer)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def summarize_detection(tp: int, fp: int, fn: int, per_image_df: pd.DataFrame) -> dict[str, Any]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    images_with_gt = int((per_image_df["gt_count"] > 0).sum())
    images_matched_one = int(per_image_df["matched_at_least_one_cylinder"].sum())
    images_pred_one = int(per_image_df["predicted_at_least_one_cylinder"].sum())
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "images_with_gt": images_with_gt,
        "images_with_at_least_one_matched_cylinder": images_matched_one,
        "image_match_coverage": images_matched_one / images_with_gt if images_with_gt else 0.0,
        "images_with_at_least_one_predicted_cylinder": images_pred_one,
        "image_prediction_coverage": images_pred_one / len(per_image_df) if len(per_image_df) else 0.0,
    }


def summarize_distance(pair_df: pd.DataFrame) -> dict[str, Any]:
    if pair_df.empty:
        return {
            "pair_count": 0,
            "image_count": 0,
            "mae_m": None,
            "rmse_m": None,
            "median_ae_m": None,
            "bias_m": None,
            "p90_ae_m": None,
            "p95_ae_m": None,
            "rme_percent": None,
            "mape_percent": None,
        }

    err = pair_df["error_m"].to_numpy(dtype=float)
    ae = pair_df["abs_error_m"].to_numpy(dtype=float)
    rel = pair_df["relative_error"].to_numpy(dtype=float)
    return {
        "pair_count": int(len(pair_df)),
        "image_count": int(pair_df["image"].nunique()),
        "mae_m": float(np.mean(ae)),
        "rmse_m": float(np.sqrt(np.mean(err**2))),
        "median_ae_m": float(np.median(ae)),
        "bias_m": float(np.mean(err)),
        "p90_ae_m": float(np.percentile(ae, 90)),
        "p95_ae_m": float(np.percentile(ae, 95)),
        "rme_percent": float(np.sqrt(np.mean(rel**2)) * 100.0),
        "mape_percent": float(np.mean(np.abs(rel)) * 100.0),
    }


def save_json(path: Path, payload: dict[str, Any]) -> None:
    def sanitize(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {str(k): sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [sanitize(v) for v in obj]
        return finite_or_none(obj)

    path.write_text(json.dumps(sanitize(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def setup_plot_style() -> None:
    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except Exception:
        plt.style.use("ggplot")
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 180,
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.labelsize": 10,
            "axes.titleweight": "bold",
            "axes.edgecolor": "#D0D7DE",
            "axes.linewidth": 0.8,
            "grid.color": "#E6EAF0",
            "grid.linewidth": 0.7,
            "legend.frameon": True,
            "legend.framealpha": 0.92,
        }
    )


def add_value_labels(ax: plt.Axes, fmt: str = "{:.3f}") -> None:
    for patch in ax.patches:
        value = patch.get_height()
        if not math.isfinite(value):
            continue
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            value,
            fmt.format(value),
            ha="center",
            va="bottom",
            fontsize=9,
            color="#24292F",
        )


def plot_detection_overview(figures_dir: Path, detection: dict[str, Any]) -> Path:
    path = figures_dir / "detection_metric_overview.png"
    labels = ["Precision", "Recall", "F1", "Image coverage"]
    values = [
        detection["precision"],
        detection["recall"],
        detection["f1"],
        detection["image_match_coverage"],
    ]
    colors = ["#2563EB", "#059669", "#7C3AED", "#EA580C"]
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    bars = ax.bar(labels, values, color=colors, width=0.62)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Score")
    ax.set_title("Detection quality summary")
    ax.bar_label(bars, labels=[f"{v:.3f}" for v in values], padding=4, fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_confusion_counts(figures_dir: Path, detection: dict[str, Any]) -> Path:
    path = figures_dir / "detection_tp_fp_fn.png"
    labels = ["TP", "FP", "FN"]
    values = [detection["tp"], detection["fp"], detection["fn"]]
    colors = ["#16A34A", "#DC2626", "#F59E0B"]
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    bars = ax.bar(labels, values, color=colors, width=0.58)
    ax.set_ylabel("Object count")
    ax.set_title("Matched detections and errors")
    ax.bar_label(bars, labels=[str(v) for v in values], padding=4, fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_gt_pred_scatter(figures_dir: Path, pair_df: pd.DataFrame) -> Path | None:
    if pair_df.empty:
        return None
    path = figures_dir / "distance_gt_vs_pred.png"
    gt = pair_df["gt_distance_m"].to_numpy(dtype=float)
    pred = pair_df["pred_distance_m"].to_numpy(dtype=float)
    lim_min = max(0.0, min(float(gt.min()), float(pred.min())) * 0.95)
    lim_max = max(float(gt.max()), float(pred.max())) * 1.05
    fig, ax = plt.subplots(figsize=(6.5, 6.0))
    sc = ax.scatter(
        gt,
        pred,
        c=np.abs(pred - gt),
        cmap="viridis",
        s=26,
        alpha=0.72,
        edgecolors="white",
        linewidths=0.25,
    )
    ax.plot([lim_min, lim_max], [lim_min, lim_max], color="#111827", linewidth=1.2, label="Ideal")
    ax.set_xlim(lim_min, lim_max)
    ax.set_ylim(lim_min, lim_max)
    ax.set_xlabel("Pseudo-GT pair distance (m)")
    ax.set_ylabel("Detected pair distance (m)")
    ax.set_title("Pair distance: pseudo-GT vs detected")
    cb = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("Absolute error (m)")
    ax.legend(loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_error_distributions(figures_dir: Path, pair_df: pd.DataFrame) -> Path | None:
    if pair_df.empty:
        return None
    path = figures_dir / "distance_error_distribution.png"
    ae = pair_df["abs_error_m"].to_numpy(dtype=float)
    ape = pair_df["abs_relative_error"].to_numpy(dtype=float) * 100.0
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
    axes[0].hist(ae, bins=32, color="#2563EB", alpha=0.86, edgecolor="white")
    axes[0].axvline(np.median(ae), color="#DC2626", linestyle="--", linewidth=1.4, label="Median")
    axes[0].set_title("Absolute error")
    axes[0].set_xlabel("Meters")
    axes[0].set_ylabel("Pair count")
    axes[0].legend()
    axes[1].hist(ape, bins=32, color="#059669", alpha=0.86, edgecolor="white")
    axes[1].axvline(np.median(ape), color="#DC2626", linestyle="--", linewidth=1.4, label="Median")
    axes[1].set_title("Absolute percentage error")
    axes[1].set_xlabel("Percent")
    axes[1].set_ylabel("Pair count")
    axes[1].legend()
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_error_by_distance(figures_dir: Path, pair_df: pd.DataFrame) -> Path | None:
    if pair_df.empty:
        return None
    path = figures_dir / "distance_error_by_range.png"
    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    ax.scatter(
        pair_df["gt_distance_m"],
        pair_df["abs_error_m"],
        c=pair_df["abs_relative_error"] * 100.0,
        cmap="magma",
        s=22,
        alpha=0.68,
        edgecolors="white",
        linewidths=0.2,
    )
    ax.set_xlabel("Pseudo-GT pair distance (m)")
    ax.set_ylabel("Absolute error (m)")
    ax.set_title("Error across distance range")
    cb = fig.colorbar(ax.collections[0], ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("Absolute percentage error")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def draw_box(
    image: np.ndarray,
    box: list[float],
    color: tuple[int, int, int],
    label: str | None = None,
    thickness: int = 2,
) -> None:
    h, w = image.shape[:2]
    x1, y1, x2, y2 = [int(round(v)) for v in box]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w - 1, x2), min(h - 1, y2)
    cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
    if not label:
        return
    (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    y_text = max(th + baseline + 3, y1)
    cv2.rectangle(image, (x1, y_text - th - baseline - 4), (x1 + tw + 5, y_text + 2), color, -1)
    cv2.putText(
        image,
        label,
        (x1 + 3, y_text - baseline - 1),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )


def plot_top_error_examples(
    figures_dir: Path,
    pair_df: pd.DataFrame,
    contexts: dict[str, ImageContext],
    top_n: int,
) -> Path | None:
    if pair_df.empty or top_n <= 0:
        return None
    selected = (
        pair_df.sort_values("abs_error_m", ascending=False)
        .drop_duplicates(subset=["image"], keep="first")
        .head(top_n)
    )
    if selected.empty:
        return None

    annotated: list[tuple[np.ndarray, str]] = []
    for _, row in selected.iterrows():
        ctx = contexts.get(str(row["image"]))
        if ctx is None:
            continue
        image = cv2.imread(str(ctx.image_path))
        if image is None:
            continue
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        for gt in ctx.gt_objects:
            draw_box(image, gt.box, (120, 190, 145), None, thickness=1)
        for pred in ctx.pred_objects:
            draw_box(image, pred.box, (130, 170, 240), None, thickness=1)

        highlighted_gt = [int(row["gt_index_a"]), int(row["gt_index_b"])]
        highlighted_pred = [int(row["pred_index_a"]), int(row["pred_index_b"])]
        for label, gt_idx in zip(("GT A", "GT B"), highlighted_gt):
            if 0 <= gt_idx < len(ctx.gt_objects):
                draw_box(image, ctx.gt_objects[gt_idx].box, (234, 88, 12), label, thickness=3)
        for label, pred_idx in zip(("Pred A", "Pred B"), highlighted_pred):
            if 0 <= pred_idx < len(ctx.pred_objects):
                conf = ctx.pred_objects[pred_idx].conf
                suffix = "" if conf is None else f" {conf:.2f}"
                draw_box(
                    image,
                    ctx.pred_objects[pred_idx].box,
                    (37, 99, 235),
                    f"{label}{suffix}",
                    thickness=3,
                )
        title = (
            f"{ctx.image_path.name}\n"
            f"GT {row['gt_distance_m']:.2f}m | Pred {row['pred_distance_m']:.2f}m | "
            f"AE {row['abs_error_m']:.2f}m"
        )
        annotated.append((image, title))

    if not annotated:
        return None

    cols = min(3, len(annotated))
    rows = math.ceil(len(annotated) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 5.2, rows * 4.7))
    axes_arr = np.array(axes, dtype=object).reshape(-1)
    for ax, (image, title) in zip(axes_arr, annotated):
        ax.imshow(image)
        ax.set_title(title, fontsize=9)
        ax.axis("off")
    for ax in axes_arr[len(annotated) :]:
        ax.axis("off")
    fig.suptitle("Highest pair-distance errors", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    path = figures_dir / "top_error_examples.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def generate_figures(
    out_dir: Path,
    detection: dict[str, Any],
    pair_df: pd.DataFrame,
    contexts: dict[str, ImageContext],
    top_examples: int,
) -> list[Path]:
    figures_dir = out_dir / "figures"
    if figures_dir.exists():
        shutil.rmtree(figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)
    setup_plot_style()

    paths: list[Path | None] = [
        plot_detection_overview(figures_dir, detection),
        plot_confusion_counts(figures_dir, detection),
        plot_gt_pred_scatter(figures_dir, pair_df),
        plot_error_distributions(figures_dir, pair_df),
        plot_error_by_distance(figures_dir, pair_df),
        plot_top_error_examples(figures_dir, pair_df, contexts, top_examples),
    ]
    return [p for p in paths if p is not None]


def fmt_metric(value: Any, digits: int = 3) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return html.escape(str(value))


def metric_table(metrics: dict[str, Any], keys: list[tuple[str, str]]) -> str:
    rows = []
    for key, label in keys:
        rows.append(
            "<tr>"
            f"<th>{html.escape(label)}</th>"
            f"<td>{html.escape(fmt_metric(metrics.get(key)))}</td>"
            "</tr>"
        )
    return "<table>" + "".join(rows) + "</table>"


def generate_report(
    out_dir: Path,
    metrics: dict[str, Any],
    figure_paths: list[Path],
) -> None:
    detection = metrics["detection"]
    distance = metrics["distance_errors"]
    dataset = metrics["dataset"]
    params = metrics["parameters"]

    figures_html = "\n".join(
        f'<figure><img src="{html.escape(str(path.relative_to(out_dir)).replace(chr(92), "/"))}" '
        f'alt="{html.escape(path.stem)}"><figcaption>{html.escape(path.stem.replace("_", " ").title())}</figcaption></figure>'
        for path in figure_paths
    )

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gas Cylinder Distance Evaluation</title>
  <style>
    :root {{
      --bg: #f6f8fb;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #5b6472;
      --line: #dbe2ea;
      --blue: #2563eb;
      --green: #059669;
      --orange: #ea580c;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Segoe UI", Arial, sans-serif;
      line-height: 1.55;
    }}
    header {{
      padding: 34px 44px 26px;
      color: white;
      background: linear-gradient(135deg, #1f2937, #2563eb 58%, #059669);
    }}
    header h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      letter-spacing: 0;
    }}
    header p {{ margin: 0; max-width: 980px; opacity: 0.94; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 26px; }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
      margin: 18px 0;
      box-shadow: 0 12px 26px rgba(15, 23, 42, 0.06);
    }}
    h2 {{ margin: 0 0 14px; font-size: 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; }}
    .kpi {{
      border-left: 4px solid var(--blue);
      background: #f8fbff;
      padding: 14px 16px;
      border-radius: 6px;
    }}
    .kpi strong {{ display: block; font-size: 25px; margin-bottom: 2px; }}
    .kpi span {{ color: var(--muted); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 9px 10px; border-bottom: 1px solid var(--line); text-align: left; }}
    th {{ width: 56%; color: var(--muted); font-weight: 600; }}
    figure {{ margin: 0 0 22px; }}
    img {{ max-width: 100%; border: 1px solid var(--line); border-radius: 7px; background: white; }}
    figcaption {{ color: var(--muted); font-size: 13px; margin-top: 6px; }}
    code {{ background: #eef2f7; border-radius: 4px; padding: 2px 5px; }}
    .note {{ color: var(--muted); }}
  </style>
</head>
<body>
<header>
  <h1>Gas Cylinder Detection and Distance Evaluation</h1>
  <p>Evaluation results for YOLO gas-cylinder detection and monocular pair-distance estimates.</p>
</header>
<main>
  <section>
    <h2>Summary</h2>
    <div class="grid">
      <div class="kpi"><strong>{fmt_metric(detection["precision"])}</strong><span>Precision</span></div>
      <div class="kpi"><strong>{fmt_metric(detection["recall"])}</strong><span>Recall</span></div>
      <div class="kpi"><strong>{fmt_metric(detection["f1"])}</strong><span>F1</span></div>
      <div class="kpi"><strong>{fmt_metric(distance["mae_m"])} m</strong><span>Pair-distance MAE</span></div>
    </div>
  </section>
  <section>
    <h2>Dataset and Parameters</h2>
    {metric_table(dataset, [
        ("evaluated_images", "Evaluated images"),
        ("gt_cylinders", "GT cylinders"),
        ("images_with_at_least_two_gt_cylinders", "Images with >=2 GT cylinders"),
    ])}
    <p class="note">Pseudo-GT is derived from human boxes with
      <code>height_m={html.escape(str(params["height_m"]))}</code>,
      <code>f={html.escape(str(params["focal"]))}</code>,
      <code>cx={html.escape(str(params["cx"]))}</code>,
      <code>cy={html.escape(str(params["cy"]))}</code>.
      It is reproducible but is not a measured physical distance.</p>
  </section>
  <section>
    <h2>Detection Metrics</h2>
    {metric_table(detection, [
        ("tp", "True positives"),
        ("fp", "False positives"),
        ("fn", "False negatives"),
        ("precision", "Precision"),
        ("recall", "Recall"),
        ("f1", "F1"),
        ("image_match_coverage", "Image coverage, >=1 matched cylinder"),
        ("image_prediction_coverage", "Image coverage, >=1 predicted cylinder"),
    ])}
  </section>
  <section>
    <h2>Distance Error Metrics</h2>
    {metric_table(distance, [
        ("pair_count", "Matched cylinder pairs"),
        ("image_count", "Images contributing pairs"),
        ("mae_m", "MAE (m)"),
        ("rmse_m", "RMSE (m)"),
        ("median_ae_m", "Median AE (m)"),
        ("bias_m", "Bias (m)"),
        ("p90_ae_m", "P90 AE (m)"),
        ("p95_ae_m", "P95 AE (m)"),
        ("rme_percent", "RME, root relative (%)"),
        ("mape_percent", "MAPE (%)"),
    ])}
  </section>
  <section>
    <h2>Figures</h2>
    {figures_html}
  </section>
</main>
</body>
</html>
"""
    (out_dir / "report.html").write_text(html_text, encoding="utf-8")


def run_evaluation(args: argparse.Namespace) -> dict[str, Any]:
    dataset = args.dataset.resolve()
    images_dir = dataset / args.split / "images"
    labels_dir = dataset / args.split / "labels"
    out_dir = args.out.resolve()
    weights = args.weights.resolve()

    if not images_dir.is_dir():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    if not labels_dir.is_dir():
        raise FileNotFoundError(f"Labels directory not found: {labels_dir}")
    if not weights.is_file():
        raise FileNotFoundError(f"Weights file not found: {weights}")

    out_dir.mkdir(parents=True, exist_ok=True)
    images = list_images(images_dir, args.limit)
    if not images:
        raise RuntimeError(f"No images found in {images_dir}")

    device = choose_device(args.device)
    print(f"Dataset: {dataset}")
    print(f"Split: {args.split}, images: {len(images)}")
    print(f"Weights: {weights}")
    print(f"Device: {device}")

    estimator = make_estimator(args)
    detector = Detector(model_path=str(weights), device=device)

    per_image_records: list[dict[str, Any]] = []
    object_records: list[dict[str, Any]] = []
    pair_records: list[dict[str, Any]] = []
    contexts: dict[str, ImageContext] = {}

    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_gt = 0
    total_pred = 0
    gt_images_ge2 = 0
    started = time.time()

    for image_idx, image_path in enumerate(images, start=1):
        frame = cv2.imread(str(image_path))
        if frame is None:
            print(f"Warning: failed to read image: {image_path}")
            continue
        height, width = frame.shape[:2]
        label_path = labels_dir / f"{image_path.stem}.txt"
        gt_boxes = read_gt_boxes(label_path, width, height)
        gt_objects = enrich_objects(gt_boxes, estimator)

        results = detector.detect(frame, conf_threshold=float(args.conf), classes=[CYLINDER_CLASS_ID])
        detections = detector.get_detections_list(results)
        pred_boxes = [list(map(float, det["box"])) for det in detections]
        pred_confs = [float(det["conf"]) for det in detections]
        pred_objects = enrich_objects(pred_boxes, estimator, pred_confs)

        matches = greedy_match(gt_objects, pred_objects, float(args.iou))
        matched_gt = {gt_idx for gt_idx, _, _ in matches}
        matched_pred = {pred_idx for _, pred_idx, _ in matches}
        tp = len(matches)
        fp = len(pred_objects) - len(matched_pred)
        fn = len(gt_objects) - len(matched_gt)

        total_tp += tp
        total_fp += fp
        total_fn += fn
        total_gt += len(gt_objects)
        total_pred += len(pred_objects)
        if len(gt_objects) >= 2:
            gt_images_ge2 += 1

        per_image_records.append(
            {
                "image": image_path.name,
                "image_path": str(image_path),
                "gt_count": len(gt_objects),
                "pred_count": len(pred_objects),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "predicted_at_least_one_cylinder": len(pred_objects) > 0,
                "matched_at_least_one_cylinder": tp > 0,
            }
        )

        for gt_idx, pred_idx, iou in matches:
            gt = gt_objects[gt_idx]
            pred = pred_objects[pred_idx]
            object_records.append(
                object_record(image_path.name, "TP", gt=gt, pred=pred, iou=iou)
            )

        for gt in gt_objects:
            if gt.index not in matched_gt:
                object_records.append(object_record(image_path.name, "FN", gt=gt))

        for pred in pred_objects:
            if pred.index not in matched_pred:
                object_records.append(object_record(image_path.name, "FP", pred=pred))

        match_lookup = {gt_idx: pred_idx for gt_idx, pred_idx, _ in matches}
        if len(match_lookup) >= 2:
            for gt_a, gt_b in combinations(sorted(match_lookup.keys()), 2):
                pred_a = match_lookup[gt_a]
                pred_b = match_lookup[gt_b]
                gt_dist = point_distance(gt_objects[gt_a].point3d, gt_objects[gt_b].point3d)
                pred_dist = point_distance(pred_objects[pred_a].point3d, pred_objects[pred_b].point3d)
                if gt_dist is None or pred_dist is None or gt_dist <= 1e-9:
                    continue
                error = pred_dist - gt_dist
                pair_records.append(
                    {
                        "image": image_path.name,
                        "image_path": str(image_path),
                        "gt_index_a": gt_a,
                        "gt_index_b": gt_b,
                        "pred_index_a": pred_a,
                        "pred_index_b": pred_b,
                        "gt_distance_m": gt_dist,
                        "pred_distance_m": pred_dist,
                        "error_m": error,
                        "abs_error_m": abs(error),
                        "relative_error": error / gt_dist,
                        "abs_relative_error": abs(error) / gt_dist,
                    }
                )

        contexts[image_path.name] = ImageContext(image_path, gt_objects, pred_objects, matches)

        if image_idx == 1 or image_idx % 50 == 0 or image_idx == len(images):
            elapsed = time.time() - started
            print(f"[{image_idx}/{len(images)}] processed, elapsed {elapsed:.1f}s")

    per_image_df = pd.DataFrame(per_image_records)
    object_df = pd.DataFrame(object_records)
    pair_df = pd.DataFrame(pair_records)

    detection_summary = summarize_detection(total_tp, total_fp, total_fn, per_image_df)
    distance_summary = summarize_distance(pair_df)
    metrics = {
        "parameters": {
            "dataset": str(dataset),
            "split": args.split,
            "weights": str(weights),
            "output_dir": str(out_dir),
            "conf": float(args.conf),
            "iou": float(args.iou),
            "height_m": float(args.height_m),
            "focal": float(args.focal),
            "cx": float(args.cx),
            "cy": float(args.cy),
            "device": device,
            "limit": args.limit,
            "class_id": CYLINDER_CLASS_ID,
            "class_name": CYLINDER_CLASS_NAME,
        },
        "dataset": {
            "evaluated_images": int(len(per_image_df)),
            "gt_cylinders": int(total_gt),
            "predicted_cylinders": int(total_pred),
            "images_with_at_least_two_gt_cylinders": int(gt_images_ge2),
        },
        "detection": detection_summary,
        "distance_errors": distance_summary,
        "runtime_seconds": float(time.time() - started),
    }

    per_image_df.to_csv(out_dir / "per_image_metrics.csv", index=False, encoding="utf-8-sig")
    object_df.to_csv(out_dir / "object_matches.csv", index=False, encoding="utf-8-sig")
    pair_df.to_csv(out_dir / "pair_distance_errors.csv", index=False, encoding="utf-8-sig")
    save_json(out_dir / "metrics.json", metrics)
    figure_paths = generate_figures(out_dir, detection_summary, pair_df, contexts, args.top_examples)
    generate_report(out_dir, metrics, figure_paths)
    return metrics


def object_record(
    image_name: str,
    match_type: str,
    gt: CylinderObject | None = None,
    pred: CylinderObject | None = None,
    iou: float | None = None,
) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "image": image_name,
        "match_type": match_type,
        "iou": iou,
        "gt_index": gt.index if gt is not None else None,
        "pred_index": pred.index if pred is not None else None,
        "pred_conf": pred.conf if pred is not None else None,
        "gt_depth_m": gt.depth_m if gt is not None else None,
        "pred_depth_m": pred.depth_m if pred is not None else None,
    }
    for prefix, obj in (("gt", gt), ("pred", pred)):
        box = obj.box if obj is not None else [None, None, None, None]
        rec[f"{prefix}_x1"] = box[0]
        rec[f"{prefix}_y1"] = box[1]
        rec[f"{prefix}_x2"] = box[2]
        rec[f"{prefix}_y2"] = box[3]
    return rec


def main() -> None:
    args = parse_args()
    metrics = run_evaluation(args)
    out_dir = args.out.resolve()
    print("\nDone.")
    print(f"Metrics: {out_dir / 'metrics.json'}")
    print(f"Report:  {out_dir / 'report.html'}")
    print(
        "Detection: "
        f"P={metrics['detection']['precision']:.3f}, "
        f"R={metrics['detection']['recall']:.3f}, "
        f"F1={metrics['detection']['f1']:.3f}"
    )
    if metrics["distance_errors"]["pair_count"]:
        print(
            "Distance: "
            f"MAE={metrics['distance_errors']['mae_m']:.3f}m, "
            f"RMSE={metrics['distance_errors']['rmse_m']:.3f}m, "
            f"MAPE={metrics['distance_errors']['mape_percent']:.2f}%"
        )
    else:
        print("Distance: no matched cylinder pairs were available.")


if __name__ == "__main__":
    main()
