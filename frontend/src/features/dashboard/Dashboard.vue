<template>
  <div class="dashboard">
    <DashboardNavigation
      class="dashboard-navigation"
      @logout="$emit('logout')"
      @show-profile="setActiveView('profile')"
      @show-manage-users="setActiveView('manageUsers')"
      @show-manage-workflows="setActiveView('manageWorkflows')"
      @show-user-accounts="setActiveView('userAccounts')"
      @show-user-workflows="setActiveView('userWorkflows')"
      @show-default="setActiveView(null)"
    />
    <div class="dashboard-content">
      <!-- Conditionally render views based on activeView -->
      <ProfileView v-if="activeView === 'profile'" />
      <ManageUsersView v-else-if="activeView === 'manageUsers'" />
      <ManageWorkflowsView v-else-if="activeView === 'manageWorkflows'" />
      <UserAccountsView v-else-if="activeView === 'userAccounts'" />
      <UserWorkflowsView v-else-if="activeView === 'userWorkflows'" /> <!-- Render UserWorkflowsView -->
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
import ManageWorkflowsView from './ManageWorkflowsView.vue';
import UserAccountsView from './UserAccountsView.vue';
import UserWorkflowsView from './UserWorkflowsView.vue'; // <-- Import UserWorkflowsView

defineEmits(['logout']);

// Single ref to track the active view component's identifier
const activeView = ref(null); // null represents the default dashboard content

// Function to update the active view
const setActiveView = (viewName) => {
  activeView.value = viewName;
};

</script>

<style scoped>
/* Styles remain unchanged as requested */
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
  margin-left: 200px; /* Add this back since navigation is position: fixed */

}

h1 {
  margin-bottom: 10px;
}
</style>
