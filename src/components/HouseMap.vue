<template>
  <div class="house-map-container">
    <div v-if="!mapLoaded && !error" class="loading">Map Loading...</div>
    <div id="map" class="map"></div>
    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="skippedHouses.length" class="warning">
      Warning: {{ skippedHouses.length }} house(s) could not be displayed due to geocoding issues.
    </div>
    <div v-if="successCount > 0" class="success">
      Successfully displayed {{ successCount }} house(s).
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

// Props: Expecting the JSON object of houses
const props = defineProps({
  houses: {
    type: Object,
    required: true,
    default: () => ({}),
  },
})

// State
const map = ref(null)
const error = ref('')
const skippedHouses = ref([])
const successCount = ref(0)
const mapLoaded = ref(false)
let googleMap = null
let markers = []

// Get API key from environment (Vite)
const apiKey = import.meta.env.VITE_GOOGLE_API_KEY
console.log('Google Maps API Key:', apiKey ? 'Set' : 'Missing')
if (!apiKey) {
  console.error('Google Maps API key is missing. Set VITE_GOOGLE_API_KEY in .env.')
  error.value = 'Map configuration error: Missing API key. Please contact support.'
}

// Normalize address for better geocoding
const normalizeAddress = (address) => {
  if (!address) return address
  let normalized = address.trim()
  const replacements = {
    Rd: 'Road',
    Ln: 'Lane',
    Dr: 'Drive',
    St: 'Street',
    Ave: 'Avenue',
    Blvd: 'Boulevard',
    Hwy: 'Highway',
    CR: 'County Road',
    'Vz CR': 'Vz County Road',
    'Us Highway': 'US Hwy',
    '#': '',
  }
  for (const [key, value] of Object.entries(replacements)) {
    normalized = normalized.replace(new RegExp(`\\b${key}\\b`, 'gi'), value)
  }
  return normalized
}

// Geocode an address using Google Maps Geocoding API
const geocodeAddress = async (address) => {
  try {
    const normalizedAddress = normalizeAddress(address)
    console.log(`Geocoding address: ${normalizedAddress}`)
    const response = await axios.get('https://maps.googleapis.com/maps/api/geocode/json', {
      params: {
        address: normalizedAddress,
        key: apiKey,
      },
    })
    console.log(`Geocoding response status for ${normalizedAddress}:`, response.data.status)
    if (response.data.results.length > 0) {
      const { lat, lng } = response.data.results[0].geometry.location
      return { lat, lng }
    }
    console.warn(
      `No geocoding result for address: ${address} (normalized: ${normalizedAddress}, status: ${response.data.status})`,
    )
    return null
  } catch (err) {
    console.error(`Geocoding error for address ${address}:`, err.message, err.response?.data)
    return null
  }
}

// Initialize the Google Map
const initMap = () => {
  console.log('Initializing Google Map')
  const mapElement = document.getElementById('map')
  if (!mapElement) {
    console.error('Map element (#map) not found in DOM')
    error.value = 'Map container not found. Please check the page structure.'
    return
  }
  try {
    googleMap = new google.maps.Map(mapElement, {
      center: { lat: 39.8283, lng: -98.5795 }, // Center of the US
      zoom: 4,
      mapId: 'ZILLOW_MAP', // Required for AdvancedMarkerElement
    })
    mapLoaded.value = true
    console.log('Map initialized successfully:', mapLoaded.value)
  } catch (err) {
    console.error('Failed to initialize Google Map:', err.message)
    error.value = 'Failed to initialize map. Please check API key and billing settings.'
  }
}

// Add houses to the map
const addHousesToMap = async () => {
  console.log('Adding houses to map, houses:', props.houses)
  const houseEntries = Object.entries(props.houses)
  if (houseEntries.length === 0) {
    error.value = 'No houses provided. Please check the data source.'
    console.warn('No houses provided to map.')
    return
  }

  let bounds = new google.maps.LatLngBounds()
  successCount.value = 0
  skippedHouses.value = []

  for (const [mlsId, house] of houseEntries) {
    if (!house.address) {
      console.warn(`Skipping house ${mlsId}: No address provided`)
      skippedHouses.value.push({ mlsId, address: 'No address' })
      continue
    }

    const coords = await geocodeAddress(house.address)
    if (!coords) {
      console.warn(`Skipping house ${mlsId}: Could not geocode address ${house.address}`)
      skippedHouses.value.push({ mlsId, address: house.address })
      continue
    }

    try {
      // Create PinElement for red pins
      const pin = new google.maps.marker.PinElement({
        background: '#ff0000', // Bright red background
        borderColor: '#8b0000', // Darker red border
        glyph: `${successCount.value + 1}`, // Numbered glyph (1–12)
        glyphColor: 'white',
        scale: 1.2, // 20% larger
      })

      // Create AdvancedMarkerElement with PinElement
      const marker = new google.maps.marker.AdvancedMarkerElement({
        position: coords,
        map: googleMap,
        content: pin.element,
        title: house.address,
        gmpClickable: true, // Ensure accessibility
      })
      markers.push(marker)

      // Create info window with external CSS classes and Zillow URL
      const infoWindowContent = `
        <div class="house-popup">
          <h3>${house.address}</h3>
          ${house.image ? `<img src="${house.image}" alt="House" class="popup-image" />` : ''}
          <p><strong>Price:</strong> ${house.price || 'N/A'}</p>
          <p><strong>Bedrooms:</strong> ${house.bedrooms || 'N/A'}</p>
          <p><strong>Bathrooms:</strong> ${house.bathrooms || 'N/A'}</p>
          <p><strong>Square Feet:</strong> ${house.square_feet || 'N/A'}</p>
          ${house.details_url ? `<a href="https://www.zillow.com${house.details_url}" target="_blank">View Details</a>` : ''}
        </div>
      `
      const infoWindow = new google.maps.InfoWindow({
        content: infoWindowContent,
      })

      // Add click listener for accessibility
      marker.addListener('click', () => {
        infoWindow.open(googleMap, marker)
      })

      // Extend bounds
      bounds.extend(coords)
      successCount.value++
    } catch (err) {
      console.error(`Failed to create marker for house ${mlsId}:`, err.message)
    }
  }

  console.log('Success count:', successCount.value)
  if (successCount.value > 0) {
    console.log(`Fitting map to ${successCount.value} markers`)
    try {
      googleMap.fitBounds(bounds, { padding: 50 })
    } catch (err) {
      console.error('Failed to fit map bounds:', err.message)
    }
  } else {
    error.value = 'No houses could be geocoded and displayed on the map.'
    console.warn('No markers added to map.')
  }
}

