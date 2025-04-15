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
        <!-- *** START: New DSAR Workflow Button *** -->
        <button
          @click="createDsarWorkflows"
          class="action-button dsar-button"
          :disabled="selectedAccountIds.length === 0 || isCreatingWorkflows"
          title="Create DSAR workflow for selected accounts"
        >
          {{ isCreatingWorkflows ? 'Creating...' : 'Create DSAR Workflow' }}
        </button>
        <!-- *** END: New DSAR Workflow Button *** -->
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
    <!-- *** START: Workflow Creation Error State *** -->
    <div v-if="workflowError" class="error-message">
      {{ workflowError }}
    </div>
    <!-- *** END: Workflow Creation Error State *** -->
    <!-- *** START: Workflow Creation Success State *** -->
    <div v-if="workflowSuccessMessage" class="success-message">
      {{ workflowSuccessMessage }}
    </div>
    <!-- *** END: Workflow Creation Success State *** -->


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
      <div v-if="selectedAccountIds.length > 0" class="selection-info">
        Selected: {{ selectedAccountIds.length }} account(s)
        <!-- Example bulk delete (currently disabled) -->
        <!-- <button @click="bulkDeleteSelected" disabled>Delete Selected</button> -->
      </div>
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
import { ref, onMounted, computed } from 'vue';
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
const selectedAccountIds = ref([]);

// --- START: New Refs for Workflow Creation ---
const isCreatingWorkflows = ref(false);
const workflowError = ref(null);
const workflowSuccessMessage = ref(null);
// --- END: New Refs for Workflow Creation ---

const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT;

// --- Computed Property for "Select All" Checkbox State ---
const isAllSelected = computed(() => {
  return accounts.value.length > 0 && accounts.value.every(acc => selectedAccountIds.value.includes(acc.id));
});

// --- Method to Toggle Select All (via header checkbox) ---
const toggleSelectAll = (event) => {
  if (event.target.checked) {
    selectedAccountIds.value = accounts.value.map(acc => acc.id);
  } else {
    selectedAccountIds.value = [];
  }
};

// --- Method to Flip All Selections (via button) ---
const flipAllSelections = () => {
  if (accounts.value.length === 0) return;

  const allAccountIds = accounts.value.map(acc => acc.id);
  const currentlySelected = new Set(selectedAccountIds.value);
  const newSelectedIds = [];

  allAccountIds.forEach(id => {
    if (!currentlySelected.has(id)) {
      newSelectedIds.push(id);
    }
  });

  selectedAccountIds.value = newSelectedIds;
};


const fetchAccounts = async () => {
  isLoading.value = true;
  fetchError.value = null;
  deleteError.value = null;
  workflowError.value = null; // Clear workflow errors on fetch
  workflowSuccessMessage.value = null; // Clear workflow success on fetch
  selectedAccountIds.value = [];

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
  workflowError.value = null; // Clear workflow errors
  workflowSuccessMessage.value = null; // Clear workflow success
  isModalVisible.value = true;
};

