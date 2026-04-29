import axios from 'axios';
import type { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import type { ApiError } from '@/types';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      // Ensure headers object exists
      if (!config.headers) {
        config.headers = {} as any;
      }
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data;
  },
  async (error) => {
    if (error.response?.status === 401) {
      // 清除 token 并同步 auth store 状态，避免「已登录」但请求无 token 的不一致
      localStorage.removeItem('access_token');
      try {
        const { useAuthStore } = await import('@/store');
        useAuthStore().logout();
      } catch {
        // store 未就绪时仅清除 localStorage
      }
      window.location.href = '/login';
    }

    const apiError: ApiError = error.response?.data || {
      detail: '网络错误，请检查网络连接',
    };

    return Promise.reject(apiError);
  }
);

export default apiClient;