// Load Google Maps API dynamically
const loadGoogleMapsApi = () => {
  return new Promise((resolve, reject) => {
    if (window.google && window.google.maps && window.google.maps.marker) {
      console.log('Google Maps API already loaded')
      resolve()
      return
    }

    const callbackName = 'initGoogleMaps_' + Math.random().toString(36).substr(2, 9)
    window[callbackName] = () => {
      console.log('Google Maps API loaded successfully')
      resolve()
      delete window[callbackName]
    }

    const existingScripts = document.querySelectorAll('script[src*="maps.googleapis.com"]').length
    console.log('Existing Google Maps scripts:', existingScripts)
    if (existingScripts > 0) {
      console.warn('Multiple Google Maps API scripts detected. This may cause conflicts.')
    }

    const script = document.createElement('script')
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places,marker&callback=${callbackName}`
    script.async = true
    script.defer = true
    script.onerror = () => {
      console.error('Failed to load Google Maps API')
      reject(new Error('Failed to load Google Maps API'))
      error.value = 'Failed to load Google Maps API. Please check network or API key.'
    }

    console.log('Loading Google Maps API script')
    document.head.appendChild(script)
    console.log('Google Maps API script appended')
  })
}

// Lifecycle hooks
onMounted(async () => {
  console.log('HouseMap component mounted, Vite port: 5173')
  if (!apiKey) return
  try {
    await loadGoogleMapsApi()
    initMap()
    await addHousesToMap()
  } catch (err) {
    console.error('Error in HouseMap setup:', err.message)
    error.value = 'Failed to load map: ' + err.message + '. Please try again later.'
  }
})

onUnmounted(() => {
  console.log('HouseMap component unmounted')
  markers.forEach((marker) => {
    google.maps.event.clearInstanceListeners(marker)
    marker.map = null
  })
  markers = []
  googleMap = null
})
</script>

<style scoped>
/* Ensure parent container supports height: 100% */
.house-map-container {
  position: relative;
  width: 100%;
  height: 100%;
}

.map {
  width: 100%;
  height: 100%;
}

.loading {
  position: absolute;
  top: 20px;
  left: 20px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 10px;
  border-radius: 5px;
  z-index: 1000;
}

.error {
  position: absolute;
  top: 10px;
  left: 10px;
  background: rgba(255, 0, 0, 0.8);
  color: white;
  padding: 10px;
  border-radius: 5px;
  z-index: 1000;
}

.warning {
  position: absolute;
  top: 50px;
  left: 10px;
  background: rgba(255, 165, 0, 0.8);
  color: white;
  padding: 10px;
  border-radius: 5px;
  z-index: 1000;
}

.success {
  position: absolute;
  top: 90px;
  left: 10px;
  background: rgba(0, 128, 0, 0.8);
  color: white;
  padding: 10px;
  border-radius: 5px;
  z-index: 1000;
}

/* Global styles for info window */
:global(.house-popup) {
  max-width: 250px;
  text-align: left;
  background: rgba(0, 0, 0, 0.8);
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
  color: white;
  font-family: 'Arial', sans-serif;
  transition: transform 0.2s ease-in-out;
}

:global(.house-popup h3) {
  font-size: 18px;
  margin: 0 0 10px;
  color: #ffd700;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.7);
}

:global(.house-popup img) {
  width: 100%;
  height: auto;
  border-radius: 5px;
  margin-bottom: 10px;
  border: 2px solid #ffd700;
}

:global(.house-popup p) {
  margin: 5px 0;
  font-size: 14px;
}

:global(.house-popup a) {
  color: #00b7eb;
  text-decoration: none;
  font-weight: bold;
  display: inline-block;
  margin-top: 5px;
}

:global(.house-popup a:hover) {
  color: #008c9e;
}
</style>
