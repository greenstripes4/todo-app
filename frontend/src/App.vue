<script setup>
import { ref } from 'vue';
import Dashboard from './features/dashboard/Dashboard.vue';
import AuthLayout from './features/auth/AuthLayout.vue';

// Access the environment variable
const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT;

// State to track if the user is logged in
const isLoggedIn = ref(localStorage.getItem('access_token') !== null);

// logout function
const logout = () => {
  localStorage.removeItem('access_token');
  isLoggedIn.value = false;
};

const handleLogin = () => {
  isLoggedIn.value = true;
};
</script>

<template>
  <main class="full-screen">
    <Dashboard v-if="isLoggedIn" @logout="logout" class="full-screen" />
    <AuthLayout v-else :API_ENDPOINT="API_ENDPOINT" @login="handleLogin" class="auth-layout-container" />
  </main>
</template>

<style scoped>
.full-screen {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

main {
  width: 100vw;
  height: 100vh;
  display: flex; /* Added */
  justify-content: center; /* Added */
  align-items: center; /* Added */
}

.auth-layout-container {
  /* width: 100vw; Removed */
  /* height: 100vh; Removed */
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
