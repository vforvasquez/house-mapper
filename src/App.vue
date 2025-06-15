<script setup>
import { ref, onMounted } from 'vue'
import HouseMap from './components/HouseMap.vue'

const houseData = ref({})
const fetchError = ref('')

onMounted(async () => {
  try {
    const response = await fetch('/data/saved_houses.json')
    console.log('Fetch response status:', response.status, response.ok)
    if (!response.ok) throw new Error(`Failed to fetch houses: ${response.status}`)
    houseData.value = await response.json()
    console.log('Loaded houseData:', houseData.value)
  } catch (err) {
    console.error('Error fetching houses:', err.message)
    fetchError.value = `Failed to load house data: ${err.message}`
  }
})
</script>

<template>
  <div id="app-container">
    <div v-if="fetchError" class="error">{{ fetchError }}</div>
    <HouseMap v-else :houses="houseData" />
  </div>
</template>

<style>
#app-container {
  width: 100vw;
}
.error {
  background: rgba(255, 0, 0, 0.8);
  color: white;
  padding: 10px;
  margin: 10px;
  border-radius: 5px;
}
</style>
