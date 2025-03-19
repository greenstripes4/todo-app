<template>
  <nav class="dashboard-navigation">
    <NavigationGroup title="User Settings" :is-open="true">
      <NavigationItem label="Your Profile" />
      <NavigationItem label="Your Accounts" />
      <NavigationItem label="Your Workflows" />
    </NavigationGroup>
    <NavigationGroup title="Account" :is-open="true">
      <NavigationItem label="Sign Out" @click="$emit('logout')" />
    </NavigationGroup>
  </nav>
</template>

<script setup>
import NavigationGroup from './NavigationGroup.vue';
import NavigationItem from './NavigationItem.vue';

defineEmits(['logout']);
</script>

<style scoped>
.dashboard-navigation {
  width: 250px;
  background-color: #f0f0f0;
  padding: 20px;
  border-right: 1px solid #ccc;
  height: 100%;
}
</style>
