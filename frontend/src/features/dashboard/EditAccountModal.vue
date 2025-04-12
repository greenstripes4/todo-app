<template>
  <div v-if="visible" class="modal-overlay" @click.self="closeModal">
    <div class="modal-content">
      <!-- Dynamically set the title based on the mode -->
      <h3>{{ isEditMode ? 'Edit Account' : 'Add New Account' }}</h3>
      <form @submit.prevent="saveChanges">
        <div class="form-group">
          <label for="website_url">Website URL:</label>
          <input type="text" id="website_url" v-model="editableAccount.website_url" required />
        </div>
        <div class="form-group">
          <label for="account_email">Account Email:</label>
          <input type="email" id="account_email" v-model="editableAccount.account_email" required />
        </div>
        <div class="form-group">
          <label for="account_name">Account Name:</label>
          <input type="text" id="account_name" v-model="editableAccount.account_name" />
        </div>
        <div class="form-group">
          <label for="compliance_contact">Compliance Contact:</label>
          <input type="text" id="compliance_contact" v-model="editableAccount.compliance_contact" />
        </div>

        <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
        <div v-if="isSaving" class="saving-message">Saving...</div>

        <div class="modal-actions">
          <button type="button" @click="closeModal" :disabled="isSaving">Cancel</button>
          <button type="submit" :disabled="isSaving">
            {{ isEditMode ? 'Save Changes' : 'Add Account' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, reactive, computed } from 'vue'; // Added computed

const props = defineProps({
  visible: Boolean,
  account: Object, // The account data passed from the parent (null for create)
  mode: { // Add mode prop
    type: String,
    required: true,
    validator: (value) => ['create', 'edit'].includes(value), // Validate mode
  },
});

const emit = defineEmits(['close', 'save']);

// Determine if we are in edit mode
const isEditMode = computed(() => props.mode === 'edit');

// Default structure for a new account
const defaultAccountStructure = {
  id: null,
  website_url: '',
  account_email: '',
  account_name: '',
  compliance_contact: '',
};

// Use reactive for the form data
const editableAccount = reactive({ ...defaultAccountStructure });

const isSaving = ref(false); // Keep isSaving local to the modal for button state
const errorMessage = ref(''); // Keep errorMessage local

// Watch for changes in visibility or account prop to reset/populate the form
watch(() => [props.visible, props.account, props.mode], ([newVisible, newAccount, newMode]) => {
  if (newVisible) {
    errorMessage.value = ''; // Clear errors when modal opens
    isSaving.value = false; // Reset saving state
    if (newMode === 'edit' && newAccount) {
      // Edit mode: Copy data from prop
      Object.assign(editableAccount, {
        id: newAccount.id,
        website_url: newAccount.website_url || '',
        account_email: newAccount.account_email || '',
        account_name: newAccount.account_name || '',
        compliance_contact: newAccount.compliance_contact || '',
      });
    } else {
      // Create mode or invalid edit state: Reset to default
      Object.assign(editableAccount, defaultAccountStructure);
    }
  }
}, { immediate: true, deep: true });

const closeModal = () => {
  // Parent now controls isSaving state related to API call,
  // but we still prevent closing if the modal's internal save action started.
  // However, since the API call is in the parent, isSaving here might not be necessary
  // unless you add local validation steps before emitting. Let's keep it simple.
  // if (!isSaving.value) { // Can likely remove this check if parent handles saving state fully
     emit('close');
  // }
};

const saveChanges = () => {
  // Basic validation example (can be expanded)
  if (!editableAccount.website_url || !editableAccount.account_email) {
      errorMessage.value = 'Website URL and Account Email are required.';
      return;
  }
  errorMessage.value = '';
  isSaving.value = true; // Indicate the save process has started locally

  // Emit the save event with the current data and mode
  // The actual API call will be handled by the parent component
  emit('save', { ...editableAccount });

  // Important: Parent component MUST reset the modal's isSaving state
  // after the API call finishes (success or error) if it wants to rely on it.
  // A simpler approach is for the parent to manage its own 'isSaving' state
  // and pass it down if needed, or just handle button disabling in the parent.
  // For now, we set it true here, and the parent will handle the API call.
  // Let's modify the parent to reset this modal's state upon completion.
};

// Expose method to reset saving state, called by parent
const resetSavingState = () => {
    isSaving.value = false;
};
// Expose method to set error message, called by parent
const setErrorMessage = (message) => {
    errorMessage.value = message;
};

defineExpose({ resetSavingState, setErrorMessage });


</script>

<style scoped>
/* Styles remain the same */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000; /* Ensure it's above other content */
}

.modal-content {
  background-color: white;
  padding: 20px 30px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  width: 90%;
  max-width: 500px; /* Adjust max-width as needed */
}

h3 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #333;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 600;
  color: #555;
}

.form-group input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box; /* Include padding and border in element's total width/height */
}

.modal-actions {
  margin-top: 25px;
  display: flex;
  justify-content: flex-end;
  gap: 10px; /* Add space between buttons */
}

.modal-actions button {
  padding: 8px 15px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95em;
}

.modal-actions button[type="submit"] {
  background-color: #007bff; /* Example primary color */
  color: white;
}
.modal-actions button[type="submit"]:disabled {
  background-color: #a0cfff;
  cursor: not-allowed;
}

.modal-actions button[type="button"] {
  background-color: #f0f0f0; /* Example secondary/cancel color */
  color: #333;
}
.modal-actions button[type="button"]:disabled {
  background-color: #e0e0e0;
  cursor: not-allowed;
}

.error-message {
  color: #d9534f;
  background-color: #f2dede;
  border: 1px solid #ebccd1;
  padding: 0.8rem;
  border-radius: 4px;
  margin-top: 15px;
  margin-bottom: 10px;
  font-size: 0.9em;
}

.saving-message {
    margin-top: 15px;
    color: #555;
    font-style: italic;
}
</style>
