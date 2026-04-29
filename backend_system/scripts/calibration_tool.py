"""
相机标定工具（命令行版本）
用于后端服务处理标定图片并生成标定配置文件
"""
import argparse
import sys
import os
import glob
import cv2
import numpy as np
import yaml
from pathlib import Path


def perform_calibration(images, pattern_size, square_size, log_cb=None):
    """
    执行相机标定
    
    Args:
        images: 图片文件路径列表
        pattern_size: 棋盘格角点数量 (rows, cols)
        square_size: 棋盘格方格大小（毫米）
        log_cb: 日志回调函数（可选）
    
    Returns:
        tuple: (camera_matrix, dist_coeffs, reprojection_error) 或 (None, None, None) 如果失败
    """
    if log_cb:
        log_cb(f"Starting calibration with {len(images)} images...")
    
    # 准备对象点（3D点）
    objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
    objp *= square_size

    objpoints = []  # 3D点
    imgpoints = []  # 2D点

    valid_images = 0
    gray = None
    
    total_imgs = len(images)
    
    for i, fname in enumerate(images):
        img = cv2.imread(fname)
        if img is None:
            if log_cb:
                log_cb(f"Failed to read {fname}")
            continue
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)

        if ret:
            objpoints.append(objp)
            # 亚像素级角点检测
            corners2 = cv2.cornerSubPix(
                gray, corners, (11, 11), (-1, -1),
                criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            )
            imgpoints.append(corners2)
            valid_images += 1
            if log_cb:
                log_cb(f"Found corners in {os.path.basename(fname)}")
        else:
            if log_cb:
                log_cb(f"Corners NOT found in {os.path.basename(fname)}")

    if valid_images == 0:
        if log_cb:
            log_cb(f"No valid images found for calibration. Searched for pattern size: {pattern_size}")
        return None, None, None, None

    if log_cb:
        log_cb(f"Calibrating with {valid_images} valid images...")
    
    # 执行标定
    h, w = gray.shape[:2]
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, (w, h), None, None
    )

    # 计算重投影误差
    mean_error = 0
    for i in range(len(objpoints)):
        imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
        error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
        mean_error += error
    total_error = mean_error / len(objpoints)
    
    if log_cb:
        log_cb(f"Calibration completed. Re-projection error: {total_error:.4f}")
    
    return mtx, dist, total_error, (h, w)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Camera calibration tool for backend service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python calibration_tool.py --images_dir ./images --output calibration.yaml
  python calibration_tool.py --images_dir ./images --output calibration.yaml --rows 9 --cols 6 --size 25.0
        """
    )
    parser.add_argument(
        '--images_dir',
        type=str,
        required=True,
        help='Directory containing calibration images'
    )
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output YAML file path'
    )
    parser.add_argument(
        '--rows',
        type=int,
        default=9,
        help='Number of inner corners per row (default: 9)'
    )
    parser.add_argument(
        '--cols',
        type=int,
        default=6,
        help='Number of inner corners per column (default: 6)'
    )
    parser.add_argument(
        '--size',
        type=float,
        default=25.0,
        help='Square size in millimeters (default: 25.0)'
    )
    
    args = parser.parse_args()
    
    # 验证输入目录
    images_dir = Path(args.images_dir)
    if not images_dir.exists():
        print(f"Error: Directory {args.images_dir} does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not images_dir.is_dir():
        print(f"Error: {args.images_dir} is not a directory", file=sys.stderr)
        sys.exit(1)
    
    # 查找图片文件
    image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.PNG', '*.JPG', '*.JPEG', '*.BMP']
    image_files = set()
    for ext in image_extensions:
        image_files.update(str(p) for p in images_dir.glob(ext))
    
    image_files = sorted(list(image_files))
    
    if not image_files:
        print(f"Error: No image files found in {args.images_dir}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(image_files)} image files")
    print(f"Pattern size: {args.rows}x{args.cols} corners")
    print(f"Square size: {args.size} mm")
    
    # 执行标定
    pattern_size = (args.rows, args.cols)
    mtx, dist, error, img_size = perform_calibration(
        image_files,
        pattern_size,
        args.size,
        log_cb=print
    )
    
    if mtx is None:
        print("Error: Calibration failed. No valid images found.", file=sys.stderr)
        sys.exit(1)
    
    # 保存结果
    try:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'camera_matrix': mtx.tolist(),
            'dist_coeffs': dist.tolist(),
            'reprojection_error': float(error),
            'image_size': list(img_size[::-1]),  # (width, height)
            'pattern_size': list(pattern_size),
            'square_size': args.size
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        
        print(f"\nCalibration successful!")
        print(f"Output saved to: {output_path}")
        print(f"Re-projection error: {error:.4f}")
        print(f"Camera matrix shape: {mtx.shape}")
        print(f"Distortion coefficients shape: {dist.shape}")
        
    except Exception as e:
        print(f"Error saving calibration file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
