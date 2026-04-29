"""
Edge Node HTTP 控制服务
供后端通知开始/停止推流
"""
import os
import threading
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

# 主窗口引用，由 main_window 在启动时设置
_main_window_ref = None

# API 触发的独立推流（不依赖 Qt 主窗口/定时器），保证有帧推送到 SRS
_api_stream_state = {"thread": None, "streamer": None, "cap": None, "stop_event": None}


def set_main_window(main_window):
    """设置主窗口引用，用于调用 start_video_stream 等"""
    global _main_window_ref
    _main_window_ref = main_window


def run_control_server(port: int = 8080):
    """在后台线程运行 Flask 服务"""
    app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False, debug=False)


def _api_stream_worker(device_id: int, stream_id: str, media_server_url: str, quality: str, source_url: str):
    """在独立线程中打开视频源、做检测画框、规则告警并上传，推帧到 SRS。"""
    global _api_stream_state, _main_window_ref
    import cv2
    from src.core.streamer import VideoStreamer
    from src.core.detector import Detector
    from src.logic.safety import SafetyEngine
    from src.core.uploader import AlertUploader

    cap = None
    streamer = None
    detector = None
    uploader = None
    try:
        streamer = VideoStreamer(
            media_server_url=media_server_url,
            device_id=device_id,
            stream_id=stream_id,
            quality=quality,
        )
        streamer.start_stream()
        _api_stream_state["streamer"] = streamer

        # 与主窗口一致的模型路径
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(base_dir, "models", "best.pt")
        if not os.path.exists(model_path):
            model_path = "yolo11m.pt"
        detector = Detector(model_path=model_path)
        safety_engine = SafetyEngine()
        conf_threshold = 0.25

        # 告警上传：优先使用主窗口的 uploader（已由 bootstrap 配置 device_id/token），否则新建
        if _main_window_ref and getattr(_main_window_ref, "uploader", None):
            uploader = _main_window_ref.uploader
        else:
            uploader = AlertUploader(device_id=device_id)

        # 视频源："0" 或空为默认摄像头，否则为 RTSP/URL 或摄像头索引
        source = (source_url or "").strip() or "0"
        if source.isdigit():
            source = int(source)
        cap = cv2.VideoCapture(source)
        _api_stream_state["cap"] = cap
        if not cap.isOpened():
            print(f"[StreamControl] Failed to open source: {source}")
            return
        print(f"[StreamControl] API stream started (with detection + alerts): source={source}, stream_id={stream_id}")

        stop_event = _api_stream_state.get("stop_event")
        while stop_event and not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue
            if streamer and streamer.is_streaming and detector:
                results = detector.detect(frame, conf_threshold=conf_threshold)
                detections_list = detector.get_detections_list(results) if results else []
                alerts = safety_engine.check_rules(detections_list, frame)
                if uploader and alerts:
                    for alert in alerts:
                        uploader.add_alert(alert, frame)
                annotated = results[0].plot() if results else frame
                streamer.push_frame(annotated)
            elif streamer and streamer.is_streaming:
                streamer.push_frame(frame)
            time.sleep(max(0, 1.0 / streamer.fps - 0.001)) if streamer else time.sleep(0.04)
    except Exception as e:
        print(f"[StreamControl] API stream error: {e}")
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass
        if streamer is not None:
            try:
                streamer.stop_stream()
            except Exception:
                pass
        _api_stream_state["streamer"] = None
        _api_stream_state["cap"] = None
        _api_stream_state["thread"] = None


@app.route("/api/stream/control", methods=["POST"])
def stream_control():
    """
    接收后端的推流控制请求
    使用独立线程打开视频源并推流到 SRS，不依赖 Qt 主窗口，确保有帧推送。
    Body: {
        "action": "start_stream",
        "stream_id": "stream_1_xxx",
        "rtsp_push_url": "rtmp://...",
        "quality": "medium",
        "source_url": "0 或 rtsp://...",
        "device_id": 1
    }
    """
    global _api_stream_state

    try:
        data = request.get_json() or {}
        action = data.get("action")
        if action != "start_stream":
            return jsonify({"error": f"Unknown action: {action}"}), 400

        stream_id = data.get("stream_id")
        rtsp_push_url = data.get("rtsp_push_url")
        quality = data.get("quality", "medium")
        source_url = data.get("source_url")
        device_id = data.get("device_id")

        if not stream_id or not rtsp_push_url:
            return jsonify({"error": "Missing stream_id or rtsp_push_url"}), 400

        if "/live/" in rtsp_push_url:
            base_url = rtsp_push_url.split("/live/")[0]
        else:
            base_url = rtsp_push_url.rsplit("/", 1)[0] if "/" in rtsp_push_url else rtsp_push_url

        device_id = int(device_id) if device_id is not None else 0

        # 若已有 API 推流在跑，先停掉
        if _api_stream_state.get("thread") and _api_stream_state["thread"].is_alive():
            if _api_stream_state.get("stop_event"):
                _api_stream_state["stop_event"].set()
            _api_stream_state["thread"].join(timeout=3.0)

        stop_event = threading.Event()
        _api_stream_state["stop_event"] = stop_event
        _api_stream_state["thread"] = threading.Thread(
            target=_api_stream_worker,
            args=(device_id, stream_id, base_url, quality, source_url or "0"),
            daemon=True,
        )
        _api_stream_state["thread"].start()

        return jsonify({"status": "ok", "stream_id": stream_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stream/stop", methods=["POST"])
def stream_stop():
    """停止 API 触发的推流"""
    global _api_stream_state
    if _api_stream_state.get("stop_event"):
        _api_stream_state["stop_event"].set()
    if _api_stream_state.get("thread") and _api_stream_state["thread"].is_alive():
        _api_stream_state["thread"].join(timeout=3.0)
    _api_stream_state["streamer"] = None
    _api_stream_state["cap"] = None
    _api_stream_state["thread"] = None
    return jsonify({"status": "ok"})


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({"status": "ok"})
