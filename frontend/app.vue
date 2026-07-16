<template>
  <div class="min-h-screen bg-gray-100">
    <div class="container mx-auto px-4 py-8">
      <header class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900">SkyRadar</h1>
        <p class="text-gray-600">Real-time satellite tracking</p>
      </header>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
<div class="lg:col-span-2">
            <div class="bg-white rounded-lg shadow p-6">
              <div class="h-96">
                <ClientOnly>
                  <SatelliteMap :satellites="satellites" :center="[latitude, longitude]" />
                </ClientOnly>
              </div>
            </div>
          </div>

        <div class="space-y-6">
          <div class="bg-white rounded-lg shadow p-6">
            <h2 class="text-xl font-semibold mb-4">Location</h2>
            <form @submit.prevent="updateLocation" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700">Latitude</label>
                <input
                  v-model="latitude"
                  type="number"
                  step="0.0001"
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  placeholder="40.7128"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">Longitude</label>
                <input
                  v-model="longitude"
                  type="number"
                  step="0.0001"
                  class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  placeholder="-74.0060"
                />
              </div>
              <button
                type="submit"
                class="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Update Location
              </button>
            </form>
          </div>

          <div class="bg-white rounded-lg shadow p-6">
            <h2 class="text-xl font-semibold mb-4">Connection</h2>
            <div class="flex items-center space-x-2">
              <div class="w-3 h-3 rounded-full" :class="connected ? 'bg-green-500' : 'bg-red-500'"></div>
              <span class="text-sm text-gray-600">{{ connected ? 'Connected' : 'Disconnected' }}</span>
            </div>
          </div>

          <div class="bg-white rounded-lg shadow p-6">
            <h2 class="text-xl font-semibold mb-4">Satellites</h2>
            <p class="text-sm text-gray-600">Overhead: {{ satellites.length }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const latitude = ref(40.7128)
const longitude = ref(-74.0060)

const { connected, satellites, connect, sendLocation } = useWebSocket()

const updateLocation = () => {
  sendLocation(latitude.value, longitude.value)
}

onMounted(() => {
  connect()
  sendLocation(latitude.value, longitude.value)
})
</script>
