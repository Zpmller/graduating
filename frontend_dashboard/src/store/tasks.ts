import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Task, CreateTaskParams, UpdateTaskParams, TaskFilterParams } from '@/types';
import { taskApi } from '@/api';

export const useTaskStore = defineStore('tasks', () => {
  // State
  const tasks = ref<Task[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Getters
  const pendingTasks = computed(() =>
    tasks.value.filter(task => task.status === 'pending')
  );

  const inProgressTasks = computed(() =>
    tasks.value.filter(task => task.status === 'in_progress')
  );

  const completedTasks = computed(() =>
    tasks.value.filter(task => task.status === 'completed')
  );

  const tasksByAssignee = computed(() => (assigneeId: number) =>
    tasks.value.filter(task => task.assigned_to === assigneeId)
  );

  const highPriorityTasks = computed(() =>
    tasks.value.filter(task => task.priority === 'high')
  );

  // Actions
  const fetchTasks = async (params?: TaskFilterParams) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await taskApi.getAll(params);
      tasks.value = response.items;
    } catch (err: any) {
      error.value = err.detail || '获取任务列表失败';
    } finally {
      loading.value = false;
    }
  };

  const createTask = async (data: CreateTaskParams) => {
    loading.value = true;
    error.value = null;

    try {
      const newTask = await taskApi.create(data);
      tasks.value.unshift(newTask);
      return newTask;
    } catch (err: any) {
      error.value = err.detail || '创建任务失败';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const updateTask = async (id: number, data: UpdateTaskParams) => {
    loading.value = true;
    error.value = null;

    try {
      const updatedTask = await taskApi.update(id, data);
      const index = tasks.value.findIndex(task => task.id === id);
      if (index !== -1) {
        tasks.value[index] = updatedTask;
      }
      return updatedTask;
    } catch (err: any) {
      error.value = err.detail || '更新任务失败';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const deleteTask = async (id: number) => {
    loading.value = true;
    error.value = null;

    try {
      await taskApi.delete(id);
      tasks.value = tasks.value.filter(task => task.id !== id);
    } catch (err: any) {
      error.value = err.detail || '删除任务失败';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const getTaskById = async (id: number) => {
    try {
      return await taskApi.getById(id);
    } catch (err: any) {
      error.value = err.detail || '获取任务详情失败';
      throw err;
    }
  };

  return {
    // State
    tasks,
    loading,
    error,

    // Getters
    pendingTasks,
    inProgressTasks,
    completedTasks,
    tasksByAssignee,
    highPriorityTasks,

    // Actions
    fetchTasks,
    createTask,
    updateTask,
    deleteTask,
    getTaskById,
  };
});