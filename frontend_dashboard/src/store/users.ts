import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { User, CreateUserParams, UpdateUserParams } from '@/types';
import { userApi } from '@/api';

export const useUserStore = defineStore('users', () => {
  // State
  const users = ref<User[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Getters
  const activeUsers = computed(() =>
    users.value.filter(user => user.is_active)
  );

  const inactiveUsers = computed(() =>
    users.value.filter(user => !user.is_active)
  );

  const usersByRole = computed(() => (role: string) =>
    users.value.filter(user => user.role === role)
  );

  const adminUsers = computed(() =>
    users.value.filter(user => user.role === 'admin')
  );

  const operatorUsers = computed(() =>
    users.value.filter(user => user.role === 'operator')
  );

  // Actions
  const fetchUsers = async () => {
    loading.value = true;
    error.value = null;

    try {
      const res = await userApi.getAll();
      users.value = res.items ?? [];
    } catch (err: any) {
      error.value = err.detail || '获取用户列表失败';
    } finally {
      loading.value = false;
    }
  };

  const createUser = async (data: CreateUserParams) => {
    loading.value = true;
    error.value = null;

    try {
      const newUser = await userApi.create(data);
      users.value.push(newUser);
      return newUser;
    } catch (err: any) {
      error.value = err.detail || '创建用户失败';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const updateUser = async (id: number, data: UpdateUserParams) => {
    loading.value = true;
    error.value = null;

    try {
      const updatedUser = await userApi.update(id, data);
      const index = users.value.findIndex(user => user.id === id);
      if (index !== -1) {
        users.value[index] = updatedUser;
      }
      return updatedUser;
    } catch (err: any) {
      error.value = err.detail || '更新用户失败';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const deleteUser = async (id: number) => {
    loading.value = true;
    error.value = null;

    try {
      await userApi.delete(id);
      users.value = users.value.filter(user => user.id !== id);
    } catch (err: any) {
      error.value = err.detail || '删除用户失败';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const getUserById = async (id: number) => {
    try {
      return await userApi.getById(id);
    } catch (err: any) {
      error.value = err.detail || '获取用户详情失败';
      throw err;
    }
  };

  return {
    // State
    users,
    loading,
    error,

    // Getters
    activeUsers,
    inactiveUsers,
    usersByRole,
    adminUsers,
    operatorUsers,

    // Actions
    fetchUsers,
    createUser,
    updateUser,
    deleteUser,
    getUserById,
  };
});