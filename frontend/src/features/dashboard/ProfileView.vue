<template>
  <div class="profile-view-container">
    <h2>Your Profile</h2>
    <form @submit.prevent="updatePassword">
      <div class="form-group">
        <label for="oldPassword">Old Password:</label>
        <input type="password" id="oldPassword" v-model="oldPassword" required />
      </div>
      <div class="form-group">
        <label for="newPassword">New Password:</label>
        <input type="password" id="newPassword" v-model="newPassword" required />
      </div>
      <div class="form-group">
        <label for="confirmPassword">Confirm Password:</label>
        <input type="password" id="confirmPassword" v-model="confirmPassword" required />
      </div>
      <div v-if="passwordMismatch" class="error-message">Passwords do not match.</div>
      <div v-if="updateError" class="error-message">{{ updateError }}</div>
      <div v-if="updateSuccess" class="success-message">Password updated successfully!</div>
      <button type="submit" class="update-button" :disabled="isUpdating">
        <span v-if="isUpdating">Updating...</span>
        <span v-else>Update Password</span>
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

const oldPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const passwordMismatch = ref(false);
const updateError = ref('');
const updateSuccess = ref(false);
const isUpdating = ref(false);

const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT;

const updatePassword = async () => {
  passwordMismatch.value = false;
  updateError.value = '';
  updateSuccess.value = false;

  if (newPassword.value !== confirmPassword.value) {
    passwordMismatch.value = true;
    return;
  }

  isUpdating.value = true;
  try {
    const accessToken = localStorage.getItem('access_token');
    const response = await axios.post(
      `${API_ENDPOINT}/update-password`,
      {
        old_password: oldPassword.value,
        new_password: newPassword.value,
      },
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      }
    );

    if (response.status === 200) {
      updateSuccess.value = true;
      // Reset the fields after a successful update
      oldPassword.value = '';
      newPassword.value = '';
      confirmPassword.value = '';
    }
  } catch (error) {
    console.error('Error updating password:', error);
    if (error.response && error.response.data && error.response.data.message) {
      updateError.value = error.response.data.message;
    } else {
      updateError.value = 'An unexpected error occurred.';
    }
  } finally {
    isUpdating.value = false;
  }
};
</script>

<style scoped>
.profile-view-container {
  background-color: #f0f0f0;
  padding: 20px;
  border-radius: 5px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
  width: 400px;
  color: #333;
}

h2 {
  margin-bottom: 20px;
  color: #333;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
  color: #333;
}

input[type='password'] {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 3px;
  color: #333;
}

.update-button {
  background-color: #333;
  color: white;
  padding: 10px 15px;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  margin-right: 10px;
  transition: background-color 0.3s ease;
}

.update-button:hover {
  background-color: #555;
}

.update-button:disabled {
  background-color: #999;
  cursor: not-allowed;
}

.error-message {
  color: red;
  margin-bottom: 10px;
}

.success-message {
  color: green;
  margin-bottom: 10px;
}
</style>
