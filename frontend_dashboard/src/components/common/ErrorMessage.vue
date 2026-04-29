<template>
  <div class="error-message">
    <el-alert
      :title="title"
      :description="message"
      type="error"
      show-icon
      :closable="closable"
      @close="$emit('close')"
    />
  </div>
</template>

<script setup lang="ts">
interface Props {
  title?: string;
  message: string;
  closable?: boolean;
}

withDefaults(defineProps<Props>(), {
  title: '错误',
  closable: true
});

defineEmits<{
  close: [];
}>();
</script>

<style scoped>
.error-message {
  @apply my-4;
}
</style>