import { describe, it, expect, vi, beforeEach } from 'vitest';
import { alertApi } from '@/api/alerts';
import apiClient from '@/api/axios';

vi.mock('@/api/axios', () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
  },
}));

describe('Alert API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getAll calls /alerts/ with params', async () => {
    const params = { severity: 'CRITICAL' as const };
    const mockResponse = { items: [], total: 0, skip: 0, limit: 10 };
    (apiClient.get as any).mockResolvedValue(mockResponse);

    const result = await alertApi.getAll(params);

    expect(apiClient.get).toHaveBeenCalledWith('/alerts/', { params });
    expect(result).toEqual(mockResponse);
  });

  it('getStats calls /alerts/stats', async () => {
    const params = { start_date: '2023-01-01' };
    const mockStats = { total: 100, by_severity: { CRITICAL: 10 } };
    (apiClient.get as any).mockResolvedValue(mockStats);

    const result = await alertApi.getStats(params);

    expect(apiClient.get).toHaveBeenCalledWith('/alerts/stats', { params });
    expect(result).toEqual(mockStats);
  });

  it('acknowledge calls PUT /alerts/{id}/acknowledge', async () => {
    const id = 1;
    const notes = 'Handled';
    const mockAlert = { id: 1, is_acknowledged: true };
    (apiClient.put as any).mockResolvedValue(mockAlert);

    const result = await alertApi.acknowledge(id, notes);

    expect(apiClient.put).toHaveBeenCalledWith(`/alerts/${id}/acknowledge`, { notes });
    expect(result).toEqual(mockAlert);
  });

  it('acknowledge calls PUT /alerts/{id}/acknowledge without notes', async () => {
    const id = 1;
    const mockAlert = { id: 1, is_acknowledged: true };
    (apiClient.put as any).mockResolvedValue(mockAlert);

    const result = await alertApi.acknowledge(id);

    expect(apiClient.put).toHaveBeenCalledWith(`/alerts/${id}/acknowledge`, {});
    expect(result).toEqual(mockAlert);
  });
});
