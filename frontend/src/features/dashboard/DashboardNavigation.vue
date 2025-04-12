<template>
  <nav class="dashboard-navigation">
    <NavigationGroup title="User Settings" :is-open="true">
      <NavigationItem label="Your Accounts" @click="$emit('show-user-accounts')" />
      <NavigationItem label="Your Workflows" @click="$emit('show-user-workflows')" />
    </NavigationGroup>
    <NavigationGroup v-if="isAdmin" title="Administration" :is-open="true">
      <NavigationItem label="Manage Users" @click="$emit('show-manage-users')" />
      <NavigationItem label="Manage Workflows" @click="$emit('show-manage-workflows')" />
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

// Add 'show-user-workflows' to the list of emitted events
defineEmits([
  'logout',
  'show-profile',
  'show-manage-users',
  'show-user-accounts',
  'show-manage-workflows',
  'show-user-workflows',
]);

const isAdmin = ref(false);

onMounted(() => {
  const token = localStorage.getItem('access_token');
  if (token) {
    try {
      const decodedToken = jwtDecode(token);
      isAdmin.value = decodedToken.role === 'admin';
    } catch (error) {
      console.error('Error decoding token:', error);
      // Handle token error, e.g., redirect to login
    }
  }
});
</script>

<style scoped>
.dashboard-navigation {
  width: 250px; /* Ensure this matches the margin-left in Dashboard.vue */
  background-color: #f0f0f0; /* Example background */
  padding: 20px;
  border-right: 1px solid #ccc;
  height: 100%;
  /* Remove fixed positioning if it's inside the flex container */
}
</style>
