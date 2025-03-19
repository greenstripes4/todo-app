<template>
  <div class="navigation-group">
    <div class="navigation-group-header" @click="toggleGroup">
      {{ title }}
      <span class="arrow" :class="{ 'arrow-down': isOpen }"></span>
    </div>
    <ul class="navigation-group-items" v-show="isOpen">
      <slot></slot>
    </ul>
  </div>
</template>

<script setup>
import { ref, defineProps } from 'vue';

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  isOpen: {
    type: Boolean,
    default: false,
  },
});

const isOpen = ref(props.isOpen);

const toggleGroup = () => {
  isOpen.value = !isOpen.value;
};
</script>

<style scoped>
.navigation-group-header {
  cursor: pointer;
  padding: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #444; /* Darker background */
  color: #eee; /* Lighter text */
  border-bottom: 1px solid #555; /* Darker border */
  transition: background-color 0.2s ease; /* Smooth hover effect */
}

.navigation-group-header:hover {
  background-color: #555; /* Darker background on hover */
}

.navigation-group-items {
  list-style: none;
  padding: 0;
  margin: 0;
}

.arrow {
  border: solid #eee; /* Lighter arrow */
  border-width: 0 3px 3px 0;
  display: inline-block;
  padding: 3px;
  transition: transform 0.2s ease-in-out;
}

.arrow-down {
  transform: rotate(45deg);
  -webkit-transform: rotate(45deg);
}
</style>
