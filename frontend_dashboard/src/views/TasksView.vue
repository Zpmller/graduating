<template>
  <AppLayout>
    <div class="tasks-view">
      <!-- Header Actions -->
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          创建任务
        </el-button>
        <el-button @click="fetchTasks">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>

      <!-- Tasks List -->
      <div v-if="taskStore.loading" class="loading-container">
        <LoadingSpinner text="加载任务中..." />
      </div>

      <div v-else-if="taskStore.tasks.length === 0" class="empty-container">
        <EmptyState
          description="暂无任务"
          action-text="创建任务"
          :action-handler="() => showCreateDialog = true"
        />
      </div>

      <div v-else class="tasks-container">
        <div class="tasks-grid">
          <div
            v-for="task in taskStore.tasks"
            :key="task.id"
            class="task-card"
            :class="`task-card--${task.priority.toLowerCase()}`"
          >
            <div class="task-header">
              <div class="task-priority">
                <el-tag :type="getPriorityType(task.priority)" size="small">
                  {{ getPriorityLabel(task.priority) }}
                </el-tag>
              </div>
              <div class="task-status">
                <el-tag :type="getStatusType(task.status)" size="small">
                  {{ getStatusLabel(task.status) }}
                </el-tag>
              </div>
            </div>

            <div class="task-content">
              <h3 class="task-title">{{ task.title }}</h3>
              <p v-if="task.description" class="task-description">{{ task.description }}</p>

              <div class="task-meta">
                <div class="task-assignee">
                  <el-icon><UserIcon /></el-icon>
                  {{ task.assignee_name || '未分配' }}
                </div>
                <div v-if="task.due_date" class="task-due-date">
                  <el-icon><Calendar /></el-icon>
                  {{ formatDate(task.due_date) }}
                </div>
                <div class="task-created">
                  创建于 {{ formatDate(task.created_at) }}
                </div>
              </div>
            </div>

            <div class="task-actions">
              <el-button size="small" @click="editTask(task)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteTask(task)">删除</el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- Create/Edit Task Dialog -->
      <el-dialog
        v-model="showCreateDialog"
        :title="editingTask ? '编辑任务' : '创建任务'"
        width="600px"
      >
        <el-form
          ref="taskFormRef"
          :model="taskForm"
          :rules="taskRules"
          label-width="80px"
        >
          <el-form-item label="标题" prop="title">
            <el-input v-model="taskForm.title" placeholder="输入任务标题" />
          </el-form-item>

          <el-form-item label="描述">
            <el-input
              v-model="taskForm.description"
              type="textarea"
              :rows="3"
              placeholder="输入任务描述（可选）"
            />
          </el-form-item>

          <el-form-item label="优先级" prop="priority">
            <el-select v-model="taskForm.priority" placeholder="选择优先级">
              <el-option label="高" value="high" />
              <el-option label="中" value="medium" />
              <el-option label="低" value="low" />
            </el-select>
          </el-form-item>

          <el-form-item label="状态" prop="status">
            <el-select v-model="taskForm.status" placeholder="选择状态">
              <el-option label="待处理" value="pending" />
              <el-option label="进行中" value="in_progress" />
              <el-option label="已完成" value="completed" />
            </el-select>
          </el-form-item>

          <el-form-item label="分配给">
            <el-select
              v-model="taskForm.assigned_to"
              placeholder="选择负责人"
              clearable
              filterable
            >
              <el-option
                v-for="user in allUsers"
                :key="user.id"
                :label="`${user.full_name || user.username} (${user.role})`"
                :value="user.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="截止日期">
            <el-date-picker
              v-model="taskForm.due_date"
              type="datetime"
              placeholder="选择截止日期"
              format="YYYY-MM-DD HH:mm:ss"
              value-format="YYYY-MM-DD HH:mm:ss"
            />
          </el-form-item>
        </el-form>

        <template #footer>
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" :loading="taskStore.loading" @click="handleTaskSubmit">
            {{ editingTask ? '更新' : '创建' }}
          </el-button>
        </template>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Refresh, User as UserIcon, Calendar } from '@element-plus/icons-vue';
import type { FormInstance, FormRules } from 'element-plus';
import type { Task, CreateTaskParams, User } from '@/types';
import AppLayout from '@/components/layout/AppLayout.vue';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import { useTaskStore, useUserStore } from '@/store';

