<template>
  <div ref="mapContainer" class="w-full h-full"></div>
</template>

<script setup lang="ts">
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

interface SatellitePosition {
  name: string
  latitude: number
  longitude: number
  altitude_deg: number
  azimuth_deg: number
  range_km: number
  is_visible: boolean
}

const props = defineProps<{
  satellites: SatellitePosition[]
  center?: [number, number]
}>()

const mapContainer = ref<HTMLDivElement>()
let map: L.Map | null = null
let markers: L.LayerGroup | null = null

onMounted(() => {
  if (!mapContainer.value) return

  map = L.map(mapContainer.value).setView(props.center || [40.7128, -74.0060], 3)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map)

  markers = L.layerGroup().addTo(map)
})

watch(
  () => props.satellites,
  (newSatellites) => {
    if (!markers) return

    markers.clearLayers()

    newSatellites.forEach((sat) => {
      const marker = L.circleMarker([sat.latitude, sat.longitude], {
        radius: 4,
        fillColor: sat.is_visible ? '#3b82f6' : '#6b7280',
        color: '#fff',
        weight: 1,
        opacity: 1,
        fillOpacity: 0.8,
      })

      marker.bindPopup(`
        <div class="text-sm">
          <strong>${sat.name}</strong><br/>
          Alt: ${sat.altitude_deg.toFixed(1)}°<br/>
          Az: ${sat.azimuth_deg.toFixed(1)}°<br/>
          Range: ${sat.range_km.toFixed(0)} km
        </div>
      `)

      markers?.addLayer(marker)
    })
  },
  { deep: true }
)

watch(
  () => props.center,
  (newCenter) => {
    if (map && newCenter) {
      map.setView(newCenter, map.getZoom())
    }
  }
)

onUnmounted(() => {
  if (map) {
    map.remove()
    map = null
  }
})
</script>
