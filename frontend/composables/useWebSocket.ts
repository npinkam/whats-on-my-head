interface SatellitePosition {
  name: string
  latitude: number
  longitude: number
  altitude_deg: number
  azimuth_deg: number
  range_km: number
  is_visible: boolean
}

interface WebSocketMessage {
  timestamp: string
  observer: {
    latitude: number
    longitude: number
  }
  satellites: SatellitePosition[]
}

export const useWebSocket = () => {
  const config = useRuntimeConfig()
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const satellites = ref<SatellitePosition[]>([])
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 5
  const clientId = ref(`client-${Date.now()}`)

  const connect = () => {
    const wsUrl = config.public.apiBase.replace('http', 'ws')
    const url = `${wsUrl}/ws/${clientId.value}`

    try {
      ws.value = new WebSocket(url)

      ws.value.onopen = () => {
        connected.value = true
        reconnectAttempts.value = 0
        console.log('WebSocket connected')
      }

      ws.value.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data)
          satellites.value = data.satellites
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.value.onclose = () => {
        connected.value = false
        console.log('WebSocket disconnected')
        attemptReconnect()
      }

      ws.value.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (e) {
      console.error('Failed to create WebSocket:', e)
      attemptReconnect()
    }
  }

  const attemptReconnect = () => {
    if (reconnectAttempts.value < maxReconnectAttempts) {
      reconnectAttempts.value++
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000)
      console.log(`Attempting reconnect in ${delay}ms (attempt ${reconnectAttempts.value})`)
      setTimeout(connect, delay)
    }
  }

  const sendLocation = (latitude: number, longitude: number) => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ latitude, longitude }))
    }
  }

  const disconnect = () => {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    satellites,
    connect,
    disconnect,
    sendLocation,
  }
}
