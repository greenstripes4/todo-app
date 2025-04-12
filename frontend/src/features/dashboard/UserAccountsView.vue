<template>
  <div class="user-accounts-view">
    <div class="view-header">
      <h2>My Website Accounts</h2>
      <div class="header-actions">
        <!-- Invert Selection Button -->
        <button
          @click="flipAllSelections"
          class="invert-button"
          :disabled="!accounts || accounts.length === 0"
          title="Invert current selection"
        >
          Invert Selection
        </button>
        <!-- Add New Account Button -->
        <button @click="openCreateModal" class="add-button">Add New Account</button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading && !accounts.length" class="loading-message">Loading your accounts...</div>

    <!-- Error State -->
    <div v-if="fetchError" class="error-message">
      Failed to load accounts: {{ fetchError }}
    </div>
    <!-- Deletion Error State -->
    <div v-if="deleteError" class="error-message">
      {{ deleteError }}
    </div>


    <!-- Data Loaded State -->
    <div v-show="!isLoading || accounts.length" class="accounts-list">
      <!-- No Accounts Message -->
      <p v-if="!isLoading && (!accounts || accounts.length === 0)">You haven't added any website accounts yet.</p>

      <!-- Accounts Table -->
      <table v-else>
        <thead>
          <tr>
            <!-- Header Checkbox -->
            <th class="checkbox-col">
              <input
                type="checkbox"
                :checked="isAllSelected"
                @change="toggleSelectAll"
                :disabled="!accounts || accounts.length === 0"
              />
            </th>
            <th>Website URL</th>
            <th>Account Email</th>
            <th>Account Name</th>
            <th>Compliance Contact</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="account in accounts" :key="account.id">
            <!-- Row Checkbox -->
            <td class="checkbox-col">
              <input type="checkbox" v-model="selectedAccountIds" :value="account.id" />
            </td>
            <td>{{ account.website_url }}</td>
            <td>{{ account.account_email }}</td>
            <td>{{ account.account_name || '-' }}</td>
            <td>{{ account.compliance_contact || '-' }}</td>
            <td>
              <button @click="openEditModal(account)">Edit</button>
              <button @click="deleteAccount(account.id, account.website_url)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
      <!-- Optional: Display selected count or add bulk actions -->
      <!-- <div v-if="selectedAccountIds.length > 0">
        Selected: {{ selectedAccountIds.length }}
        <button @click="bulkDeleteSelected" disabled>Delete Selected</button>
      </div> -->
    </div>

    <!-- Edit/Create Account Modal -->
    <EditAccountModal
      ref="accountModalRef"
      :visible="isModalVisible"
      :account="accountToEdit"
      :mode="modalMode"
      @close="closeEditModal"
      @save="handleSaveChanges"
    />

  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'; // Import computed
import EditAccountModal from './EditAccountModal.vue';

const accounts = ref([]);
const isLoading = ref(true);
const fetchError = ref(null);
const deleteError = ref(null);
const isModalVisible = ref(false);
const accountToEdit = ref(null);
const modalMode = ref('create');
const isSaving = ref(false);
const accountModalRef = ref(null);
const selectedAccountIds = ref([]); // State for selected account IDs

const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT;

// --- Computed Property for "Select All" Checkbox State ---
// This computed property might become less intuitive with the new flip logic,
// but it still correctly reflects if *all* items happen to be selected.
const isAllSelected = computed(() => {
  // Check if accounts list is not empty and every account ID is in selectedAccountIds
  return accounts.value.length > 0 && accounts.value.every(acc => selectedAccountIds.value.includes(acc.id));
});

// --- Method to Toggle Select All (via header checkbox) ---
// This remains the same, controlling the header checkbox behavior
const toggleSelectAll = (event) => {
  if (event.target.checked) {
    // Select all: map account IDs to the selected list
    selectedAccountIds.value = accounts.value.map(acc => acc.id);
  } else {
    // Deselect all: clear the list
    selectedAccountIds.value = [];
  }
};

