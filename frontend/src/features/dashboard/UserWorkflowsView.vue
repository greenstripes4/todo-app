<template>
  <div class="user-workflows-view">
    <h2>My Workflows</h2>

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
      <p v-if="workflows.length === 0">You haven't created any workflows yet.</p>

      <!-- Workflows Table -->
      <table v-else>
        <thead>
          <tr>
            <th>Workflow ID</th>
            <th>Website URL</th>
            <th>Type</th>
            <th>Status</th>
            <th>Active Tasks</th> <!-- Added Active Tasks Header -->
            <th>Created At</th>
            <th>Updated At</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="workflow in workflows" :key="workflow.id">
            <td>{{ workflow.workflow_id }}</td>
            <td>{{ workflow.website_account?.website_url || 'N/A' }}</td>
            <td>{{ workflow.workflow_type }}</td>
            <td>
              <!-- Updated class binding for status badges -->
              <span :class="['status-badge', `status-${workflow.workflow_status?.toLowerCase().replace('_', '-')}`]">
                {{ workflow.workflow_status }}
              </span>
            </td>
            <!-- Display Active Tasks -->
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
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Basic Pagination Info (Optional) -->
      <div v-if="pagination && pagination.total_items > 0" class="pagination-info">
        Showing page {{ pagination.current_page }} of {{ pagination.total_pages }} ({{ pagination.total_items }} total workflows)
        <!-- Add actual pagination controls here if needed -->
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';

const workflows = ref([]);
const pagination = ref(null); // Initialize pagination state
const isLoading = ref(true);
const fetchError = ref(null);
const actionMessage = ref(''); // For showing success/error after action
const actionError = ref(false); // Flag to style action message as error
const isTerminating = reactive({}); // Track terminating state per workflow

const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT;

// Helper function to format date/time
const formatDateTime = (dateTimeString) => {
  if (!dateTimeString) return 'N/A';
  try {
    const options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return new Date(dateTimeString).toLocaleString(undefined, options);
  } catch (e) {
    console.error("Error formatting date:", e);
    return dateTimeString; // Fallback to original string
  }
};

// --- NEW HELPER: Format Active Tasks ---
const formatActiveTasks = (tasks) => {
  if (!tasks || tasks.length === 0) {
    return 'None'; // Or '-' or empty string
  }
  // Join the array of task names into a comma-separated string
  return tasks.join(', ');
};


// Helper function to check if a workflow status allows termination
const isTerminable = (status) => {
  // Enable button for statuses that are not final
  // Based on backend UserWorkflowStatusEnum
  const terminalStatuses = ['COMPLETED', 'FAILED', 'CANCELLED', 'TERMINATED', 'DELETED'];
  return !terminalStatuses.includes(status?.toUpperCase());
};

// Function to clear action messages after a delay
const clearActionMessage = () => {
  setTimeout(() => {
    actionMessage.value = '';
    actionError.value = false;
  }, 5000); // Clear after 5 seconds
};

const fetchWorkflows = async (page = 1, perPage = 10) => { // Add parameters for pagination
  isLoading.value = true;
  fetchError.value = null;
  actionMessage.value = ''; // Clear previous action messages on refresh

  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('Authentication token not found. Please log in.');
    }
    // Construct URL with pagination parameters
    const url = new URL(`${API_ENDPOINT}/workflows`);
    url.searchParams.append('page', page);
    url.searchParams.append('per_page', perPage);
    // --- START: Added scope parameter ---
    url.searchParams.append('scope', 'mine'); // Explicitly request user's own workflows
    // --- END: Added scope parameter ---

    const response = await fetch(url.toString(), { // Use url.toString()
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
    workflows.value = data.workflows || [];
    pagination.value = data.pagination || null; // Store pagination metadata

  } catch (err) {
    console.error("Error fetching workflows:", err);
    fetchError.value = err.message || 'An unexpected error occurred while fetching workflows.';
    workflows.value = [];
    pagination.value = null; // Reset pagination on error
  } finally {
    isLoading.value = false;
  }
};

// --- METHOD: Terminate Workflow ---
const terminateWorkflow = async (workflowId) => {
  if (!workflowId) return;

  // Set loading state for this specific button
  isTerminating[workflowId] = true;
  actionMessage.value = ''; // Clear previous messages
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
      // Using 'Terminated' as the backend status for termination
      body: JSON.stringify({ status: 'Terminated' }),
    });

    if (!response.ok) {
      let errorMessage = `Failed to terminate workflow (Status: ${response.status})`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorMessage;
      } catch (e) { console.warn("Could not parse error response as JSON.", e); }
      throw new Error(errorMessage);
    }

    const updatedWorkflowData = await response.json();

    // Update local state for immediate feedback
    const index = workflows.value.findIndex(wf => wf.workflow_id === workflowId);
    if (index !== -1 && updatedWorkflowData.workflow) {
       // Update the specific workflow in the array
       workflows.value[index] = { ...workflows.value[index], ...updatedWorkflowData.workflow };
    } else {
        // Fallback: Refetch all workflows if local update fails
        console.warn("Could not find workflow locally to update, refetching list.");
        // Refetch current page
        await fetchWorkflows(pagination.value?.current_page || 1, pagination.value?.per_page || 10);
    }

    actionMessage.value = `Workflow ${workflowId} terminated successfully.`;
    actionError.value = false;

  } catch (err) {
    console.error("Error terminating workflow:", err);
    actionMessage.value = err.message || 'An unexpected error occurred.';
    actionError.value = true;
  } finally {
    // Reset loading state for this specific button
    isTerminating[workflowId] = false;
    clearActionMessage(); // Clear the message after a few seconds
  }
};

// Fetch workflows when the component is mounted (fetch first page)
onMounted(() => {
  fetchWorkflows();
});
</script>

<style scoped>
/* Styles are kept as they were in the provided context */
.user-workflows-view {
  padding: 20px;
}

h2 {
  margin-bottom: 20px;
  margin-top: 0;
}

.workflows-list {
  margin-top: 20px;
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 15px;
}

th,
td {
  border: 1px solid #ccc;
  padding: 8px 10px; /* Adjusted padding slightly */
  text-align: left;
  white-space: nowrap;
  vertical-align: middle;
}

th {
  background-color: #f8f9fa;
  font-weight: 600;
  color: #000000;
}

/* Center align action buttons */
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
  display: inline-block; /* Added for consistency */
  line-height: 1.2; /* Added for consistency */
}

/* Original status colors + new ones */
.status-pending { background-color: #ffc107; color: #333; }
.status-running { background-color: #17a2b8; } /* Added Running */
.status-suspended { background-color: #fd7e14; } /* Added Suspended */
.status-completed { background-color: #28a745; }
.status-failed { background-color: #dc3545; }
.status-terminated { background-color: #6c757d; } /* Added Terminated */
.status-cancelled { background-color: #6c757d; }
.status-deleted { background-color: #343a40; } /* Added Deleted */
/* Note: .status-in_progress is removed as backend uses RUNNING */


.pagination-info {
    margin-top: 15px;
    font-size: 0.9em;
    color: #555;
    text-align: right;
}

/* Action Button Styling */
.action-button {
  padding: 5px 10px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  transition: background-color 0.2s ease;
  margin: 0 2px; /* Add small margin between buttons if needed */
  vertical-align: middle; /* Added for consistency */
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
