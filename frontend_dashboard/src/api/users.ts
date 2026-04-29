import apiClient from './axios';
import type { User, PaginatedResponse, CreateUserParams, UpdateUserParams } from '@/types';

export const userApi = {
  // GET /users/
  getAll: (params?: { skip?: number; limit?: number }): Promise<PaginatedResponse<User>> => {
    return apiClient.get('/users/', { params });
  },

  // GET /users/{id}
  getById: (id: number): Promise<User> => {
    return apiClient.get(`/users/${id}`);
  },

  // POST /users/
  create: (data: CreateUserParams): Promise<User> => {
    return apiClient.post('/users/', data);
  },

  // PUT /users/{id}
  update: (id: number, data: UpdateUserParams): Promise<User> => {
    return apiClient.put(`/users/${id}`, data);
  },

  // DELETE /users/{id}
  delete: (id: number): Promise<void> => {
    return apiClient.delete(`/users/${id}`);
  }
};