const openEditModal = (account) => {
  modalMode.value = 'edit';
  accountToEdit.value = { ...account };
  deleteError.value = null;
  workflowError.value = null; // Clear workflow errors
  workflowSuccessMessage.value = null; // Clear workflow success
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
  workflowError.value = null; // Clear workflow errors
  workflowSuccessMessage.value = null; // Clear workflow success
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
        // Use a more general error display if modal isn't involved or available
        fetchError.value = `Save failed: ${err.message}`;
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
  workflowError.value = null; // Clear workflow errors
  workflowSuccessMessage.value = null; // Clear workflow success

  try {
    const token = localStorage.getItem('access_token');
    if (!token) throw new Error('Authentication token not found.');

    const url = `${API_ENDPOINT}/website-accounts/${accountId}`;
    const response = await fetch(url, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}`, 'Accept': 'application/json' },
    });

    if (!response.ok && response.status !== 204) { // 204 No Content is also a success for DELETE
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
    // No specific loading state for delete needed here as it's quick
  }
};

// --- Method to Create DSAR Workflows ---
const createDsarWorkflows = async () => {
  if (selectedAccountIds.value.length === 0 || isCreatingWorkflows.value) {
    return; // Don't run if nothing selected or already running
  }

  isCreatingWorkflows.value = true;
  workflowError.value = null;
  workflowSuccessMessage.value = null;
  deleteError.value = null; // Clear other errors

  const token = localStorage.getItem('access_token');
  if (!token) {
    workflowError.value = 'Authentication token not found. Please log in.';
    isCreatingWorkflows.value = false;
    return;
  }

  const url = `${API_ENDPOINT}/workflows`;
  const workflowType = 'DSAR'; // As requested

  // --- START: Modification ---
  // Prepare the payload with the list of selected IDs
  const payload = {
    website_account_ids: [...selectedAccountIds.value], // Send the array of selected IDs
    workflow_type: workflowType,
  };
  // --- END: Modification ---

  try {
    // --- START: Modification ---
    // Send ONE request with the list of IDs
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let errorMessage = `Workflow creation failed. Status: ${response.status}`;
      try {
        const errorData = await response.json();
        // Use the specific error message from the backend if available
        errorMessage = errorData.message || errorMessage;
      } catch (e) {
         console.warn("Could not parse error response as JSON.", e);
      }
      throw new Error(errorMessage);
    }

    // Assuming the backend returns a success message or details about created workflows
    // You might need to adjust this based on the actual API response structure
    try {
        const resultData = await response.json();
        // Example: Use a message from the backend if provided
        workflowSuccessMessage.value = resultData.message || `Successfully initiated ${selectedAccountIds.value.length} DSAR workflow(s).`;
    } catch(e) {
        // Fallback message if response parsing fails or no message field
        workflowSuccessMessage.value = `Successfully initiated ${selectedAccountIds.value.length} DSAR workflow(s).`;
        console.warn("Could not parse success response as JSON or missing 'message' field.", e);
    }

    // Clear selection after successful processing
    selectedAccountIds.value = [];
    // --- END: Modification ---

  } catch (error) {
    console.error(`Error creating DSAR workflows:`, error);
    // Display the error caught from the fetch or the !response.ok block
    workflowError.value = error.message || 'An unexpected error occurred during workflow creation.';
  } finally {
    isCreatingWorkflows.value = false;

    // Optional: Hide success/error messages after a delay
    setTimeout(() => {
        workflowError.value = null;
        workflowSuccessMessage.value = null;
    }, 7000); // Hide after 7 seconds
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

/* Common button styles */
.add-button,
.invert-button,
.dsar-button { /* Added .dsar-button */
    padding: 8px 15px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.95em;
    white-space: nowrap; /* Prevent button text wrapping */
    transition: background-color 0.2s ease; /* Smooth hover */
}
.add-button:disabled,
.invert-button:disabled,
.dsar-button:disabled { /* Added .dsar-button */
    background-color: #c0c4c8;
    cursor: not-allowed;
    opacity: 0.7;
}


.add-button {
    background-color: #28a745; /* Green color for add */
    color: white;
}
.add-button:hover:not(:disabled) {
    background-color: #218838;
}

.invert-button {
    background-color: #6c757d; /* Grey color for invert */
    color: white;
}
.invert-button:hover:not(:disabled) {
    background-color: #5a6268;
}

/* --- START: DSAR Button Styles --- */
.dsar-button {
    background-color: #007bff; /* Blue color for action */
    color: white;
}
.dsar-button:hover:not(:disabled) {
    background-color: #0056b3;
}
/* --- END: DSAR Button Styles --- */


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
.error-message,
.success-message { /* Added .success-message */
  margin-top: 15px; /* Consistent spacing */
  margin-bottom: 15px;
  padding: 0.8rem 1rem;
  border-radius: 4px;
  border: 1px solid transparent;
}

.loading-message {
  font-style: italic;
  color: #555;
  background-color: #e9ecef;
  border-color: #ced4da;
}

.error-message {
  color: #721c24; /* Darker red text */
  background-color: #f8d7da; /* Light red background */
  border-color: #f5c6cb; /* Reddish border */
}

/* --- START: Success Message Style --- */
.success-message {
  color: #155724; /* Darker green text */
  background-color: #d4edda; /* Light green background */
  border-color: #c3e6cb; /* Greenish border */
}
/* --- END: Success Message Style --- */

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

/* --- START: Selection Info Style --- */
.selection-info {
    margin-top: 15px;
    font-size: 0.9em;
    color: #555;
}
/* --- END: Selection Info Style --- */

</style>
