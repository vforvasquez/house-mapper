<template>
  <div class="house-map-container">
    <div v-if="!mapLoaded && !error" class="loading">Loading...</div>
    <div id="map" class="house-map"></div>
    <!-- Map Type Dropdown -->
    <div class="map-type-control">
      <select v-model="selectedMapType" @change="updateMapType">
        <option value="roadmap">Roadmap</option>
        <option value="satellite">Satellite</option>
        <option value="hybrid">Hybrid</option>
        <option value="terrain">Terrain</option>
      </select>
    </div>
    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="skippedHouses.length" class="warning">
      Warning: {{ skippedHouses.length }} house(s) could not be displayed due to issues.
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
const selectedMapType = ref('roadmap') // Default map type
let googleMap = null
let markers = []

// Get API key from environment (Vite)
const apiKey = import.meta.env.VITE_GOOGLE_API_KEY
if (!apiKey) {
  console.error('Google Maps API key is missing. Set VITE_GOOGLE_API_KEY in .env.')
  error.value = 'Map configuration error: Missing API key. Please contact support.'
}

// Initialize the Google Map
const initMap = () => {
  const mapElement = document.getElementById('map')
  if (!mapElement) {
    error.value = 'Map container not found. Please check the page structure.'
    return
  }
  try {
    googleMap = new google.maps.Map(mapElement, {
      center: { lat: 31.9686, lng: -99.9018 }, // Center of Texas
      zoom: 6,
      mapId: 'ZILLOW_MAP',
      mapTypeId: google.maps.MapTypeId.ROADMAP, // Initial map type
      mapTypeControl: false, // Disable default map type control
    })
    mapLoaded.value = true
  } catch (err) {
    error.value = 'Failed to initialize map. Please check API key and billing settings.'
  }
}

// Update map type based on user selection
const updateMapType = () => {
  if (googleMap) {
    googleMap.setMapTypeId(selectedMapType.value)
  }
}

