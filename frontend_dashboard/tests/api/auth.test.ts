import { describe, it, expect, vi, beforeEach } from 'vitest';
import { authApi } from '@/api/auth';
import apiClient from '@/api/axios';

// Mock the apiClient
vi.mock('@/api/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('Auth API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('login calls /auth/token with correct credentials', async () => {
    const credentials = { username: 'admin', password: 'password' };
    const mockResponse = { access_token: 'token', token_type: 'bearer', expires_in: 3600 };
    (apiClient.post as any).mockResolvedValue(mockResponse);

    const result = await authApi.login(credentials);

    expect(apiClient.post).toHaveBeenCalledWith('/auth/token', credentials);
    expect(result).toEqual(mockResponse);
  });

  it('getCurrentUser calls /auth/me', async () => {
    const mockUser = { id: 1, username: 'admin', role: 'admin', is_active: true };
    (apiClient.get as any).mockResolvedValue(mockUser);

    const result = await authApi.getCurrentUser();

    expect(apiClient.get).toHaveBeenCalledWith('/auth/me');
    expect(result).toEqual(mockUser);
  });
});
