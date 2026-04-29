<template>
  <AppLayout>
    <div class="users-view">
      <!-- Header Actions -->
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          添加用户
        </el-button>
        <el-button @click="fetchUsers">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>

      <!-- Users Table -->
      <div class="table-section">
        <el-table
          :data="userStore.users"
          :loading="userStore.loading"
          stripe
          style="width: 100%"
        >
          <el-table-column prop="username" label="用户名" width="150" />
          <el-table-column prop="full_name" label="姓名" width="150" />
          <el-table-column prop="role" label="角色" width="120">
            <template #default="scope">
              <el-tag :type="getRoleType(scope.row.role)">
                {{ getRoleLabel(scope.row.role) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="is_active" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="scope.row.is_active ? 'success' : 'danger'">
                {{ scope.row.is_active ? '激活' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="200">
            <template #default="scope">
              <el-button size="small" @click="editUser(scope.row)">编辑</el-button>
              <el-button
                size="small"
                :type="scope.row.is_active ? 'warning' : 'success'"
                @click="toggleUserStatus(scope.row)"
              >
                {{ scope.row.is_active ? '禁用' : '激活' }}
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="deleteUser(scope.row)"
                :disabled="scope.row.id === authStore.user?.id"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Create/Edit User Dialog -->
      <el-dialog
        v-model="showCreateDialog"
        :title="editingUser ? '编辑用户' : '添加用户'"
        width="500px"
      >
        <el-form
          ref="userFormRef"
          :model="userForm"
          :rules="userRules"
          label-width="80px"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="userForm.username"
              placeholder="输入用户名"
              :disabled="!!editingUser"
            />
          </el-form-item>

          <el-form-item label="姓名">
            <el-input v-model="userForm.full_name" placeholder="输入姓名（可选）" />
          </el-form-item>

          <el-form-item v-if="!editingUser" label="密码" prop="password">
            <el-input
              v-model="userForm.password"
              type="password"
              placeholder="输入密码"
              show-password
            />
          </el-form-item>

          <el-form-item label="角色" prop="role">
            <el-select v-model="userForm.role" placeholder="选择角色">
              <el-option label="管理员" value="admin" />
              <el-option label="操作员" value="operator" />
              <el-option label="查看者" value="viewer" />
            </el-select>
          </el-form-item>

          <el-form-item v-if="editingUser" label="状态">
            <el-switch
              v-model="userForm.is_active"
              active-text="激活"
              inactive-text="禁用"
            />
          </el-form-item>
        </el-form>

        <template #footer>
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" :loading="userStore.loading" @click="handleUserSubmit">
            {{ editingUser ? '更新' : '添加' }}
          </el-button>
        </template>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Refresh } from '@element-plus/icons-vue';
import type { FormInstance, FormRules } from 'element-plus';
import type { User, CreateUserParams, UpdateUserParams } from '@/types';
import AppLayout from '@/components/layout/AppLayout.vue';
import { useUserStore, useAuthStore } from '@/store';

const userStore = useUserStore();
const authStore = useAuthStore();

const showCreateDialog = ref(false);
const editingUser = ref<User | null>(null);
const userFormRef = ref<FormInstance>();

const userForm = reactive<CreateUserParams & { is_active?: boolean }>({
  username: '',
  full_name: '',
  password: '',
  role: 'viewer',
  is_active: true
});

const userRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度应为3-20个字符', trigger: 'blur' }
  ],
  password: editingUser.value ? [] : [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6个字符', trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
};

const getRoleLabel = (role: string) => {
  const labelMap = {
    admin: '管理员',
    operator: '操作员',
    viewer: '查看者'
  };
  return labelMap[role as keyof typeof labelMap] || role;
};

const getRoleType = (role: string) => {
  const typeMap = {
    admin: 'danger',
    operator: 'primary',
    viewer: 'info'
  };
  return typeMap[role as keyof typeof typeMap] || 'info';
};

const fetchUsers = async () => {
  await userStore.fetchUsers();
};

const editUser = (user: User) => {
  editingUser.value = user;
  Object.assign(userForm, {
    username: user.username,
    full_name: user.full_name,
    role: user.role,
    is_active: user.is_active
  });
  showCreateDialog.value = true;
};

const toggleUserStatus = async (user: User) => {
  try {
    await userStore.updateUser(user.id, { is_active: !user.is_active });
    ElMessage.success('用户状态更新成功');
  } catch (error) {
    ElMessage.error('用户状态更新失败');
  }
};

const deleteUser = async (user: User) => {
  if (user.id === authStore.user?.id) {
    ElMessage.warning('不能删除当前登录用户');
    return;
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除用户 "${user.username}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );

    await userStore.deleteUser(user.id);
    ElMessage.success('用户删除成功');
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('用户删除失败');
    }
  }
};

const handleUserSubmit = async () => {
  if (!userFormRef.value) return;

  try {
    await userFormRef.value.validate();

    if (editingUser.value) {
      const updateData: UpdateUserParams = {
        full_name: userForm.full_name,
        role: userForm.role,
        is_active: userForm.is_active
      };
      await userStore.updateUser(editingUser.value.id, updateData);
      ElMessage.success('用户更新成功');
    } else {
      const createData: CreateUserParams = {
        username: userForm.username,
        full_name: userForm.full_name,
        password: userForm.password,
        role: userForm.role
      };
      await userStore.createUser(createData);
      ElMessage.success('用户创建成功');
    }

    showCreateDialog.value = false;
    resetUserForm();
    editingUser.value = null;
  } catch (error) {
    // Validation error
  }
};

const resetUserForm = () => {
  Object.assign(userForm, {
    username: '',
    full_name: '',
    password: '',
    role: 'viewer',
    is_active: true
  });
};

// Watch for dialog close to reset form
const stopWatchingCreateDialog = watch(showCreateDialog, (newValue) => {
  if (!newValue) {
    resetUserForm();
    editingUser.value = null;
  }
});

onMounted(async () => {
  await fetchUsers();
});

onUnmounted(() => {
  stopWatchingCreateDialog();
});
</script>

<style scoped>
.users-view {
  @apply space-y-6;
}

.header-actions {
  @apply flex justify-between items-center;
}

.table-section {
  @apply bg-white rounded-lg shadow-sm p-6;
}
</style>