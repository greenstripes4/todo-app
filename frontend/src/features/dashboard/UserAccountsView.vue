<template>
  <div class="user-accounts-view">
    <h2>My Website Accounts</h2>

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-message">Loading your accounts...</div>

    <!-- Error State -->
    <div v-else-if="error" class="error-message">
      Failed to load accounts: {{ error }}
    </div>

    <!-- Data Loaded State -->
    <div v-else class="accounts-list">
      <!-- No Accounts Message -->
      <p v-if="!accounts || accounts.length === 0">You haven't added any website accounts yet.</p>

      <!-- Accounts Table -->
      <table v-else>
        <thead>
          <tr>
            <th>Website URL</th>
            <th>Account Email</th>
            <th>Account Name</th>
            <th>Compliance Contact</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="account in accounts" :key="account.id">
            <td>{{ account.website_url }}</td>
            <td>{{ account.account_email }}</td>
            <td>{{ account.account_name || '-' }}</td>
            <td>{{ account.compliance_contact || '-' }}</td>
            <td>
              <button @click="editAccount(account.id)" disabled>Edit</button>
              <button @click="deleteAccount(account.id)" disabled>Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const accounts = ref([]);
const isLoading = ref(true);
const error = ref(null);
// const pagination = ref(null);

const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT;

const fetchAccounts = async () => {
  isLoading.value = true;
  error.value = null;
  // pagination.value = null;

  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Authentication token not found. Please log in.');
    }

    const url = `${API_ENDPOINT}/website-accounts`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      let errorMessage = `HTTP error! Status: ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorMessage;
      } catch (e) {
        console.warn("Could not parse error response as JSON.", e);
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    accounts.value = data.accounts || [];
    // if (data.pagination) { pagination.value = data.pagination; }

  } catch (err) {
    console.error("Error fetching website accounts:", err);
    error.value = err.message || 'An unexpected error occurred while fetching accounts.';
  } finally {
    isLoading.value = false;
  }
};

const editAccount = (accountId) => {
  console.log("Edit account:", accountId);
  // TODO: Implement navigation or modal for editing
};

const deleteAccount = (accountId) => {
  console.log("Delete account:", accountId);
  // TODO: Implement confirmation and API call for deletion
};

onMounted(() => {
  fetchAccounts();
});
</script>

<style scoped>
.user-accounts-view {
  padding: 20px; /* Match container padding */
}

.accounts-list { /* Match content container margin */
  margin-top: 20px;
  overflow-x: auto;
}

table {
  border-collapse: collapse;
}

th,
td {
  border: 1px solid #ccc;
  padding: 8px;
  text-align: left;
  white-space: nowrap; /* Prevent text wrapping */
  vertical-align: middle; /* Added for better vertical alignment */
}

.loading-message,
.error-message {
  margin-top: 20px;
}

/* Style buttons inside table cells if needed */
td button {
  margin-right: 5px;
  padding: 4px 8px; /* Adjust padding as needed */
  font-size: 0.9em; /* Adjust font size as needed */
  /* Button text color will typically be inherited or set by browser defaults */
}
td button:last-child {
  margin-right: 0;
}

/* Styles for pagination (if implemented, copy from ManageUsersView) */
/*
.pagination {
  margin-top: 20px;
}
.pagination button { ... }
.pagination button:disabled { ... }
*/
</style>
