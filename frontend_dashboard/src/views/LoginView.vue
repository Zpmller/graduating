<template>
  <div class="login-view">
    <div class="login-container">
      <div class="login-card">
        <div class="login-header">
          <h1 class="login-title">矿山热工作业安全监控系统</h1>
          <p class="login-subtitle">请登录您的账户</p>
        </div>

        <el-form
          ref="loginFormRef"
          :model="form"
          :rules="rules"
          label-position="top"
          @submit.prevent="handleLogin"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              :prefix-icon="User"
              size="large"
            />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              size="large"
              show-password
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="authStore.loading"
              native-type="submit"
              class="login-btn"
            >
              登录
            </el-button>
          </el-form-item>
        </el-form>

        <ErrorMessage
          v-if="authStore.error"
          :message="authStore.error"
          @close="authStore.error = null"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { User, Lock } from '@element-plus/icons-vue';
import type { FormInstance, FormRules } from 'element-plus';
import { useAuthStore } from '@/store';
import ErrorMessage from '@/components/common/ErrorMessage.vue';

const router = useRouter();
const authStore = useAuthStore();

const loginFormRef = ref<FormInstance>();

const form = reactive({
  username: '',
  password: ''
});

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
};

const handleLogin = async () => {
  if (!loginFormRef.value) return;

  try {
    await loginFormRef.value.validate();
    const success = await authStore.login(form);

    if (success) {
      ElMessage.success('登录成功');
      router.push('/');
    }
  } catch (error) {
    // Validation error, do nothing
  }
};

onMounted(() => {
  // Clear any existing auth state
  authStore.logout();
});
</script>

<style scoped>
.login-view {
  @apply min-h-screen bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center p-4;
}

.login-container {
  @apply w-full max-w-md;
}

.login-card {
  @apply bg-white rounded-lg shadow-xl p-8;
}

.login-header {
  @apply text-center mb-8;
}

.login-title {
  @apply text-2xl font-bold text-gray-800 mb-2;
}

.login-subtitle {
  @apply text-gray-600;
}

.login-btn {
  @apply w-full;
}
</style>