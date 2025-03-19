<template>
  <nav class="dashboard-navigation">
    <NavigationGroup title="User Settings" :is-open="true">
      <NavigationItem label="Your Accounts" />
      <NavigationItem label="Your Workflows" />
    </NavigationGroup>
    <NavigationGroup v-if="isAdmin" title="Administration" :is-open="true">
      <NavigationItem label="Manage Users" @click="$emit('show-manage-users')" />
      <NavigationItem label="Manage Workflows" />
    </NavigationGroup>
    <NavigationGroup title="Account" :is-open="true">
      <NavigationItem label="Your Profile" @click="$emit('show-profile')" />
      <NavigationItem label="Sign Out" @click="$emit('logout')" />
    </NavigationGroup>
  </nav>
</template>

<script setup>
import NavigationGroup from './NavigationGroup.vue';
import NavigationItem from './NavigationItem.vue';
import { ref, onMounted } from 'vue';
import { jwtDecode } from 'jwt-decode';

defineEmits(['logout', 'show-profile', 'show-manage-users']);

const isAdmin = ref(false);

onMounted(() => {
  const token = localStorage.getItem('access_token');
  if (token) {
    try {
      const decodedToken = jwtDecode(token);
      if (decodedToken.role === 'admin') {
        isAdmin.value = true;
      }
    } catch (error) {
      console.error('Error decoding token:', error);
    }
  }
});
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