// Utility function to escape special characters for JavaScript and HTML
const escapeHtml = (str) => {
  if (!str) return 'No description available'
  return str
    .replace(/\\/g, '\\\\') // Escape backslashes first
    .replace(/'/g, "\\'") // Escape single quotes
    .replace(/"/g, '\\"') // Escape double quotes
    .replace(/`/g, '\\`') // Escape backticks
    .replace(/\n/g, ' ') // Replace newlines with spaces
    .replace(/\r/g, '') // Remove carriage returns
    .replace(/</g, '<') // Escape less-than for HTML
    .replace(/>/g, '>') // Escape greater-than for HTML
}

// Add houses to the map
const addHousesToMap = async () => {
  // Define global toggleDescription function
  window.toggleDescription = function (zpid) {
    const desc = document.getElementById(`description-${zpid}`)
    const button = event.target
    const isExpanded = desc.style.display === 'none'
    desc.style.display = isExpanded ? 'block' : 'none'
    button.textContent = isExpanded ? 'Hide Details' : 'View Details'
    button.setAttribute('aria-expanded', isExpanded ? 'true' : 'false')
  }

  const houseEntries = Object.entries(props.houses)
  if (houseEntries.length === 0) {
    error.value = 'No houses provided. Please check the data source.'
    return
  }

  let bounds = new google.maps.LatLngBounds()
  successCount.value = 0
  skippedHouses.value = []

  for (const [zpid, houseData] of houseEntries) {
    const house = houseData.property
    if (
      !house?.address?.streetAddress ||
      !house.address.city ||
      !house.address.state ||
      !house.address.zipcode
    ) {
      skippedHouses.value.push({ zpid, address: 'Invalid or missing address' })
      continue
    }

    // Construct full address
    const fullAddress = `${house.address.streetAddress}, ${house.address.city}, ${house.address.state} ${house.address.zipcode}`

    // Use provided lat/lng if available, otherwise geocode
    let coords = null
    if (house.latitude && house.longitude) {
      coords = { lat: house.latitude, lng: house.longitude }
    } else {
      console.error(`Failed to create marker for house ${zpid}:`, 'Missing lat/long')
    }

    if (!coords) {
      skippedHouses.value.push({ zpid, address: fullAddress })
      continue
    }

    try {
      const pin = new google.maps.marker.PinElement({
        background: '#ff0000',
        borderColor: '#8b0000',
        glyph: `${successCount.value + 1}`,
        glyphColor: 'white',
        scale: 1.2,
      })

      const marker = new google.maps.marker.AdvancedMarkerElement({
        position: coords,
        map: googleMap,
        content: pin.element,
        title: fullAddress,
        gmpClickable: true,
      })
      markers.push(marker)

      // Get image from hiResImageLink or first originalPhotos
      const imageUrl =
        house.hiResImageLink || house.originalPhotos?.[0]?.mixedSources?.jpeg?.[0]?.url || ''

      // Format price
      const safePrice = house.price ? `$${house.price.toLocaleString()}` : 'N/A'

      // Extract climate risk scores
      const climateRisks = houseData.odpPropertyModels?.climate || {}
      const floodRisk = climateRisks.floodSources?.primary?.riskScore?.label || 'N/A'
      const fireRisk = climateRisks.fireSources?.primary?.riskScore?.label || 'N/A'
      const heatRisk = climateRisks.heatSources?.primary?.riskScore?.label || 'N/A'

      // Prepare full description
      const fullDesc = house.description
        ? escapeHtml(house.description)
        : 'No description available'

      const infoWindowContent = `
        <div class="house-popup-wrapper">
          <div class="house-popup">
            <h3>${fullAddress}</h3>
            ${imageUrl ? `<img src="${imageUrl}" alt="House" class="popup-image" />` : ''}
            <p><strong>Price:</strong> ${safePrice}</p>
            <p><strong>Bedrooms:</strong> ${house.bedrooms || 'N/A'}</p>
            <p><strong>Bathrooms:</strong> ${house.bathrooms || 'N/A'}</p>
            <p><strong>Square Feet:</strong> ${house.livingArea || 'N/A'}</p>
            <p><strong>Lot Size:</strong> ${house.lotAreaValue || 'N/A'} ${house.lotAreaUnits || ''}</p>
            <p><strong>Days On Zillow:</strong> ${house.daysOnZillow || 'N/A'}</p>
            <button class="details-button" onclick="toggleDescription('${zpid}')" aria-expanded="false" aria-controls="description-${zpid}">View Details</button>
            <div id="description-${zpid}" style="display: none; margin-top: 10px;">
              <p id="desc-text-${zpid}">${fullDesc}</p>
            </div>
            ${house.hdpUrl ? `<a href="https://www.zillow.com${house.hdpUrl}" target="_blank">View Zillow Page</a>` : ''}
          </div>
        </div>
      `

      const infoWindow = new google.maps.InfoWindow({
        content: infoWindowContent,
      })

      marker.addListener('click', () => {
        infoWindow.open(googleMap, marker)
      })

      bounds.extend(coords)
      successCount.value++
    } catch (err) {
      console.error(`Failed to create marker for house ${zpid}:`, err.message)
    }
  }

  if (successCount.value > 0) {
    try {
      googleMap.fitBounds(bounds, { padding: 50 })
    } catch (err) {
      console.error('Failed to fit map bounds:', err.message)
    }
  } else {
    error.value = 'No houses could be displayed on the map.'
  }
}

// Load Google Maps API dynamically
const loadGoogleMapsApi = () => {
  return new Promise((resolve, reject) => {
    if (window.google && window.google.maps && window.google.maps.marker) {
      resolve()
      return
    }

    const callbackName = 'initGoogleMaps_' + Math.random().toString(36).substr(2, 9)
    window[callbackName] = () => {
      resolve()
      delete window[callbackName]
    }

    const script = document.createElement('script')
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places,marker&callback=${callbackName}`
    script.async = true
    script.defer = true
    script.onerror = () => {
      reject(new Error('Failed to load Google Maps API'))
      error.value = 'Failed to load Google Maps API. Please check network or API key.'
    }

    document.head.appendChild(script)
  })
}

// Lifecycle hooks
onMounted(async () => {
  if (!apiKey) return
  try {
    await loadGoogleMapsApi()
    initMap()
    await addHousesToMap()
  } catch (err) {
    error.value = 'Failed to load map: ' + err.message + '. Please try again later.'
  }
})

onUnmounted(() => {
  markers.forEach((marker) => {
    google.maps.event.clearInstanceListeners(marker)
    marker.map = null
  })
  markers = []
  googleMap = null
})
</script>

<style scoped lang="scss">
.house-map-container {
  position: relative;
  width: 100%;
  height: 100%;
}

.house-map {
  width: 100%;
  height: 100%;
}

.loading,
.error,
.warning,
.success {
  position: absolute;
  left: 10px;
  padding: 10px;
  border-radius: 5px;
  z-index: 1000;
  color: white;
}

.loading {
  top: 20px;
  background: rgba(0, 0, 0, 0.7);
}

.error {
  top: 10px;
  background: rgba(255, 0, 0, 0.8);
}

.warning {
  top: 50px;
  background: rgba(255, 165, 0, 0.8);
}

.success {
  top: 90px;
  background: rgba(0, 128, 0, 0.8);
}

/* Map Type Control Styling */
.map-type-control {
  position: absolute;
  top: 10px;
  right: 100px;
  z-index: 1000;
  color: black;
}

.map-type-control select {
  padding: 8px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.map-type-control select:focus {
  outline: none;
  border-color: #00b7eb;
}

:global(.house-popup-wrapper) {
  background: transparent !important;
}

:global(.house-popup) {
  max-width: 50vw;
  max-height: 50vh;
  overflow: auto;
  text-align: left;
  background: rgba(0, 0, 0, 0.8) !important;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
  font-size: 20px;
}

:global(.house-popup h3) {
  font-size: 24px;
  margin: 0 0 10px;
  color: #ffd700;
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
  font-size: 20px;
  line-height: 2;
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

:global(.house-popup button) {
  background: #008c9e;
  padding: 0.25em;
  border-radius: 3px;
  cursor: pointer;
  color: white;
  border: none;
  font-size: 14px;
  margin: 5px 0;
}

:global(.house-popup button:hover) {
  background: #00b7eb;
}

:global(.house-popup [id^='description-'] p) {
  font-size: 20px;
  line-height: 1.4;
  color: #ddd;
}
</style>
