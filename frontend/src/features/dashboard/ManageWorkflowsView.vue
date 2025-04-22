<template>
  <div class="manage-workflows-view"> <!-- Updated class name -->
    <h2>Manage All Workflows</h2> <!-- Updated Title -->

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-message">Loading workflows...</div>

    <!-- Error State -->
    <div v-if="fetchError" class="error-message">
      Failed to load workflows: {{ fetchError }}
    </div>
     <!-- Action Feedback -->
    <div v-if="actionMessage" :class="['action-message', actionError ? 'error' : 'success']">
      {{ actionMessage }}
    </div>

    <!-- Data Loaded State -->
    <div v-if="!isLoading && !fetchError" class="workflows-list">
      <!-- No Workflows Message -->
      <p v-if="workflows.length === 0">No workflows found in the system.</p> <!-- Updated Message -->

      <!-- Workflows Table -->
      <table v-else>
        <thead>
          <tr>
            <th>Workflow ID</th>
            <th>Website URL</th>
            <!-- START: Added User Column -->
            <th>User</th>
            <!-- END: Added User Column -->
            <th>Type</th>
            <th>Status</th>
            <th>Active Tasks</th>
            <th>Created At</th>
            <th>Updated At</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="workflow in workflows" :key="workflow.id">
            <td>{{ workflow.workflow_id }}</td>
            <td>{{ workflow.website_account?.website_url || 'N/A' }}</td>
            <!-- START: Added User Data Cell -->
            <td>{{ workflow.user?.username || workflow.user_id || 'N/A' }}</td>
            <!-- END: Added User Data Cell -->
            <td>{{ workflow.workflow_type }}</td>
            <td>
              <span :class="['status-badge', `status-${workflow.workflow_status?.toLowerCase().replace('_', '-')}`]">
                {{ workflow.workflow_status }}
              </span>
            </td>
            <td>
              {{ formatActiveTasks(workflow.active_tasks) }}
            </td>
            <td>{{ formatDateTime(workflow.created_at) }}</td>
            <td>{{ formatDateTime(workflow.updated_at) }}</td>
            <td>
              <!-- Terminate Button -->
              <button
                @click="terminateWorkflow(workflow.workflow_id)"
                :disabled="!isTerminable(workflow.workflow_status) || isTerminating[workflow.workflow_id]"
                class="action-button terminate-button"
              >
                {{ isTerminating[workflow.workflow_id] ? 'Terminating...' : 'Terminate' }}
              </button>
              <!-- Add other admin actions here if needed -->
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination Controls (similar to ManageUsersView) -->
      <div v-if="pagination && pagination.total_items > 0" class="pagination-controls">
         <button @click="fetchWorkflows(pagination.current_page - 1)" :disabled="pagination.current_page <= 1">
           Previous
         </button>
         <span>
           Page {{ pagination.current_page }} of {{ pagination.total_pages }} ({{ pagination.total_items }} total workflows)
         </span>
         <button @click="fetchWorkflows(pagination.current_page + 1)" :disabled="pagination.current_page >= pagination.total_pages">
           Next
         </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';

// Copied reactive state and helpers from UserWorkflowsView
const workflows = ref([]);
const pagination = ref(null);
const isLoading = ref(true);
const fetchError = ref(null);
const actionMessage = ref('');
const actionError = ref(false);
const isTerminating = reactive({});

const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT;

// Copied helper functions
const formatDateTime = (dateTimeString) => {
  if (!dateTimeString) return 'N/A';
  try {
    const options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return new Date(dateTimeString).toLocaleString(undefined, options);
  } catch (e) {
    console.error("Error formatting date:", e);
    return dateTimeString;
  }
};

const formatActiveTasks = (tasks) => {
  if (!tasks || tasks.length === 0) {
    return 'None';
  }
  return tasks.join(', ');
};

const isTerminable = (status) => {
  const terminalStatuses = ['COMPLETED', 'FAILED', 'CANCELLED', 'TERMINATED', 'DELETED'];
  return !terminalStatuses.includes(status?.toUpperCase());
};

const clearActionMessage = () => {
  setTimeout(() => {
    actionMessage.value = '';
    actionError.value = false;
  }, 5000);
};

