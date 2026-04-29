import apiClient from './axios';
import type { StreamOffer, StreamAnswer, StreamStatus, StreamControlParams } from '@/types';

export const streamApi = {
  // GET /devices/{id}/stream/offer
  getStreamOffer: (deviceId: number, quality?: 'low' | 'medium' | 'high'): Promise<StreamOffer> => {
    return apiClient.get(`/devices/${deviceId}/stream/offer`, {
      params: { quality }
    });
  },

  // POST /devices/{id}/stream/answer
  sendStreamAnswer: (deviceId: number, streamId: string, answer: StreamAnswer): Promise<{ status: string }> => {
    return apiClient.post(`/devices/${deviceId}/stream/answer`, {
      stream_id: streamId,
      ...answer
    });
  },

  // GET /devices/{id}/stream/status
  getStreamStatus: (deviceId: number): Promise<StreamStatus> => {
    return apiClient.get(`/devices/${deviceId}/stream/status`);
  },

  // POST /devices/{id}/stream/control
  controlStream: (deviceId: number, params: StreamControlParams): Promise<StreamStatus> => {
    return apiClient.post(`/devices/${deviceId}/stream/control`, params);
  },

  // DELETE /devices/{id}/stream
  stopStream: (deviceId: number, streamId: string): Promise<void> => {
    return apiClient.delete(`/devices/${deviceId}/stream`, {
      params: { stream_id: streamId }
    });
  }
};