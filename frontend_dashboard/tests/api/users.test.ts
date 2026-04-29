import { describe, it, expect, vi, beforeEach } from 'vitest';
import { userApi } from '@/api/users';
import apiClient from '@/api/axios';

vi.mock('@/api/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('User API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getAll calls /users/ with params', async () => {
    const params = { skip: 0, limit: 10 };
    const mockResponse = [{ id: 1, username: 'test' }];
    (apiClient.get as any).mockResolvedValue(mockResponse);

    const result = await userApi.getAll(params);

    expect(apiClient.get).toHaveBeenCalledWith('/users/', { params });
    expect(result).toEqual(mockResponse);
  });

  it('getById calls /users/{id}', async () => {
    const id = 1;
    const mockUser = { id: 1, username: 'test' };
    (apiClient.get as any).mockResolvedValue(mockUser);

    const result = await userApi.getById(id);

    expect(apiClient.get).toHaveBeenCalledWith(`/users/${id}`);
    expect(result).toEqual(mockUser);
  });

  it('create calls POST /users/', async () => {
    const userData = { username: 'newuser', password: 'pw', role: 'operator' as const };
    const mockUser = { id: 2, ...userData };
    (apiClient.post as any).mockResolvedValue(mockUser);

    const result = await userApi.create(userData);

    expect(apiClient.post).toHaveBeenCalledWith('/users/', userData);
    expect(result).toEqual(mockUser);
  });

  it('update calls PUT /users/{id}', async () => {
    const id = 1;
    const updateData = { is_active: false };
    const mockUser = { id: 1, username: 'test', is_active: false };
    (apiClient.put as any).mockResolvedValue(mockUser);

    const result = await userApi.update(id, updateData);

    expect(apiClient.put).toHaveBeenCalledWith(`/users/${id}`, updateData);
    expect(result).toEqual(mockUser);
  });

  it('delete calls DELETE /users/{id}', async () => {
    const id = 1;
    (apiClient.delete as any).mockResolvedValue(undefined);

    await userApi.delete(id);

    expect(apiClient.delete).toHaveBeenCalledWith(`/users/${id}`);
  });
});
