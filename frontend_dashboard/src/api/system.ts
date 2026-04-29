import apiClient from './axios';

export const systemApi = {
  // GET /system/health
  checkHealth: (): Promise<{ status: string; database: string }> => {
    return apiClient.get('/system/health');
  }
};