// --- Method to Flip All Selections (via button) ---
// Updated logic: Invert the selection status of each item
const flipAllSelections = () => {
  if (accounts.value.length === 0) return; // Do nothing if no accounts

  const allAccountIds = accounts.value.map(acc => acc.id);
  const currentlySelected = new Set(selectedAccountIds.value); // Use a Set for efficient lookup
  const newSelectedIds = [];

  allAccountIds.forEach(id => {
    if (!currentlySelected.has(id)) {
      // If it wasn't selected, select it now
      newSelectedIds.push(id);
    }
    // If it was selected (present in the Set), it's implicitly deselected
    // by not being added to newSelectedIds.
  });

  selectedAccountIds.value = newSelectedIds;
};


const fetchAccounts = async () => {
  isLoading.value = true;
  fetchError.value = null;
  deleteError.value = null;
  selectedAccountIds.value = []; // Clear selection on fetch

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
      } catch (e) { console.warn("Could not parse error response as JSON.", e); }
      throw new Error(errorMessage);
    }
    const data = await response.json();
    accounts.value = data.accounts || [];
  } catch (err) {
    console.error("Error fetching website accounts:", err);
    fetchError.value = err.message || 'An unexpected error occurred while fetching accounts.';
  } finally {
    isLoading.value = false;
  }
};

// --- Modal Methods ---
const openCreateModal = () => {
  modalMode.value = 'create';
  accountToEdit.value = null;
  deleteError.value = null;
  isModalVisible.value = true;
};

const openEditModal = (account) => {
  modalMode.value = 'edit';
  accountToEdit.value = { ...account };
  deleteError.value = null;
  isModalVisible.value = true;
};

const closeEditModal = () => {
  isModalVisible.value = false;
  accountToEdit.value = null;
  if (accountModalRef.value) {
      accountModalRef.value.setErrorMessage('');
      accountModalRef.value.resetSavingState();
  }
};

