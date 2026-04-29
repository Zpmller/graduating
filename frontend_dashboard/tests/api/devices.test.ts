/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { deviceApi } from '@/api/devices';
import apiClient from '@/api/axios';

vi.mock('@/api/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('Device API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getAll calls /devices/ with params', async () => {
    const params = { status: 'online' };
    const mockResponse = { items: [], total: 0, skip: 0, limit: 10 };
    (apiClient.get as any).mockResolvedValue(mockResponse);

    const result = await deviceApi.getAll(params);

    expect(apiClient.get).toHaveBeenCalledWith('/devices/', { params });
    expect(result).toEqual(mockResponse);
  });

  it('getById calls /devices/{id}', async () => {
    const id = 1;
    const mockDevice = { id: 1, name: 'Cam1' };
    (apiClient.get as any).mockResolvedValue(mockDevice);

    const result = await deviceApi.getById(id);

    expect(apiClient.get).toHaveBeenCalledWith(`/devices/${id}`);
    expect(result).toEqual(mockDevice);
  });

  it('create calls POST /devices/', async () => {
    const deviceData = { name: 'Cam1', location: 'Gate', ip_address: '192.168.1.100' };
    const mockDevice = { id: 1, ...deviceData };
    (apiClient.post as any).mockResolvedValue(mockDevice);

    const result = await deviceApi.create(deviceData);

    expect(apiClient.post).toHaveBeenCalledWith('/devices/', deviceData);
    expect(result).toEqual(mockDevice);
  });

  it('update calls PUT /devices/{id}', async () => {
    const id = 1;
    const updateData = { name: 'Cam1 Updated' };
    const mockDevice = { id: 1, name: 'Cam1 Updated' };
    (apiClient.put as any).mockResolvedValue(mockDevice);

    const result = await deviceApi.update(id, updateData);

    expect(apiClient.put).toHaveBeenCalledWith(`/devices/${id}`, updateData);
    expect(result).toEqual(mockDevice);
  });

  it('delete calls DELETE /devices/{id}', async () => {
    const id = 1;
    (apiClient.delete as any).mockResolvedValue(undefined);

    await deviceApi.delete(id);

    expect(apiClient.delete).toHaveBeenCalledWith(`/devices/${id}`);
  });

  it('getCalibrationConfig calls /devices/{id}/calibration/yaml', async () => {
    const id = 1;
    const mockYaml = 'config: test';
    (apiClient.get as any).mockResolvedValue(mockYaml);

    const result = await deviceApi.getCalibrationConfig(id);

    expect(apiClient.get).toHaveBeenCalledWith(`/devices/${id}/calibration/yaml`);
    expect(result).toEqual(mockYaml);
  });

  it('uploadCalibrationConfig calls POST /devices/{id}/calibration/yaml with FormData', async () => {
    const id = 1;
    const file = new File(['content'], 'config.yaml', { type: 'text/yaml' });
    const mockResponse = { message: 'success' };
    (apiClient.post as any).mockResolvedValue(mockResponse);

    const result = await deviceApi.uploadCalibrationConfig(id, file);

    expect(apiClient.post).toHaveBeenCalledWith(
      `/devices/${id}/calibration/yaml`,
      expect.any(FormData),
      expect.objectContaining({ headers: { 'Content-Type': 'multipart/form-data' } })
    );
    expect(result).toEqual(mockResponse);
  });

  it('uploadCalibrationImages calls POST /devices/{id}/calibration/images with FormData', async () => {
    const id = 1;
    const files = [new File(['img'], 'img1.jpg', { type: 'image/jpeg' })];
    const mockResponse = { message: 'success' };
    (apiClient.post as any).mockResolvedValue(mockResponse);

    const result = await deviceApi.uploadCalibrationImages(id, files);

    expect(apiClient.post).toHaveBeenCalledWith(
      `/devices/${id}/calibration/images`,
      expect.any(FormData),
      expect.objectContaining({ headers: { 'Content-Type': 'multipart/form-data' } })
    );
    expect(result).toEqual(mockResponse);
  });
});
