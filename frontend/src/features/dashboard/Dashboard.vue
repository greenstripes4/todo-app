<template>
  <div class="dashboard">
    <DashboardNavigation
      class="dashboard-navigation"
      @logout="$emit('logout')"
      @show-profile="showProfile = true"
      @show-manage-users="showManageUsers = true"
    />
    <div class="dashboard-content">
      <ProfileView v-if="showProfile" />
      <ManageUsersView v-if="showManageUsers" />
      <template v-else-if="!showProfile">
        <h1>Welcome!</h1>
        <p>This is your dashboard.</p>
        <!-- You can add more dashboard content here -->
      </template>
    </div>
  </div>
</template>

<script setup>
import DashboardNavigation from './DashboardNavigation.vue';
import ProfileView from './ProfileView.vue';
import ManageUsersView from './ManageUsersView.vue';
import { ref } from 'vue';

defineEmits(['logout']);

const showProfile = ref(false);
const showManageUsers = ref(false);
</script>

<style scoped>
.dashboard {
  display: flex;
  height: 100%;
  width: 100%;
}

.dashboard-navigation {
  width: 200px;
  flex-shrink: 0;
  position: fixed;
  top: 0;
  left: 0;
  height: 100vh;
  background-color: #333;
  color: #fff;
  border-right: 1px solid #555;
  box-shadow: 2px 0 5px rgba(0, 0, 0, 0.2);
  padding: 20px;
}

.dashboard-content {
  flex-grow: 1;
  padding: 20px;
  height: 100%;
  overflow-y: auto;
  margin-left: 200px;
}

h1 {
  margin-bottom: 10px;
}
</style>
