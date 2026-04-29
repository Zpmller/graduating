import apiClient from './axios';
import type { Task, PaginatedResponse, CreateTaskParams, UpdateTaskParams, TaskFilterParams } from '@/types';

export const taskApi = {
  // GET /tasks/
  getAll: (params?: TaskFilterParams): Promise<PaginatedResponse<Task>> => {
    return apiClient.get('/tasks/', { params });
  },

  // GET /tasks/{id}
  getById: (id: number): Promise<Task> => {
    return apiClient.get(`/tasks/${id}`);
  },

  // POST /tasks/
  create: (data: CreateTaskParams): Promise<Task> => {
    return apiClient.post('/tasks/', data);
  },

  // PUT /tasks/{id}
  update: (id: number, data: UpdateTaskParams): Promise<Task> => {
    return apiClient.put(`/tasks/${id}`, data);
  },

  // DELETE /tasks/{id}
  delete: (id: number): Promise<void> => {
    return apiClient.delete(`/tasks/${id}`);
  }
};