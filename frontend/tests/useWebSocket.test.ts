import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useWebSocket } from '../composables/useWebSocket'

describe('useWebSocket', () => {
  let wsInstances: any[]

  beforeEach(() => {
    wsInstances = []

    const MockWebSocket = vi.fn(function (this: any) {
      this.readyState = 1
      this.onopen = null
      this.onmessage = null
      this.onclose = null
      this.onerror = null
      this.send = vi.fn()
      this.close = vi.fn()
      wsInstances.push(this)
    }) as any
    MockWebSocket.CONNECTING = 0
    MockWebSocket.OPEN = 1
    MockWebSocket.CLOSING = 2
    MockWebSocket.CLOSED = 3

    vi.stubGlobal('WebSocket', MockWebSocket)
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('creates a WebSocket connection with correct URL', () => {
    const { connect } = useWebSocket()
    connect()

    const MockWebSocket = vi.mocked(globalThis.WebSocket as any)
    expect(MockWebSocket).toHaveBeenCalledTimes(1)
    const url = MockWebSocket.mock.calls[0][0] as string
    expect(url).toMatch(/^ws:\/\/localhost:8000\/ws\/client-/)
  })

  it('sets connected to true on open', () => {
    const { connect, connected } = useWebSocket()
    connect()

    wsInstances[0].onopen()
    expect(connected.value).toBe(true)
  })

  it('parses incoming satellite messages', () => {
    const { connect, satellites } = useWebSocket()
    connect()

    const message = {
      timestamp: '2024-01-01T00:00:00Z',
      observer: { latitude: 40.7128, longitude: -74.006 },
      satellites: [
        {
          name: 'ISS',
          latitude: 51.5,
          longitude: -0.1,
          altitude_deg: 45.0,
          azimuth_deg: 180.0,
          range_km: 500,
          is_visible: true,
        },
      ],
    }

    wsInstances[0].onmessage({ data: JSON.stringify(message) })
    expect(satellites.value).toEqual(message.satellites)
  })

  it('handles invalid JSON gracefully', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { connect } = useWebSocket()
    connect()

    wsInstances[0].onmessage({ data: 'invalid json{' })
    expect(consoleSpy).toHaveBeenCalled()
    consoleSpy.mockRestore()
  })

  it('sends location when WebSocket is open', () => {
    const { connect, sendLocation } = useWebSocket()
    connect()

    sendLocation(40.7128, -74.006)
    expect(wsInstances[0].send).toHaveBeenCalledWith(
      JSON.stringify({ latitude: 40.7128, longitude: -74.006 }),
    )
  })

  it('sets connected to false on close', () => {
    const { connect, connected } = useWebSocket()
    connect()

    wsInstances[0].onopen()
    expect(connected.value).toBe(true)

    wsInstances[0].onclose()
    expect(connected.value).toBe(false)
  })

  it('closes WebSocket on disconnect', () => {
    const { connect, disconnect } = useWebSocket()
    connect()

    disconnect()
    expect(wsInstances[0].close).toHaveBeenCalled()
  })
})
