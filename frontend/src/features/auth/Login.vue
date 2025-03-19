<script setup>
import { ref } from 'vue';

const props = defineProps({
  API_ENDPOINT: String,
});

const emit = defineEmits(['login']);

// Form data for login
const loginFormData = ref({
  username: '',
  password: '',
});

// Function to handle user login
const handleLogin = async () => {
  try {
    const response = await fetch(`${props.API_ENDPOINT}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(loginFormData.value),
    });

    if (response.ok) {
      const data = await response.json();
      // Store the access token (you might want to use a more secure method)
      localStorage.setItem('access_token', data.access_token);
      emit('login');
      console.log('Login successful:', data);
      // Clear form data after successful login
      loginFormData.value.username = '';
      loginFormData.value.password = '';
    } else {
      const errorData = await response.json();
      emit('error', errorData.message || 'Login failed');
      console.error('Login failed:', errorData);
    }
  } catch (error) {
    emit('error', 'An error occurred during login.');
    console.error('Login error:', error);
  }
};
</script>

<template>
  <h2>Login</h2>
  <form @submit.prevent="handleLogin">
    <div>
      <label for="login-username">Username:</label>
      <input type="text" id="login-username" v-model="loginFormData.username" required />
    </div>
    <div>
      <label for="login-password">Password:</label>
      <input type="password" id="login-password" v-model="loginFormData.password" required />
    </div>
    <button type="submit">Login</button>
    <p>
      Don't have an account?
      <a href="#" @click="$emit('toggle-form')">Register</a>
    </p>
  </form>
</template>
