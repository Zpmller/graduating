import os
import glob
import argparse


def remap_labels(label_dir, mapping, output_dir=None):
    """
    Remaps YOLO label indices in text files.

    Args:
        label_dir (str): Directory containing .txt label files.
        mapping (dict): Dictionary mapping old_id (int) to new_id (int).
        output_dir (str, optional): Directory to save modified files. If None, overwrites originals.
    """
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    txt_files = glob.glob(os.path.join(label_dir, "*.txt"))
    print(f"Found {len(txt_files)} label files in {label_dir}")

    count = 0
    empty_count = 0
    for txt_file in txt_files:
        with open(txt_file, "r") as f:
            lines = f.readlines()

        new_lines = []
        modified = False

        for line in lines:
            parts = line.strip().split()
            if not parts:
                continue

            try:
                class_id = int(parts[0])

                if class_id in mapping:
                    new_class_id = mapping[class_id]
                    parts[0] = str(new_class_id)
                    new_line = " ".join(parts) + "\n"
                    new_lines.append(new_line)
                    modified = True
                else:
                    modified = True
            except ValueError:
                print(f"Skipping invalid line in {txt_file}: {line.strip()}")
                continue

        if modified or output_dir:
            save_path = txt_file
            if output_dir:
                filename = os.path.basename(txt_file)
                save_path = os.path.join(output_dir, filename)

            with open(save_path, "w") as f:
                f.writelines(new_lines)
            count += 1
            if not new_lines:
                empty_count += 1

    print(f"Processed {count} files.")
    print(f"Generated {empty_count} empty label files (these act as negative samples/background images).")


def remap_dataset_splits(dataset_root, mapping, splits=None, output_root=None):
    """
    对同一数据集下的 train / valid / test 分别执行 remap_labels（使用相同 mapping）。

    Args:
        dataset_root: YOLO 数据集根目录（其下应有 train/valid/test 子目录，各含 labels/）
        mapping: {旧类别ID: 新类别ID}
        splits: 要处理的划分名，默认 Roboflow 风格 train, valid, test
        output_root: 若指定，则写入 output_root/<split>/labels/，保持目录结构；None 则原地覆盖各 split 的 labels
    """
    splits = splits or ("train", "valid", "test")
    print("--- 标签重映射（多划分）---")
    print(f"数据集根目录: {dataset_root}")
    print(f"划分: {list(splits)}")
    print(f"输出根目录: {output_root or '(原地覆盖)'}")
    print(f"映射规则: {mapping}")
    print()

    for split in splits:
        label_dir = os.path.join(dataset_root, split, "labels")
        if not os.path.isdir(label_dir):
            print(f"[跳过] 不存在: {label_dir}")
            continue
        out_dir = None
        if output_root:
            out_dir = os.path.join(output_root, split, "labels")
        print(f">>> {split}")
        remap_labels(label_dir, mapping, out_dir)
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO 标签类别 ID 重映射（可一次处理 train/valid/test）")
    parser.add_argument(
        "--dataset-root",
        type=str,
        default=None,
        help="数据集根目录（含 train/valid/test/labels），不填则使用脚本内 DATASET_ROOT",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default=None,
        help="可选。若指定，结果写到该目录下的 train|valid|test/labels/，不覆盖原数据",
    )
    parser.add_argument(
        "--splits",
        type=str,
        default="train,valid,test",
        help="逗号分隔，如 train,valid,test 或 train,val（若你的目录是 val 而非 valid）",
    )
    args = parser.parse_args()

    # --- 默认配置（命令行未传 --dataset-root 时使用）---
    _base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATASET_ROOT = os.path.join(_base, "data", "fire", "Spark.v2i.yolov11")

    dataset_root = args.dataset_root or DATASET_ROOT

    # 映射规则 {旧ID: 新ID}；不在映射中的类别行会被删除
    # 旧 ID 以该数据集自带的 data.yaml 为准；新 ID 对齐 ai_edge_system/data/data.yaml
    # Spark.v2i：nc=1, names=['sparks'] -> 旧 ID 0；统一 8 类里 sparks 为索引 3（清洗脚本已写 3 时可省略再映射）
    MAPPING = {
        0: 3,  # sparks -> sparks（项目全局类别 ID 3）
    }

    splits = tuple(s.strip() for s in args.splits.split(",") if s.strip())
    remap_dataset_splits(dataset_root, MAPPING, splits=splits, output_root=args.output_root)
