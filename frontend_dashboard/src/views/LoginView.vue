<template>
  <div class="login-view">
    <ParticleBackdrop :quiet="true" />
    <div class="login-container">
      <div class="login-brand">
        <div class="brand-emblem">
          <el-icon><User /></el-icon>
        </div>
        <h1 class="system-title">矿山热工作业安全监控系统</h1>
        <p class="system-subtitle">智能监控 · 实时预警 · 安全生产</p>
      </div>

      <div class="login-card">
        <div class="login-header">
          <h2 class="login-title">用户登录</h2>
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
import ParticleBackdrop from '@/components/common/ParticleBackdrop.vue';
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
  position: relative;
  display: flex;
  min-height: 100vh;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 24px;
  background: var(--mine-bg-deep);
}

.login-container {
  position: relative;
  z-index: 1;
  display: grid;
  width: min(100%, 940px);
  grid-template-columns: minmax(0, 1.05fr) 420px;
  gap: 28px;
  align-items: center;
}

.login-brand {
  min-height: 390px;
  padding: 34px;
  border: 1px solid rgba(126, 211, 255, 0.16);
  border-radius: 8px;
  background:
    linear-gradient(115deg, rgba(2, 8, 18, 0.18), rgba(2, 8, 18, 0.72)),
    linear-gradient(180deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.012));
  box-shadow: var(--shadow-glass);
  backdrop-filter: blur(14px);
}

.brand-emblem {
  display: flex;
  width: 86px;
  height: 86px;
  align-items: center;
  justify-content: center;
  margin-bottom: 34px;
  border: 1px solid rgba(28, 199, 255, 0.62);
  border-radius: 8px;
  color: #a4f2ff;
  background: rgba(28, 199, 255, 0.11);
  box-shadow: 0 0 34px rgba(28, 199, 255, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.13);
  font-size: 44px;
}

.system-title {
  max-width: 500px;
  margin: 0 0 14px;
  color: #ffffff;
  font-size: clamp(28px, 4vw, 42px);
  font-weight: 900;
  line-height: 1.16;
  letter-spacing: 0;
}

.system-subtitle {
  margin: 0;
  color: #80ddff;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0;
}

.login-card {
  padding: 28px;
  border: 1px solid rgba(126, 211, 255, 0.26);
  border-radius: 8px;
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.09), rgba(255, 255, 255, 0.02)),
    rgba(8, 29, 47, 0.78);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.42), 0 0 32px rgba(28, 199, 255, 0.12);
  backdrop-filter: blur(20px) saturate(135%);
}

.login-header {
  margin-bottom: 26px;
  text-align: center;
}

.login-title {
  margin: 0 0 8px;
  color: #ffffff;
  font-size: 24px;
  font-weight: 850;
  letter-spacing: 0;
}

.login-subtitle {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 650;
}

.login-btn {
  width: 100%;
  min-height: 42px;
}

.login-card :deep(.el-form-item) {
  margin-bottom: 20px;
}

@media (max-width: 860px) {
  .login-container {
    grid-template-columns: 1fr;
  }

  .login-brand {
    min-height: auto;
    padding: 24px;
  }
}

@media (max-width: 520px) {
  .login-view {
    padding: 14px;
  }

  .login-card {
    padding: 20px;
  }
}
</style>
