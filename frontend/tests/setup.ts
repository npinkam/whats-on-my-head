import { vi } from 'vitest'
import { ref, onUnmounted } from 'vue'

vi.stubGlobal('useRuntimeConfig', () => ({
  public: { apiBase: 'http://localhost:8000' },
}))

vi.stubGlobal('ref', ref)
vi.stubGlobal('onUnmounted', onUnmounted)
