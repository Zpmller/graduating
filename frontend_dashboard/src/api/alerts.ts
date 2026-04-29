import apiClient from './axios';
import type { Alert, PaginatedResponse, AlertFilterParams, AlertStats } from '@/types';

export const alertApi = {
  // GET /alerts/
  getAll: (params?: AlertFilterParams): Promise<PaginatedResponse<Alert>> => {
    // Filter out empty strings and null/undefined values
    const filteredParams = params
      ? Object.fromEntries(
          Object.entries(params).filter(
            ([_, v]) => v !== '' && v !== null && v !== undefined
          )
        )
      : undefined;
    return apiClient.get('/alerts/', { params: filteredParams });
  },

  // GET /alerts/stats
  getStats: (params?: { start_date?: string; end_date?: string }): Promise<AlertStats> => {
    return apiClient.get('/alerts/stats', { params });
  },

  // PUT /alerts/{id}/acknowledge
  acknowledge: (id: number, notes?: string): Promise<Alert> => {
    return apiClient.put(`/alerts/${id}/acknowledge`, notes ? { notes } : {});
  }
};