import apiClient from './axios';
import type { LoginParams, TokenResponse, User } from '@/types';

export const authApi = {
  // POST /auth/token
  login: (credentials: LoginParams): Promise<TokenResponse> => {
    return apiClient.post('/auth/token', credentials);
  },

  // GET /auth/me
  getCurrentUser: (): Promise<User> => {
    return apiClient.get('/auth/me');
  }
};