const taskStore = useTaskStore();
const userStore = useUserStore();

const showCreateDialog = ref(false);
const editingTask = ref<Task | null>(null);
const taskFormRef = ref<FormInstance>();

const taskForm = reactive<CreateTaskParams>({
  title: '',
  description: '',
  priority: 'medium',
  status: 'pending',
  assigned_to: undefined,
  due_date: undefined
});

const taskRules: FormRules = {
  title: [{ required: true, message: '请输入任务标题', trigger: 'blur' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
};

const allUsers = computed(() => userStore.users);

const getPriorityLabel = (priority: string) => {
  const labelMap = {
    high: '高',
    medium: '中',
    low: '低'
  };
  return labelMap[priority as keyof typeof labelMap] || priority;
};

const getPriorityType = (priority: string) => {
  const typeMap = {
    high: 'danger',
    medium: 'warning',
    low: 'info'
  };
  return typeMap[priority as keyof typeof typeMap] || 'info';
};

const getStatusLabel = (status: string) => {
  const labelMap = {
    pending: '待处理',
    in_progress: '进行中',
    completed: '已完成'
  };
  return labelMap[status as keyof typeof labelMap] || status;
};

const getStatusType = (status: string) => {
  const typeMap = {
    pending: 'warning',
    in_progress: 'primary',
    completed: 'success'
  };
  return typeMap[status as keyof typeof typeMap] || 'info';
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString('zh-CN');
};

const fetchTasks = async () => {
  await taskStore.fetchTasks();
};

const editTask = (task: Task) => {
  editingTask.value = task;
  Object.assign(taskForm, {
    title: task.title,
    description: task.description,
    priority: task.priority,
    status: task.status,
    assigned_to: task.assigned_to,
    due_date: task.due_date
  });
  showCreateDialog.value = true;
};

const deleteTask = async (task: Task) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除任务 "${task.title}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );

    await taskStore.deleteTask(task.id);
    ElMessage.success('任务删除成功');
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('任务删除失败');
    }
  }
};

const handleTaskSubmit = async () => {
  if (!taskFormRef.value) return;

  try {
    await taskFormRef.value.validate();

    if (editingTask.value) {
      await taskStore.updateTask(editingTask.value.id, taskForm);
      ElMessage.success('任务更新成功');
    } else {
      await taskStore.createTask(taskForm);
      ElMessage.success('任务创建成功');
    }

    showCreateDialog.value = false;
    resetTaskForm();
    editingTask.value = null;
  } catch (error) {
    // Validation error
  }
};

const resetTaskForm = () => {
  Object.assign(taskForm, {
    title: '',
    description: '',
    priority: 'medium',
    status: 'pending',
    assigned_to: undefined,
    due_date: undefined
  });
};

// Watch for dialog close to reset form
const stopWatchingCreateDialog = watch(showCreateDialog, (newValue) => {
  if (!newValue) {
    resetTaskForm();
    editingTask.value = null;
  }
});

onMounted(async () => {
  await Promise.all([
    fetchTasks(),
    userStore.fetchUsers()
  ]);
});

onUnmounted(() => {
  stopWatchingCreateDialog();
});
</script>

<style scoped>
.tasks-view {
  @apply space-y-6;
}

.header-actions {
  @apply flex justify-between items-center;
}

.tasks-container {
  @apply space-y-6;
}

.tasks-grid {
  @apply grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6;
}

.task-card {
  @apply bg-white rounded-lg shadow-sm border p-6;
}

.task-card--high {
  @apply border-red-200;
}

.task-card--medium {
  @apply border-yellow-200;
}

.task-card--low {
  @apply border-blue-200;
}

.task-header {
  @apply flex items-center justify-between mb-4;
}

.task-content {
  @apply mb-4;
}

.task-title {
  @apply text-lg font-semibold text-gray-800 mb-2;
}

.task-description {
  @apply text-gray-600 mb-3;
}

.task-meta {
  @apply space-y-2 text-sm text-gray-500;
}

.task-assignee,
.task-due-date,
.task-created {
  @apply flex items-center;
}

.task-assignee .el-icon,
.task-due-date .el-icon,
.task-created .el-icon {
  @apply mr-1;
}

.task-actions {
  @apply flex justify-end space-x-2;
}

.loading-container,
.empty-container {
  @apply py-12;
}
</style>