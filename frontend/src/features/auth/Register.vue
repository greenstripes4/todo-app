<script setup>
import { ref } from 'vue';

const props = defineProps({
  API_ENDPOINT: String,
});

const emit = defineEmits(['register']);

// Form data for registration
const registerFormData = ref({
  username: '',
  password: '',
  confirmPassword: '',
});

// Function to handle user registration
const handleRegister = async () => {
  // Check if passwords match
  if (registerFormData.value.password !== registerFormData.value.confirmPassword) {
    emit('error', 'Passwords do not match.');
    return; // Stop the registration process
  }

  try {
    const response = await fetch(`${props.API_ENDPOINT}/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: registerFormData.value.username,
        password: registerFormData.value.password,
      }),
    });

    if (response.ok) {
      const data = await response.json();
      console.log('Registration successful:', data);
      // Clear form data after successful registration
      registerFormData.value.username = '';
      registerFormData.value.password = '';
      registerFormData.value.confirmPassword = '';
      emit('register');
    } else {
      const errorData = await response.json();
      emit('error', errorData.message || 'Registration failed');
      console.error('Registration failed:', errorData);
    }
  } catch (error) {
    emit('error', 'An error occurred during registration.');
    console.error('Registration error:', error);
  }
};
</script>

<template>
  <h2>Register</h2>
  <form @submit.prevent="handleRegister">
    <div>
      <label for="register-username">Username:</label>
      <input type="text" id="register-username" v-model="registerFormData.username" required />
    </div>
    <div>
      <label for="register-password">Password:</label>
      <input type="password" id="register-password" v-model="registerFormData.password" required />
    </div>
    <div>
      <label for="register-confirm-password">Confirm Password:</label>
      <input type="password" id="register-confirm-password" v-model="registerFormData.confirmPassword" required />
    </div>
    <button type="submit">Register</button>
    <p>
      Already have an account?
      <a href="#" @click="$emit('toggle-form')">Login</a>
    </p>
  </form>
</template>
