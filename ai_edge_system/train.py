from ultralytics import YOLO
import os
import shutil
import torch
import argparse


def train_model(
    finetune: bool = False,
    weights: str | None = None,
    data_yaml: str | None = None,
    lr0: float | None = None,
    run_name: str = "mining_safety_v1",
):
    # 1. Setup Paths
    # Base directory: ai_edge_system (current folder of train.py)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Data config path（可用 --data 覆盖，例如只训 helmet2 子集时）
    data_config = data_yaml or os.path.join(base_dir, 'data', 'data.yaml')

    # 权重：微调默认 best.pt；否则 yolo11m.pt
    if weights:
        model_path = weights
    elif finetune:
        model_path = os.path.join(base_dir, 'models', 'best.pt')
    else:
        model_path = os.path.join(base_dir, 'models', 'yolo11m.pt')
    
    # Output directory for runs: ai_edge_system/models/runs
    project_dir = os.path.join(base_dir, 'models', 'runs')
    
    # Check if model exists
    if not os.path.exists(model_path):
        print(f"Error: Model file not found at {model_path}")
        return

    mode = "微调 (from best)" if finetune else "预训练 (from yolo11m)"
    print(f"[{mode}] Loading model from: {model_path}")
    model = YOLO(model_path) 

    # 2. Train the model
    print(f"Starting training with config: {data_config}")
    print(f"Output will be saved to: {project_dir}/{run_name}")
    
    # Auto-detect device
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        if gpu_count > 1:
            # Generate device string "0,1,..." for all available GPUs
            # If you want to specify specific GPUs (e.g., only 0 and 1), you can manually set device="0,1"
            device = ",".join(str(i) for i in range(gpu_count))
            print(f"Multi-GPU training enabled. Using devices: {device}")
        else:
            device = '0'
            print(f"Single GPU training enabled. Using device: {device}")
    else:
        device = 'cpu'
        print("Warning: CUDA not available. Using CPU for training.")

# Auto-adjust workers
    if os.name == 'nt':
        workers = 0  # Windows: must be 0 to avoid Shared File Mapping errors
        print("Windows detected. Setting workers to 0 for stability.")
    else:
        # Linux Server: Use available CPU cores (capped at 16 to avoid overhead)
        cpu_count = os.cpu_count() or 8
        workers = min(cpu_count, 24)
        print(f"Linux Server detected. Setting data loader workers to: {workers}") 

    # Auto-adjust batch size based on VRAM
    # Default for low VRAM (e.g. RTX 3060 6GB/12GB)
    batch_size = 8
    
    if torch.cuda.is_available():
        try:
            # Check total memory of device 0 (in bytes)
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            vram_gb = vram_bytes / (1024**3)
            print(f"Detected VRAM: {vram_gb:.2f} GB")
            
            if vram_gb > 30:
                # For RTX 5090 (32GB+), use even larger batch
                batch_size = 128
                print(f"Ultra-High VRAM (RTX 5090 class) detected. Setting batch size to {batch_size} for max speed.")
            elif vram_gb > 20:
                # For RTX 3090/4090 (24GB), use large batch
                batch_size = 64
                print(f"High VRAM detected. Setting batch size to {batch_size} for optimal server training.")
            else:
                print(f"Low/Medium VRAM detected. Keeping safe batch size: {batch_size}")
        except Exception as e:
            print(f"Could not detect VRAM size ({e}). Using default batch size: {batch_size}")
    
    # 微调时使用较小初始学习率（仍可用 --lr0 覆盖）；全量训练走 Ultralytics 默认 lr0
    if lr0 is None and finetune:
        lr0 = 0.003

    train_kw = dict(
            data=data_config,
            epochs=100,
            imgsz=640,
            device=device,
            batch=batch_size,
            project=project_dir,
            name=run_name,
            exist_ok=True,
            patience=50,
            save=True,
            workers=workers,
            amp=True,
            cos_lr=True,
            half=False,
            cache=True,
            nbs=64,
    )
    if lr0 is not None:
        train_kw["lr0"] = lr0

    try:
        results = model.train(**train_kw)
        
        # 3. Post-Training: Move/Copy best.pt to models/best.pt
        best_model_path = os.path.join(project_dir, run_name, 'weights', 'best.pt')
        target_path = os.path.join(base_dir, 'models', 'best.pt')
        
        if os.path.exists(best_model_path):
            print("-" * 50)
            print("Training completed successfully.")
            print(f"Copying best model to: {target_path}")
            shutil.copy2(best_model_path, target_path)
            print("Model updated. You can now run the application.")
            print("-" * 50)
        else:
            print(f"Warning: Could not find trained model at {best_model_path}")
            
    except Exception as e:
        print(f"An error occurred during training: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='YOLO 训练（支持从 best 微调）')
    parser.add_argument('--finetune', action='store_true', help='从 models/best.pt 加载，lr0 默认 0.003')
    parser.add_argument('--weights', type=str, default=None, help='权重 .pt 路径，覆盖默认 yolo11m/best')
    parser.add_argument('--data', type=str, default=None, help='data.yaml 路径，默认 data/data.yaml')
    parser.add_argument('--lr0', type=float, default=None, help='初始学习率，微调未指定时默认 0.003')
    parser.add_argument('--name', type=str, default=None, help='run 子目录名，默认 mining_safety_v1')
    args = parser.parse_args()
    train_model(
        finetune=args.finetune,
        weights=args.weights,
        data_yaml=args.data,
        lr0=args.lr0,
        run_name=args.name or "mining_safety_v1",
    )
