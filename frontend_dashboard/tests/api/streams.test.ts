import { describe, it, expect, vi, beforeEach } from 'vitest';
import { streamApi } from '@/api/streams';
import apiClient from '@/api/axios';

vi.mock('@/api/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('Stream API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getStreamOffer calls /devices/{id}/stream/offer', async () => {
    const deviceId = 1;
    const quality = 'high';
    const mockOffer = { sdp: 'sdp', type: 'offer', stream_id: '123' };
    (apiClient.get as any).mockResolvedValue(mockOffer);

    const result = await streamApi.getStreamOffer(deviceId, quality);

    expect(apiClient.get).toHaveBeenCalledWith(`/devices/${deviceId}/stream/offer`, {
      params: { quality }
    });
    expect(result).toEqual(mockOffer);
  });

  it('sendStreamAnswer calls POST /devices/{id}/stream/answer', async () => {
    const deviceId = 1;
    const streamId = '123';
    const answer = { sdp: 'sdp_answer', type: 'answer' as const };
    const mockResponse = { status: 'connected' };
    (apiClient.post as any).mockResolvedValue(mockResponse);

    const result = await streamApi.sendStreamAnswer(deviceId, streamId, answer);

    expect(apiClient.post).toHaveBeenCalledWith(`/devices/${deviceId}/stream/answer`, {
      stream_id: streamId,
      ...answer
    });
    expect(result).toEqual(mockResponse);
  });

  it('getStreamStatus calls /devices/{id}/stream/status', async () => {
    const deviceId = 1;
    const mockStatus = { active: true, viewers: 1 };
    (apiClient.get as any).mockResolvedValue(mockStatus);

    const result = await streamApi.getStreamStatus(deviceId);

    expect(apiClient.get).toHaveBeenCalledWith(`/devices/${deviceId}/stream/status`);
    expect(result).toEqual(mockStatus);
  });

  it('controlStream calls POST /devices/{id}/stream/control', async () => {
    const deviceId = 1;
    const params = { device_id: deviceId, action: 'start' as const };
    const mockStatus = { active: true };
    (apiClient.post as any).mockResolvedValue(mockStatus);

    const result = await streamApi.controlStream(deviceId, params);

    expect(apiClient.post).toHaveBeenCalledWith(`/devices/${deviceId}/stream/control`, params);
    expect(result).toEqual(mockStatus);
  });

  it('stopStream calls DELETE /devices/{id}/stream', async () => {
    const deviceId = 1;
    const streamId = '123';
    (apiClient.delete as any).mockResolvedValue(undefined);

    await streamApi.stopStream(deviceId, streamId);

    expect(apiClient.delete).toHaveBeenCalledWith(`/devices/${deviceId}/stream`, {
      params: { stream_id: streamId }
    });
  });
});
