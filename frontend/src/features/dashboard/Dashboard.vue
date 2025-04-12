<template>
  <div class="dashboard">
    <DashboardNavigation
      class="dashboard-navigation"
      @logout="$emit('logout')"
      @show-profile="setActiveView('profile')"
      @show-manage-users="setActiveView('manageUsers')"
      @show-default="setActiveView(null)"
    />
    <div class="dashboard-content">
      <!-- Conditionally render views based on activeView -->
      <ProfileView v-if="activeView === 'profile'" />
      <ManageUsersView v-else-if="activeView === 'manageUsers'" />
      <!-- Show default content only when no specific view is active -->
      <template v-else>
        <h1>Welcome!</h1>
        <p>This is your dashboard.</p>
        <!-- You can add more dashboard content here -->
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import DashboardNavigation from './DashboardNavigation.vue';
import ProfileView from './ProfileView.vue';
import ManageUsersView from './ManageUsersView.vue';

defineEmits(['logout']);

// Single ref to track the active view component's identifier
const activeView = ref(null); // null represents the default dashboard content

// Function to update the active view
const setActiveView = (viewName) => {
  activeView.value = viewName;
};

// Optional: If you need a way to explicitly go back to the default view
// const showDefaultView = () => {
//   setActiveView(null);
// };
</script>

<style scoped>
.dashboard {
  display: flex;
  height: 100%;
  width: 100%;
  overflow: hidden;
}

.dashboard-navigation {
  width: 200px; /* Fixed width for the navigation */
  flex-shrink: 0; /* Prevent navigation from shrinking */
  position: fixed;
  top: 0;
  left: 0;
  height: 100%;
  background-color: #333;
  color: #fff;
  border-right: 1px solid #555;
  box-shadow: 2px 0 5px rgba(0, 0, 0, 0.2);
  padding: 20px;
  overflow-y: auto; /* Allow scrolling within nav if content overflows */
}

.dashboard-content {
  flex-grow: 1; /* Allow content area to take remaining space */
  padding: 20px;
  height: 100%; /* Take full height of the flex container */
  overflow-y: auto; /* Allow content area to scroll if needed */
  /* Removed margin-left as flexbox handles positioning */
  /* margin-left: 200px; */
}

h1 {
  margin-bottom: 10px;
}
</style>
