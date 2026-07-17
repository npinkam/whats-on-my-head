<template>
  <div class="h-screen flex flex-col bg-gray-100 overflow-hidden">
    <header class="h-14 bg-slate-900 flex items-center gap-2 px-4 shadow-lg z-50 flex-shrink-0">
      <span class="text-2xl">🛰️</span>
      <div>
        <h1 class="text-lg font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent leading-tight">
          What's On My Head
        </h1>
        <p class="text-xs text-slate-400 -mt-0.5">real-time satellite tracker</p>
      </div>
      <div class="ml-4 px-2 py-0.5 bg-slate-800 rounded text-xs text-slate-300">
        {{ satellites.length }} overhead
      </div>
      <div
class="ml-auto flex items-center gap-1.5 px-2.5 py-1 rounded-full"
           :class="connected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'">
        <div
class="w-2 h-2 rounded-full"
             :class="connected ? 'bg-emerald-400' : 'bg-red-400'" />
        <span class="text-xs font-medium">{{ connected ? 'Live' : 'Offline' }}</span>
      </div>
    </header>
    <main class="flex-1 relative">
      <ClientOnly>
        <SatelliteMap :satellites="satellites" :center="[mapCenter.lat, mapCenter.lng]" @map-move="onMapMove" />
      </ClientOnly>
      <div class="absolute bottom-4 left-4 bg-white/90 backdrop-blur rounded-lg px-3 py-2 shadow z-[1000]">
        <span class="text-sm font-mono">{{ mapCenter.lat.toFixed(4) }}°, {{ mapCenter.lng.toFixed(4) }}°</span>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
const { connected, satellites, connect, sendLocation } = useWebSocket()

const mapCenter = ref({ lat: 40.7128, lng: -74.0060 })

const onMapMove = (center: { lat: number; lng: number }) => {
  mapCenter.value = center
  sendLocation(center.lat, center.lng)
}

onMounted(() => {
  connect()
})

watch(connected, (val) => {
  if (val) sendLocation(mapCenter.value.lat, mapCenter.value.lng)
})
</script>