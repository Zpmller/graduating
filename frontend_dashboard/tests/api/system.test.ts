import { describe, it, expect, vi, beforeEach } from 'vitest';
import { systemApi } from '@/api/system';
import apiClient from '@/api/axios';

vi.mock('@/api/axios', () => ({
  default: {
    get: vi.fn(),
  },
}));

describe('System API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('checkHealth calls /system/health', async () => {
    const mockHealth = { status: 'ok', database: 'connected' };
    (apiClient.get as any).mockResolvedValue(mockHealth);

    const result = await systemApi.checkHealth();

    expect(apiClient.get).toHaveBeenCalledWith('/system/health');
    expect(result).toEqual(mockHealth);
  });
});
