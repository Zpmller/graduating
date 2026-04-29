import sys
import os
import warnings

# 抑制 tf_keras 中 tf.losses.sparse_softmax_cross_entropy 的弃用警告（来自依赖库，非本项目代码）
warnings.filterwarnings(
    "ignore",
    message=".*tf\\.losses\\.sparse_softmax_cross_entropy.*deprecated.*",
    category=DeprecationWarning,
)
# 降低 TensorFlow 日志级别，减少启动时的弃用类输出
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import logging
logging.getLogger("tensorflow").setLevel(logging.ERROR)

# Fix for WinError 1114: Import torch before PyQt5
# This prevents DLL conflicts between PyQt5 and Torch (OpenMP/MKL)
import torch

from PyQt5.QtWidgets import QApplication

# 1. Setup path to allow imports from 'src'
# Get the directory where this script is located (ai_edge_system)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Add it to sys.path so that 'import src.xxx' works
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Now we can import from src
try:
    from src.ui.main_window import MainWindow
except ImportError as e:
    print(f"Error importing modules: {e}")
    print(f"Current sys.path: {sys.path}")
    print("Ensure you are running the script from the correct directory or that 'src' exists.")
    sys.exit(1)

def main():
    # 2. Initialize PyQt Application
    app = QApplication(sys.argv)
    
    # 3. Create and Show Main Window
    window = MainWindow()
    window.show()
    
    # 4. Execute Application Event Loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    print("Starting Mining Hot-Work Safety Monitoring System...")
    main()
