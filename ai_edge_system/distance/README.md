# Distance Evaluation Outputs

This folder contains the evaluation outputs for gas-cylinder detection and monocular distance estimation on the CylinDeRS dataset (default: `test` split).

The evaluation script is:

- `F:\mine\ai_edge_system\scripts\eval_cylinder_distance.py`

## What “Ground Truth Distance” Means Here

The CylinDeRS dataset does **not** provide measured distances.
So this evaluation uses **pseudo ground truth** derived from the **human-labeled YOLO boxes**:

- Image size: `640 x 640`
- Camera intrinsics (fixed): `f = 640 px`, `cx = 320`, `cy = 320`
- Real cylinder height (assumed): `H = 1.25 m`
- Depth formula (same as runtime module): `Z = (f * H) / pixel_height`

This pseudo-GT is:

- reproducible
- consistent with the code’s monocular geometry

But it is **not a physical measurement** and can deviate from real-world distances.

## How To Reproduce

Run from `F:\mine\ai_edge_system`:

```bash
python scripts/eval_cylinder_distance.py
```

Useful options:

```bash
# quick smoke test
python scripts/eval_cylinder_distance.py --limit 20

# change confidence / IoU thresholds
python scripts/eval_cylinder_distance.py --conf 0.25 --iou 0.5

# override dataset, weights, output
python scripts/eval_cylinder_distance.py ^
  --dataset F:\mine\ai_edge_system\data\gas_cylinder\CylinDeRS ^
  --split test ^
  --weights F:\mine\ai_edge_system\models\best.pt ^
  --out F:\mine\ai_edge_system\distance
```

## Outputs (Files)

- `metrics.json`
  - Overall summary: dataset counts, detection metrics, distance-error metrics, runtime, and all parameters used.

- `per_image_metrics.csv`
  - One row per image:
    - `gt_count`, `pred_count`
    - `tp`, `fp`, `fn` (object-level, after matching)
    - `predicted_at_least_one_cylinder`, `matched_at_least_one_cylinder`

- `object_matches.csv`
  - One row per object event:
    - `match_type` in `{TP, FP, FN}`
    - TP rows contain both GT and Pred info, with `iou`
    - FP rows only have Pred fields (GT fields are empty)
    - FN rows only have GT fields (Pred fields are empty)
  - Common columns:
    - `gt_*` / `pred_*` bounding box coords (`x1,y1,x2,y2`)
    - `pred_conf` (only for Pred)
    - `gt_depth_m` / `pred_depth_m` (monocular depth estimate)

- `pair_distance_errors.csv`
  - Pairwise distance evaluation **only for images with at least 2 correctly matched cylinders**.
  - Each row is one matched pair:
    - `gt_distance_m`, `pred_distance_m`
    - `error_m = pred - gt`
    - `abs_error_m`
    - `relative_error = error / gt`
    - `abs_relative_error`

- `report.html`
  - A human-readable report:
    - key KPIs
    - figures
    - pseudo-GT assumptions

- `figures/`
  - `detection_metric_overview.png`: precision/recall/F1 + image coverage
  - `detection_tp_fp_fn.png`: TP/FP/FN counts
  - `distance_gt_vs_pred.png`: GT vs Pred scatter (colored by abs error)
  - `distance_error_distribution.png`: abs error + abs percentage error histograms
  - `distance_error_by_range.png`: abs error vs GT distance

## Metrics Definitions (Quick)

Detection metrics (object-level):

- TP: predicted box matched to a GT box (greedy matching) with `IoU >= iou_threshold`
- FP: predicted box not matched to any GT box
- FN: GT box not matched by any prediction
- Precision: `TP / (TP + FP)`
- Recall: `TP / (TP + FN)`
- F1: harmonic mean of precision and recall
- Image coverage: fraction of images where there is at least one matched cylinder

Distance metrics (pairwise, matched cylinders only):

- MAE (m): mean absolute error of pair distances
- RMSE (m): root mean squared error
- Bias (m): mean signed error (pred - gt)
- P90/P95 AE (m): 90th/95th percentile of absolute error
- MAPE (%): mean absolute percentage error
- RME (%): root mean squared relative error (in percent)

## Notes / Caveats

- Small object box-height changes can cause large depth changes (because `Z ~ 1 / pixel_height`).
- Roboflow export applies `640x640 stretch`, which can distort geometry.
- Pseudo-GT is derived from labeled boxes, so distance results reflect consistency with labels and model boxes, not absolute physical distance accuracy.