const handleSaveChanges = async (accountData) => {
  isSaving.value = true;
  deleteError.value = null;
  if (accountModalRef.value) {
    accountModalRef.value.setErrorMessage('');
  }

  const token = localStorage.getItem('access_token');
  if (!token) {
    if (accountModalRef.value) accountModalRef.value.setErrorMessage('Authentication token not found.');
    isSaving.value = false;
    if (accountModalRef.value) accountModalRef.value.resetSavingState();
    return;
  }

  try {
    let response;
    let url;
    let method;
    const payload = { ...accountData };

    if (modalMode.value === 'edit') {
      url = `${API_ENDPOINT}/website-accounts/${accountData.id}`;
      method = 'PUT';
    } else {
      delete payload.id;
      url = `${API_ENDPOINT}/website-accounts`;
      method = 'POST';
    }

    response = await fetch(url, {
      method: method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let errorMessage = `${method === 'PUT' ? 'Update' : 'Creation'} failed! Status: ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorMessage;
      } catch (e) { console.warn("Could not parse error response as JSON.", e); }
      throw new Error(errorMessage);
    }

    // --- Success ---
     if (modalMode.value === 'edit') {
        const index = accounts.value.findIndex(acc => acc.id === accountData.id);
        if (index !== -1) {
            try {
                const updatedFromServer = await response.json();
                if (updatedFromServer && updatedFromServer.id) {
                    accounts.value[index] = updatedFromServer;
                } else {
                    accounts.value[index] = { ...accounts.value[index], ...accountData };
                }
            } catch (e) {
                console.warn("Could not parse update response, merging local data.", e);
                accounts.value[index] = { ...accounts.value[index], ...accountData };
            }
        } else {
             console.warn(`Edited account ID ${accountData.id} not found locally. Refetching.`);
             await fetchAccounts(); // Refetch if local item not found
        }
    } else { // Create mode
        let newAccount = null;
        try {
            newAccount = await response.json();
        } catch (e) {
            console.warn("Could not parse create response body as JSON.", e);
        }

        if (newAccount && newAccount.id) {
            console.log('New account received from server:', newAccount);
            accounts.value.unshift(newAccount);
        } else {
            console.warn('New account data not returned or invalid in response. Refetching list.');
            await fetchAccounts();
        }
    }

    closeEditModal();

  } catch (err) {
    console.error(`Error ${modalMode.value === 'edit' ? 'saving' : 'creating'} account:`, err);
    if (accountModalRef.value) {
        accountModalRef.value.setErrorMessage(err.message || `An unexpected error occurred during ${modalMode.value}.`);
    } else {
        alert(`Save failed: ${err.message}`);
    }
  } finally {
    isSaving.value = false;
    if (accountModalRef.value) {
        accountModalRef.value.resetSavingState();
    }
  }
};


// --- Delete Method ---
const deleteAccount = async (accountId, accountUrl) => {
  const confirmed = window.confirm(`Are you sure you want to delete the account for "${accountUrl || 'this website'}"?`);
  if (!confirmed) return;

  deleteError.value = null;

  try {
    const token = localStorage.getItem('access_token');
    if (!token) throw new Error('Authentication token not found.');

    const url = `${API_ENDPOINT}/website-accounts/${accountId}`;
    const response = await fetch(url, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}`, 'Accept': 'application/json' },
    });

    if (!response.ok && response.status !== 204) {
      let errorMessage = `Deletion failed! Status: ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorMessage;
      } catch (e) { console.warn("Could not parse error response on delete as JSON.", e); }
      throw new Error(errorMessage);
    }

    // --- Success ---
    accounts.value = accounts.value.filter(acc => acc.id !== accountId);
    // Also remove from selected list if it was selected
    selectedAccountIds.value = selectedAccountIds.value.filter(id => id !== accountId);
    console.log(`Account ${accountId} deleted successfully.`);

  } catch (err) {
    console.error(`Error deleting account ${accountId}:`, err);
    deleteError.value = err.message || 'An unexpected error occurred during deletion.';
  } finally {
    // isDeleting.value = false;
  }
};

onMounted(() => {
  fetchAccounts();
});
</script>

<style scoped>
/* Add styles for the header and button */
.view-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px; /* Add space below header */
    flex-wrap: wrap; /* Allow wrapping if needed */
    gap: 10px; /* Add gap between title and actions */
}

.header-actions {
    display: flex;
    gap: 10px; /* Space between buttons */
    align-items: center;
}

.add-button,
.invert-button { /* Apply common styles */
    padding: 8px 15px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.95em;
    white-space: nowrap; /* Prevent button text wrapping */
}

.add-button {
    background-color: #28a745; /* Green color for add */
    color: white;
}
.add-button:hover {
    background-color: #218838;
}

.invert-button {
    background-color: #6c757d; /* Grey color for invert */
    color: white;
}
.invert-button:hover {
    background-color: #5a6268;
}
.invert-button:disabled {
    background-color: #c0c4c8;
    cursor: not-allowed;
}


/* Existing styles remain the same */
.user-accounts-view {
  padding: 20px;
}

h2 {
  margin-bottom: 0;
  margin-top: 0;
  margin-right: auto; /* Push actions to the right */
}


.accounts-list {
  margin-top: 20px;
  overflow-x: auto;
}

table {
  border-collapse: collapse;
  /* Consider removing width: 100% if you want table to shrink */
  /* width: 100%; */
}

th,
td {
  border: 1px solid #ccc;
  padding: 8px;
  text-align: left;
  white-space: nowrap;
  vertical-align: middle;
}

/* Style for checkbox column */
.checkbox-col {
  width: 1%; /* Make checkbox column narrow */
  text-align: center;
  white-space: nowrap; /* Prevent wrapping just in case */
}
.checkbox-col input[type="checkbox"] {
  margin: 0; /* Remove default margins */
}


th {
  background-color: #f8f9fa;
  font-weight: 600;
  color: #000000;
}

.loading-message,
.error-message {
  margin-top: 20px;
}

.loading-message {
  font-style: italic;
  color: #555;
}

.error-message {
  color: #d9534f;
  background-color: #f2dede;
  border: 1px solid #ebccd1;
  padding: 0.8rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

td button {
  margin-right: 5px;
  padding: 4px 8px;
  font-size: 0.9em;
  cursor: pointer;
}
td button:disabled {
    cursor: not-allowed;
    opacity: 0.6;
}
td button:last-child {
  margin-right: 0;
}

</style>
