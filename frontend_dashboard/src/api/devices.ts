import apiClient from './axios';
import type { Device, PaginatedResponse, CreateDeviceParams, UpdateDeviceParams } from '@/types';

export const deviceApi = {
  // GET /devices/（支持 include_stream_status 获取在线状态与视频流信息）
  getAll: (params?: {
    skip?: number;
    limit?: number;
    status?: string;
    include_stream_status?: boolean;
  }): Promise<PaginatedResponse<Device>> => {
    return apiClient.get('/devices/', { params });
  },

  // GET /devices/{id}
  getById: (id: number): Promise<Device> => {
    return apiClient.get(`/devices/${id}`);
  },

  // POST /devices/
  create: (data: CreateDeviceParams): Promise<Device> => {
    return apiClient.post('/devices/', data);
  },

  // PUT /devices/{id}
  update: (id: number, data: UpdateDeviceParams): Promise<Device> => {
    return apiClient.put(`/devices/${id}`, data);
  },

  // DELETE /devices/{id}
  delete: (id: number): Promise<void> => {
    return apiClient.delete(`/devices/${id}`);
  },

  // GET /devices/{id}/calibration/yaml
  getCalibrationConfig: (id: number): Promise<string> => {
    return apiClient.get(`/devices/${id}/calibration/yaml`);
  },

  // POST /devices/{id}/calibration/yaml
  uploadCalibrationConfig: (id: number, file: File): Promise<{ message: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post(`/devices/${id}/calibration/yaml`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  // POST /devices/{id}/calibration/images
  uploadCalibrationImages: (id: number, files: File[]): Promise<{ message: string }> => {
    const formData = new FormData();
    files.forEach((file) => formData.append('images', file));
    return apiClient.post(`/devices/${id}/calibration/images`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  }
};