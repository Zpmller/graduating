<template>
  <div class="empty-state">
    <el-empty
      :image="image"
      :description="description"
    >
      <template v-if="actionText && actionHandler" #default>
        <el-button type="primary" @click="actionHandler">
          {{ actionText }}
        </el-button>
      </template>
    </el-empty>
  </div>
</template>

<script setup lang="ts">
interface Props {
  description?: string;
  image?: string;
  actionText?: string;
  actionHandler?: () => void;
}

withDefaults(defineProps<Props>(), {
  description: '暂无数据',
  image: undefined
});
</script>

<style scoped>
.empty-state {
  padding: 2rem 0;
}
</style>
