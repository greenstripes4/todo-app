<template>
  <div class="manage-users-view">
    <h2>Manage Users</h2>
    <div class="user-list">
      <div v-if="loading" class="loading">Loading users...</div>
      <div v-else-if="error" class="error">Error: {{ error }}</div>
      <table v-else>
        <thead>
          <tr>
            <th></th>
            <th>ID</th>
            <th>Username</th>
            <th>Role</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td><input type="checkbox" v-model="selectedUsers" :value="user.id" /></td>
            <td>{{ user.id }}</td>
            <td>{{ user.username }}</td>
            <td>
              <select v-model="user.role">
                <option value="admin">Admin</option>
                <option value="normal">Normal</option>
              </select>
            </td>
            <td>
              <select v-model="user.status">
                <option value="active">Active</option>
                <option value="deactivated">Deactivated</option>
              </select>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="pagination" v-if="pagination">
        <button :disabled="pagination.current_page === 1" @click="fetchUsers(pagination.current_page - 1)">Previous</button>
        <span>Page {{ pagination.current_page }} of {{ pagination.total_pages }}</span>
        <button :disabled="pagination.current_page === pagination.total_pages" @click="fetchUsers(pagination.current_page + 1)">Next</button>
      </div>
      <button @click="saveUpdates">Save Updates</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const users = ref([]);
const loading = ref(false);
const error = ref(null);
const pagination = ref(null);
const selectedUsers = ref([]);

// Get the API endpoint from environment variables
const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT;

const fetchUsers = async (page = 1, perPage = 25) => {
  loading.value = true;
  error.value = null;
  try {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_ENDPOINT}/users?page=${page}&per_page=${perPage}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    users.value = data.users;
    pagination.value = data.pagination;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
};

const saveUpdates = async () => {
  const token = localStorage.getItem('access_token');
  const updatedUsers = users.value.filter(user => selectedUsers.value.includes(user.id));
  for (const user of updatedUsers) {
    try {
      const response = await fetch(`${API_ENDPOINT}/users`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ id: user.id, role: user.role, status: user.status }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      console.log(`User ${user.id} updated successfully`);
    } catch (err) {
      console.error(`Error updating user ${user.id}:`, err);
    }
  }
};

onMounted(() => {
  fetchUsers();
});
</script>

<style scoped>
.manage-users-view {
  padding: 20px;
}

.user-list {
  margin-top: 20px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  border: 1px solid #ccc;
  padding: 8px;
  text-align: left;
}

.loading,
.error {
  margin-top: 20px;
}

.pagination {
  margin-top: 20px;
}
</style>
