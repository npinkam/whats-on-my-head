<template>
  <div ref="mapContainer" class="w-full h-full"/>
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

const emit = defineEmits<{
  mapMove: [center: { lat: number; lng: number }]
}>()

const config = useRuntimeConfig()
const apiBase = config.public.apiBase

const mapContainer = ref<HTMLDivElement>()
let map: L.Map | null = null
let markers: L.LayerGroup | null = null
const markerMap = new Map<string, L.CircleMarker>()
let activeTrail: L.Polyline | null = null

onMounted(() => {
  if (!mapContainer.value) return

  map = L.map(mapContainer.value).setView(props.center || [40.7128, -74.0060], 3)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map)

  markers = L.layerGroup().addTo(map)

  map.on('moveend', () => {
    const center = map!.getCenter()
    emit('mapMove', { lat: center.lat, lng: center.lng })
  })

  map.on('click', () => {
    if (activeTrail) {
      map!.removeLayer(activeTrail)
      activeTrail = null
    }
  })
})

watch(
  () => props.satellites,
  (newSatellites) => {
    if (!markers || !map) return

    const incomingNames = new Set(newSatellites.map(s => s.name))

    for (const [name, marker] of markerMap) {
      if (!incomingNames.has(name)) {
        markers.removeLayer(marker)
        markerMap.delete(name)
      }
    }

    for (const sat of newSatellites) {
      const existing = markerMap.get(sat.name)
      if (existing) {
        existing.setLatLng([sat.latitude, sat.longitude])
        existing.setStyle({
          fillColor: sat.is_visible ? '#3b82f6' : '#6b7280'
        })
        if (existing.isPopupOpen()) {
          existing.setPopupContent(popupContent(sat))
        }
      } else {
        const marker = L.circleMarker([sat.latitude, sat.longitude], {
          radius: 6,
          fillColor: sat.is_visible ? '#3b82f6' : '#6b7280',
          color: '#fff',
          weight: 1,
          opacity: 1,
          fillOpacity: 0.8,
        })
        marker.bindPopup(popupContent(sat), {
          closeButton: true,
          autoClose: false,
          closeOnClick: false,
        })
        marker.on('click', async (e) => {
          L.DomEvent.stopPropagation(e)
          await loadTrajectory(sat.name)
        })
        markers.addLayer(marker)
        markerMap.set(sat.name, marker)
      }
    }
  },
  { deep: true }
)

onUnmounted(() => {
  if (map) {
    map.remove()
    map = null
  }
})

function popupContent(sat: SatellitePosition): string {
  return `<div class="text-sm">
    <strong>${sat.name}</strong><br/>
    Alt: ${sat.altitude_deg.toFixed(1)}°<br/>
    Az: ${sat.azimuth_deg.toFixed(1)}°<br/>
    Range: ${sat.range_km.toFixed(0)} km
  </div>`
}

async function loadTrajectory(name: string) {
  try {
    const resp = await fetch(
      `${apiBase}/api/satellites/${encodeURIComponent(name)}/trajectory?steps=200`
    )
    if (!resp.ok) return
    const data = await resp.json()
    const points = data.trajectory.map(
      (p: { latitude: number; longitude: number }) => [p.latitude, p.longitude] as [number, number]
    )
    if (activeTrail) {
      map!.removeLayer(activeTrail)
    }
    activeTrail = L.polyline(points, {
      color: '#3b82f6', weight: 2, opacity: 0.7, dashArray: '5, 5'
    }).addTo(map!)
  } catch {
    // ignore fetch errors
  }
}
</script>