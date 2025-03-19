<template>
  <li class="navigation-item">
    <a href="#" @click="$emit('click')">{{ label }}</a>
  </li>
</template>

<script setup>
defineProps({
  label: {
    type: String,
    required: true,
  },
});

defineEmits(['click']);
</script>

<style scoped>
.navigation-item {
  padding: 10px;
}
</style>
