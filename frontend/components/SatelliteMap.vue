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
  viewportCount: [count: number]
}>()

const config = useRuntimeConfig()
const apiBase = config.public.apiBase

const mapContainer = ref<HTMLDivElement>()
let map: L.Map | null = null
let markers: L.LayerGroup | null = null
const markerMap = new Map<string, L.CircleMarker>()
const searchAdded = new Set<string>()
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
    emitViewportCount()
  })

  map.on('click', () => {
    map!.closePopup()
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

    // Remove markers that are no longer broadcast — except search-added ones
    for (const [name, marker] of markerMap) {
      if (!incomingNames.has(name) && !searchAdded.has(name)) {
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
        // This satellite is now managed by broadcast — remove from search-added
        searchAdded.delete(sat.name)
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
        marker.on('popupclose', () => {
          if (activeTrail) {
            map!.removeLayer(activeTrail)
            activeTrail = null
          }
        })
        markers.addLayer(marker)
        markerMap.set(sat.name, marker)
      }
    }

    emitViewportCount()
  },
  { deep: true }
)

function emitViewportCount() {
  if (!map || !markers) return
  const bounds = map.getBounds()
  let count = 0
  for (const marker of markerMap.values()) {
    if (bounds.contains(marker.getLatLng())) {
      count++
    }
  }
  emit('viewportCount', count)
}

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
    return points
  } catch {
    console.warn(`Failed to load trajectory for ${name}`)
    return undefined
  }
}

function flyToSatellite(name: string) {
  if (!map || !markers) return

  // If satellite is already on the map, fly to its marker
  const existingMarker = markerMap.get(name)
  if (existingMarker) {
    map.flyTo(existingMarker.getLatLng(), 6, { duration: 0.8 })
    existingMarker.openPopup()
    loadTrajectory(name)
    return
  }

  // Not in broadcast data — fetch trajectory and place a marker at its current position
  loadTrajectory(name).then((points) => {
    if (!points || points.length === 0) {
      console.warn(`No trajectory data for ${name}`)
      return
    }
    const mid = points[Math.floor(points.length / 2)]
    const latlng: [number, number] = [mid[0], mid[1]]

    const marker = L.circleMarker(latlng, {
      radius: 6,
      fillColor: '#3b82f6',
      color: '#fff',
      weight: 1,
      opacity: 1,
      fillOpacity: 0.8,
    })
    marker.bindPopup(
      `<div class="text-sm"><strong>${name}</strong><br/><span class="text-xs text-slate-400">Position estimated from orbital path</span></div>`,
      { closeButton: true, autoClose: false, closeOnClick: false }
    )
    marker.on('click', async (e) => {
      L.DomEvent.stopPropagation(e)
      await loadTrajectory(name)
    })
    marker.on('popupclose', () => {
      if (activeTrail) {
        map!.removeLayer(activeTrail)
        activeTrail = null
      }
    })
    markers!.addLayer(marker)
    markerMap.set(name, marker)
    searchAdded.add(name)

    map!.flyTo(latlng, 6, { duration: 0.8 })
    marker.openPopup()
  })
}

defineExpose({ flyToSatellite })
</script>
