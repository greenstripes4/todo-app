<script setup>
import { ref } from 'vue';
import Dashboard from './Dashboard.vue';

// Access the environment variable
const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT;

// State to track if the user is logged in
const isLoggedIn = ref(false);
// State to show registration or login form
const showRegister = ref(false);

// Form data for login and registration
const loginFormData = ref({
  username: '',
  password: '',
});

const registerFormData = ref({
  username: '',
  password: '',
  confirmPassword: '', // Add confirmPassword field
});

// Error message state
const errorMessage = ref('');

// Function to handle user login
const handleLogin = async () => {
  errorMessage.value = ''; // Clear any previous error messages
  try {
    const response = await fetch(`${API_ENDPOINT}/login`, {
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
      isLoggedIn.value = true;
      console.log('Login successful:', data);
      // Clear form data after successful login
      loginFormData.value.username = '';
      loginFormData.value.password = '';
    } else {
      const errorData = await response.json();
      errorMessage.value = errorData.message || 'Login failed';
      console.error('Login failed:', errorData);
    }
  } catch (error) {
    errorMessage.value = 'An error occurred during login.';
    console.error('Login error:', error);
  }
};

// Function to handle user registration
const handleRegister = async () => {
  errorMessage.value = ''; // Clear any previous error messages

  // Check if passwords match
  if (registerFormData.value.password !== registerFormData.value.confirmPassword) {
    errorMessage.value = 'Passwords do not match.';
    return; // Stop the registration process
  }

  try {
    const response = await fetch(`${API_ENDPOINT}/register`, {
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
      // Switch to login form after successful registration
      showRegister.value = false;
      // Clear form data after successful registration
      registerFormData.value.username = '';
      registerFormData.value.password = '';
      registerFormData.value.confirmPassword = '';
    } else {
      const errorData = await response.json();
      errorMessage.value = errorData.message || 'Registration failed';
      console.error('Registration failed:', errorData);
    }
  } catch (error) {
    errorMessage.value = 'An error occurred during registration.';
    console.error('Registration error:', error);
  }
};

// Function to toggle between login and registration forms
const toggleForm = () => {
  showRegister.value = !showRegister.value;
  errorMessage.value = ''; // Clear error message on form toggle
};

// logout function
const logout = () => {
  localStorage.removeItem('access_token');
  isLoggedIn.value = false;
}

</script>

<template>
  <main>
    <div v-if="isLoggedIn">
      <Dashboard />
      <button @click="logout">Logout</button>
    </div>
    <div v-else>
      <div v-if="showRegister">
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
            <a href="#" @click="toggleForm">Login</a>
          </p>
        </form>
      </div>
      <div v-else>
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
            <a href="#" @click="toggleForm">Register</a>
          </p>
        </form>
      </div>
      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>
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

form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 300px;
}

.error-message {
  color: red;
  margin-top: 10px;
}

.dashboard {
  width: 100%;
  height: 100%;
}
</style>
