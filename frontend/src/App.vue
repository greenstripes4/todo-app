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
  <main>
    <div v-if="isLoggedIn">
      <Dashboard />
      <button @click="logout">Logout</button>
    </div>
    <div v-else>
      <AuthLayout :API_ENDPOINT="API_ENDPOINT" @login="handleLogin" />
    </div>
  </main>
</template>

<style scoped>
main {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
}
</style>
