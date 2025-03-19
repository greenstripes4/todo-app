<script setup>
import { ref } from 'vue';
import Login from './Login.vue';
import Register from './Register.vue';

const props = defineProps({
  API_ENDPOINT: String,
});

const emit = defineEmits(['login']);

// State to show registration or login form
const showRegister = ref(false);

// Error message state
const errorMessage = ref('');

// Function to toggle between login and registration forms
const toggleForm = () => {
  showRegister.value = !showRegister.value;
  errorMessage.value = ''; // Clear error message on form toggle
};

const handleLogin = () => {
  emit('login');
};

const handleError = (message) => {
  errorMessage.value = message;
};

const handleRegister = () => {
  toggleForm();
};
</script>

<template>
  <div v-if="showRegister">
    <Register :API_ENDPOINT="props.API_ENDPOINT" @register="handleRegister" @toggle-form="toggleForm" @error="handleError" />
  </div>
  <div v-else>
    <Login :API_ENDPOINT="props.API_ENDPOINT" @login="handleLogin" @toggle-form="toggleForm" @error="handleError" />
  </div>
  <div v-if="errorMessage" class="error-message">
    {{ errorMessage }}
  </div>
</template>

<style scoped>
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
</style>
