<template>
  <div class="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] w-full max-w-md px-4">
    <div ref="searchContainer" class="relative">
      <!-- Search input -->
      <div class="flex items-center bg-white/95 backdrop-blur rounded-lg shadow-lg border border-slate-200 focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-400/20 transition-all">
        <span class="pl-3 pr-1 text-slate-400">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </span>
        <input
          ref="inputEl"
          v-model="query"
          type="text"
          placeholder="Search satellites..."
          class="flex-1 px-2 py-2.5 text-sm bg-transparent outline-none text-slate-800 placeholder-slate-400"
          autocomplete="off"
          spellcheck="false"
          @keydown="onKeydown"
          @focus="onFocus"
        >
        <button
          v-if="query"
          class="px-2 py-2.5 text-slate-400 hover:text-slate-600 transition-colors"
          @click="clear"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <span v-if="loading" class="pr-3">
          <svg class="animate-spin h-4 w-4 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </span>
      </div>

      <!-- Dropdown -->
      <div
        v-if="showDropdown"
        class="absolute left-0 right-0 mt-1 bg-white/98 backdrop-blur rounded-lg shadow-xl border border-slate-200 overflow-hidden max-h-80 overflow-y-auto"
      >
        <!-- Error state -->
        <div v-if="error" class="px-4 py-3 text-sm text-red-600">
          {{ error }}
        </div>

        <!-- Empty state -->
        <div v-else-if="query.length > 0 && !loading && results.length === 0" class="px-4 py-3 text-sm text-slate-500">
          No satellites found for "{{ query }}"
        </div>

        <!-- Results list -->
        <ul v-else-if="results.length > 0" class="py-1">
          <li
            v-for="(sat, index) in results"
            :key="sat.norad_cat_id"
            ref="resultItems"
            class="px-4 py-2.5 cursor-pointer flex items-center gap-2 transition-colors"
            :data-satellite-item="true"
            :class="index === highlightedIndex ? 'bg-blue-50 text-blue-700' : 'text-slate-700 hover:bg-slate-50'"
            @mousedown.prevent="select(sat)"
            @mouseenter="highlightedIndex = index"
          >
            <span class="text-base">🛰️</span>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium truncate">{{ sat.name }}</div>
              <div class="text-xs text-slate-400">NORAD {{ sat.norad_cat_id }}</div>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface SatelliteResult {
  name: string
  norad_cat_id: number
}

const emit = defineEmits<{
  select: [satellite: SatelliteResult]
}>()

const config = useRuntimeConfig()
const apiBase = config.public.apiBase

const query = ref('')
const results = ref<SatelliteResult[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const highlightedIndex = ref(-1)
const showDropdown = ref(false)

const searchContainer = ref<HTMLDivElement>()
const inputEl = ref<HTMLInputElement>()
const resultItems = ref<HTMLElement[]>([])

let abortController: AbortController | null = null
let debounceTimer: ReturnType<typeof setTimeout> | null = null

// Debounced search
watch(query, (newVal) => {
  if (debounceTimer) clearTimeout(debounceTimer)

  if (!newVal.trim()) {
    results.value = []
    highlightedIndex.value = -1
    error.value = null
    showDropdown.value = false
    return
  }

  debounceTimer = setTimeout(() => {
    search(newVal.trim())
  }, 150)
})

async function search(q: string) {
  // Cancel previous request
  if (abortController) {
    abortController.abort()
  }
  abortController = new AbortController()

  loading.value = true
  error.value = null

  try {
    const resp = await fetch(
      `${apiBase}/api/satellites/search?q=${encodeURIComponent(q)}&limit=10`,
      { signal: abortController.signal }
    )
    if (!resp.ok) {
      throw new Error(`Search failed (${resp.status})`)
    }
    const data = await resp.json()
    results.value = data.results
    highlightedIndex.value = results.value.length > 0 ? 0 : -1
    showDropdown.value = true
  } catch (e: unknown) {
    if (e instanceof DOMException && e.name === 'AbortError') return
    error.value = e instanceof Error ? e.message : 'Search failed'
    results.value = []
    showDropdown.value = true
  } finally {
    loading.value = false
  }
}

function select(sat: SatelliteResult) {
  emit('select', sat)
  clear()
}

function clear() {
  query.value = ''
  results.value = []
  highlightedIndex.value = -1
  error.value = null
  showDropdown.value = false
  inputEl.value?.blur()
}

function onKeydown(e: KeyboardEvent) {
  if (!showDropdown.value) {
    if (e.key === 'ArrowDown' && results.value.length > 0) {
      showDropdown.value = true
      highlightedIndex.value = 0
      e.preventDefault()
    }
    return
  }

  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault()
      highlightedIndex.value = Math.min(highlightedIndex.value + 1, results.value.length - 1)
      scrollToHighlighted()
      break
    case 'ArrowUp':
      e.preventDefault()
      highlightedIndex.value = Math.max(highlightedIndex.value - 1, 0)
      scrollToHighlighted()
      break
    case 'Enter':
      e.preventDefault()
      if (highlightedIndex.value >= 0 && results.value[highlightedIndex.value]) {
        select(results.value[highlightedIndex.value])
      }
      break
    case 'Escape':
      e.preventDefault()
      clear()
      break
  }
}

function onFocus() {
  if (query.value.trim() && results.value.length > 0) {
    showDropdown.value = true
  }
}

function scrollToHighlighted() {
  // Let DOM update, then scroll highlighted item into view
  nextTick(() => {
    const items = document.querySelectorAll('[data-satellite-item]')
    const item = items[highlightedIndex.value] as HTMLElement | undefined
    item?.scrollIntoView({ block: 'nearest' })
  })
}

// Click outside to close
function onClickOutside(e: MouseEvent) {
  if (searchContainer.value && !searchContainer.value.contains(e.target as Node)) {
    showDropdown.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', onClickOutside, true)
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside, true)
  if (debounceTimer) clearTimeout(debounceTimer)
  if (abortController) abortController.abort()
})
</script>
