import { describe, it, expect, vi, beforeEach } from 'vitest';
import { taskApi } from '@/api/tasks';
import apiClient from '@/api/axios';

vi.mock('@/api/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('Task API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getAll calls /tasks/ with params', async () => {
    const params = { status: 'pending' as const };
    const mockResponse = { items: [], total: 0, skip: 0, limit: 10 };
    (apiClient.get as any).mockResolvedValue(mockResponse);

    const result = await taskApi.getAll(params);

    expect(apiClient.get).toHaveBeenCalledWith('/tasks/', { params });
    expect(result).toEqual(mockResponse);
  });

  it('getById calls /tasks/{id}', async () => {
    const id = 1;
    const mockTask = { id: 1, title: 'Test Task' };
    (apiClient.get as any).mockResolvedValue(mockTask);

    const result = await taskApi.getById(id);

    expect(apiClient.get).toHaveBeenCalledWith(`/tasks/${id}`);
    expect(result).toEqual(mockTask);
  });

  it('create calls POST /tasks/', async () => {
    const taskData = { title: 'New Task', description: 'Desc', assigned_to: 1 };
    const mockTask = { id: 1, ...taskData };
    (apiClient.post as any).mockResolvedValue(mockTask);

    const result = await taskApi.create(taskData);

    expect(apiClient.post).toHaveBeenCalledWith('/tasks/', taskData);
    expect(result).toEqual(mockTask);
  });

  it('update calls PUT /tasks/{id}', async () => {
    const id = 1;
    const updateData = { status: 'completed' as const };
    const mockTask = { id: 1, status: 'completed' };
    (apiClient.put as any).mockResolvedValue(mockTask);

    const result = await taskApi.update(id, updateData);

    expect(apiClient.put).toHaveBeenCalledWith(`/tasks/${id}`, updateData);
    expect(result).toEqual(mockTask);
  });

  it('delete calls DELETE /tasks/{id}', async () => {
    const id = 1;
    (apiClient.delete as any).mockResolvedValue(undefined);

    await taskApi.delete(id);

    expect(apiClient.delete).toHaveBeenCalledWith(`/tasks/${id}`);
  });
});