// Copied and modified fetchWorkflows
const fetchWorkflows = async (page = 1, perPage = 10) => {
  isLoading.value = true;
  fetchError.value = null;
  actionMessage.value = '';

  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Authentication token not found. Please log in.');
    }

    const url = new URL(`${API_ENDPOINT}/workflows`);
    url.searchParams.append('page', page);
    url.searchParams.append('per_page', perPage);
    // --- START: Modified scope parameter ---
    url.searchParams.append('scope', 'all'); // Fetch all workflows for admin
    // --- END: Modified scope parameter ---

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      // Handle specific errors like 403 Forbidden if the user is not an admin
      if (response.status === 403) {
        throw new Error('Forbidden: You do not have permission to view all workflows.');
      }
      let errorMessage = `HTTP error! Status: ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorMessage;
      } catch (e) { console.warn("Could not parse error response as JSON.", e); }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    // Assuming the backend includes user info when scope=all
    workflows.value = data.workflows || [];
    pagination.value = data.pagination || null;

  } catch (err) {
    console.error("Error fetching workflows:", err);
    fetchError.value = err.message || 'An unexpected error occurred while fetching workflows.';
    workflows.value = [];
    pagination.value = null;
  } finally {
    isLoading.value = false;
  }
};

// Copied terminateWorkflow (assumes backend handles admin authorization)
const terminateWorkflow = async (workflowId) => {
  if (!workflowId) return;

  isTerminating[workflowId] = true;
  actionMessage.value = '';
  actionError.value = false;

  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Authentication token not found.');
    }

    const url = `${API_ENDPOINT}/workflows/${workflowId}/status`;
    const response = await fetch(url, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ status: 'Terminated' }),
    });

    if (!response.ok) {
      let errorMessage = `Failed to terminate workflow (Status: ${response.status})`;
      if (response.status === 403) {
         errorMessage = 'Forbidden: You do not have permission to terminate this workflow.';
      } else {
          try {
            const errorData = await response.json();
            errorMessage = errorData.message || errorMessage;
          } catch (e) { console.warn("Could not parse error response as JSON.", e); }
      }
      throw new Error(errorMessage);
    }

    const updatedWorkflowData = await response.json();

    // Update local state
    const index = workflows.value.findIndex(wf => wf.workflow_id === workflowId);
    if (index !== -1 && updatedWorkflowData.workflow) {
       // Include user data in the update if present in the response
       workflows.value[index] = { ...workflows.value[index], ...updatedWorkflowData.workflow };
    } else {
        console.warn("Could not find workflow locally to update, refetching list.");
        await fetchWorkflows(pagination.value?.current_page || 1, pagination.value?.per_page || 10);
    }

    actionMessage.value = `Workflow ${workflowId} terminated successfully.`;
    actionError.value = false;

  } catch (err) {
    console.error("Error terminating workflow:", err);
    actionMessage.value = err.message || 'An unexpected error occurred.';
    actionError.value = true;
  } finally {
    isTerminating[workflowId] = false;
    clearActionMessage();
  }
};

// Fetch workflows on mount
onMounted(() => {
  fetchWorkflows();
});
</script>

<style scoped>
/* Copied styles directly from UserWorkflowsView.vue */
.manage-workflows-view { /* Updated class name */
  padding: 20px;
}

h2 {
  margin-bottom: 20px;
  margin-top: 0;
}

.workflows-list {
  margin-top: 20px;
  overflow-x: auto; /* Enable horizontal scrolling for table */
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 15px;
  min-width: 800px; /* Ensure table has a minimum width */
}

th,
td {
  border: 1px solid #ccc;
  padding: 8px 12px; /* Slightly more padding */
  text-align: left;
  white-space: nowrap;
  vertical-align: middle;
}

th {
  background-color: #f8f9fa;
  font-weight: 600;
  color: #000000;
}

/* Center align action buttons column */
td:last-child {
    text-align: center;
}

.loading-message,
.error-message,
.action-message {
  margin-top: 15px;
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

.error-message,
.action-message.error {
  color: #721c24;
  background-color: #f8d7da;
  border-color: #f5c6cb;
}

.action-message.success {
  color: #155724;
  background-color: #d4edda;
  border-color: #c3e6cb;
}


/* Status Badge Styling */
.status-badge {
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 0.85em;
  font-weight: 500;
  color: white;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: inline-block;
  line-height: 1.2;
}

/* Status colors */
.status-pending { background-color: #ffc107; color: #333; }
.status-running { background-color: #17a2b8; }
.status-suspended { background-color: #fd7e14; }
.status-completed { background-color: #28a745; }
.status-failed { background-color: #dc3545; }
.status-terminated { background-color: #6c757d; }
.status-cancelled { background-color: #6c757d; }
.status-deleted { background-color: #343a40; }


/* Pagination Controls Styling (similar to ManageUsersView) */
.pagination-controls {
    margin-top: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.9em;
    color: #555;
}

.pagination-controls button {
  padding: 6px 12px;
  border: 1px solid #ccc;
  background-color: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.pagination-controls button:hover:not(:disabled) {
  background-color: #e9ecef;
}

.pagination-controls button:disabled {
  background-color: #f8f9fa;
  color: #aaa;
  cursor: not-allowed;
  border-color: #ddd;
}

.pagination-controls span {
    margin: 0 10px;
}


/* Action Button Styling */
.action-button {
  padding: 5px 10px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  transition: background-color 0.2s ease;
  margin: 0 2px;
  vertical-align: middle;
}

.terminate-button {
  background-color: #dc3545; /* Red */
  color: white;
}

.terminate-button:hover:not(:disabled) {
  background-color: #c82333; /* Darker red on hover */
}

.action-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
  opacity: 0.7;
}
</style>
