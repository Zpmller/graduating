import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { User, LoginParams, TokenResponse } from '@/types';
import { authApi } from '@/api';

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null);
  const token = ref<string | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Getters
  const isAuthenticated = computed(() => !!token.value);
  const isAdmin = computed(() => user.value?.role === 'admin');
  const userRole = computed(() => user.value?.role || 'viewer');

  // Actions
  const login = async (credentials: LoginParams) => {
    loading.value = true;
    error.value = null;

    try {
      const response: TokenResponse = await authApi.login(credentials);
      token.value = response.access_token;

      // Store token in localStorage
      localStorage.setItem('access_token', response.access_token);

      // Get user info
      await fetchCurrentUser();

      return true;
    } catch (err: any) {
      error.value = err.detail || '登录失败';
      return false;
    } finally {
      loading.value = false;
    }
  };

  const fetchCurrentUser = async () => {
    try {
      const userData = await authApi.getCurrentUser();
      user.value = userData;
    } catch (err: any) {
      error.value = err.detail || '获取用户信息失败';
      logout();
    }
  };

  const logout = () => {
    user.value = null;
    token.value = null;
    localStorage.removeItem('access_token');
    error.value = null;
  };

  const initializeAuth = () => {
    const storedToken = localStorage.getItem('access_token');
    if (storedToken) {
      token.value = storedToken;
      fetchCurrentUser();
    }
  };

  return {
    // State
    user,
    token,
    loading,
    error,

    // Getters
    isAuthenticated,
    isAdmin,
    userRole,

    // Actions
    login,
    fetchCurrentUser,
    logout,
    initializeAuth,
  };
});