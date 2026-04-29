import type { StreamOffer } from '@/types';
import apiClient from '@/api/axios';

// #region agent log
const _dbg = (msg: string, data: Record<string, unknown>) => {
  console.log('[StreamDebug]', msg, data);
  fetch('http://127.0.0.1:7906/ingest/961b9707-2d8e-4b68-9d7c-de21fdda61c9', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '870502' },
    body: JSON.stringify({ sessionId: '870502', location: 'webrtc.ts', message: msg, data: { ...data, timestamp: Date.now() } })
  }).catch(() => {});
};
// #endregion

/**
 * 确保 SDP 包含 a=group:BUNDLE，SRS 强制要求
 */
function ensureBundleInSdp(sdp: string): string {
  if (/a=group:BUNDLE/i.test(sdp)) return sdp;
  const mids: string[] = [];
  const midMatch = sdp.matchAll(/a=mid:(\S+)/g);
  for (const m of midMatch) mids.push(m[1]);
  const bundleLine = mids.length > 0
    ? `a=group:BUNDLE ${mids.join(' ')}\r\n`
    : 'a=group:BUNDLE 0 1\r\n';
  const firstM = sdp.indexOf('\nm=');
  if (firstM >= 0) {
    return sdp.slice(0, firstM + 1) + bundleLine + sdp.slice(firstM + 1);
  }
  return sdp + '\r\n' + bundleLine;
}

/**
 * WebRTC 播放器（WHEP 协议）
 * 前端 POST SDP offer 到 WHEP（经后端代理到 SRS），获取 answer 建立连接
 */
export class WebRTCStreamManager {
  private peerConnection: RTCPeerConnection | null = null;
  private videoElement: HTMLVideoElement | null = null;

  constructor(videoElement: HTMLVideoElement) {
    this.videoElement = videoElement;
  }

  async startStream(offer: StreamOffer): Promise<void> {
    if (!offer.whep_url || !offer.stream_id) {
      throw new Error('Invalid offer: missing whep_url or stream_id');
    }

    this.peerConnection = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
      bundlePolicy: 'max-bundle'  // SRS 要求 BUNDLE，否则 SDP 协商失败
    });

    this.peerConnection.ontrack = (event) => {
      const s0 = event.streams[0];
      const tracks = s0 ? s0.getTracks().map((t) => ({ kind: t.kind, readyState: t.readyState, muted: t.muted, enabled: t.enabled })) : [];
      // #region agent log
      _dbg('ontrack', { kind: event.track.kind, streams: event.streams.length, track_readyState: event.track.readyState, track_muted: event.track.muted, tracks });
      // #endregion
      if (!this.videoElement || !s0) return;
      // 只绑定一次流并调用一次 play()，避免第二次 ontrack(audio) 再次设置 srcObject 导致 "play() interrupted by a new load request" 黑屏
      if (this.videoElement.srcObject !== s0) {
        this.videoElement.srcObject = s0;
        this.videoElement.play().catch((e) => {
          // #region agent log
          _dbg('play failed', { err: String(e) });
          // #endregion
        });
        // #region agent log
        _dbg('after srcObject', { videoReadyState: this.videoElement.readyState, videoError: this.videoElement.error?.message ?? null });
        // #endregion
      }
    };

    // WHEP 播放：添加 recvonly 收发器，确保 SDP 含 a=group:BUNDLE 0 1
    this.peerConnection.addTransceiver('video', { direction: 'recvonly' });
    this.peerConnection.addTransceiver('audio', { direction: 'recvonly' });

    // 1. 创建 offer
    const pcOffer = await this.peerConnection.createOffer();
    await this.peerConnection.setLocalDescription(pcOffer);

    let offerSdp = this.peerConnection.localDescription?.sdp;
    if (!offerSdp) {
      throw new Error('Failed to create offer');
    }
    offerSdp = ensureBundleInSdp(offerSdp);
    await this.peerConnection.setLocalDescription({ type: 'offer', sdp: offerSdp });

    // 2. 构建完整 URL（whep_url 可能为相对路径 /api/stream/whep/xxx）
    const baseURL = apiClient.defaults.baseURL || '';
    const whepFullUrl = offer.whep_url.startsWith('http')
      ? offer.whep_url
      : `${baseURL.replace(/\/$/, '')}${offer.whep_url.startsWith('/') ? '' : '/'}${offer.whep_url}`;
    // #region agent log
    _dbg('WHEP URL', { whepFullUrl, stream_id: offer.stream_id });
    // #endregion

    // 3. POST offer 到 WHEP URL（带认证头）
    const token = localStorage.getItem('access_token');
    const headers: Record<string, string> = {
      'Content-Type': 'application/sdp'
    };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(whepFullUrl, {
      method: 'POST',
      headers,
      body: offerSdp
    });

    if (!response.ok) {
      const text = await response.text();
      // #region agent log
      _dbg('WHEP failed', { status: response.status, text });
      // #endregion
      throw new Error(`WHEP request failed ${response.status}: ${text}`);
    }

    const answerSdp = await response.text();
    // #region agent log
    _dbg('WHEP ok', { answerLen: answerSdp.length });
    // #endregion

    if (!this.peerConnection) {
      throw new Error('Stream was stopped');
    }

    // 3. 设置远程描述 (answer)
    const answer: RTCSessionDescriptionInit = {
      type: 'answer',
      sdp: answerSdp
    };
    await this.peerConnection.setRemoteDescription(new RTCSessionDescription(answer));

    if (!this.peerConnection) {
      throw new Error('Stream was stopped');
    }

    // 4. 等待 ICE 连接建立（否则可能无媒体流）
    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        // #region agent log
        _dbg('ICE timeout', { state: this.peerConnection?.connectionState });
        // #endregion
        reject(new Error('连接超时'));
      }, 15000);
      const onStateChange = () => {
        const state = this.peerConnection?.connectionState;
        // #region agent log
        _dbg('connectionstatechange', { state });
        // #endregion
        if (state === 'connected') {
          clearTimeout(timeout);
          this.peerConnection?.removeEventListener('connectionstatechange', onStateChange);
          resolve();
        } else if (state === 'failed' || state === 'disconnected' || state === 'closed') {
          clearTimeout(timeout);
          this.peerConnection?.removeEventListener('connectionstatechange', onStateChange);
          reject(new Error(`连接失败: ${state}`));
        }
      };
      if (this.peerConnection?.connectionState === 'connected') {
        clearTimeout(timeout);
        resolve();
      } else {
        this.peerConnection?.addEventListener('connectionstatechange', onStateChange);
      }
    });
  }

  stopStream(): void {
    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }
    if (this.videoElement) {
      this.videoElement.srcObject = null;
    }
  }

  toggleDetectionOverlay(_enabled: boolean): void {
    // WHEP 模式下覆盖层由 Edge 控制，可通过后端 control API 通知 Edge
    // 此处无需通过 WebSocket 发送
  }
}
