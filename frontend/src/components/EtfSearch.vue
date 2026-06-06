<template>
  <div class="relative">
    <input
      v-model="query"
      type="text"
      :placeholder="placeholder"
      :readonly="readonly"
      :class="['w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
               readonly ? 'bg-gray-50 text-gray-400' : '']"
      @input="onInput"
      @focus="open = true"
      @blur="onBlur"
    />

    <!-- Dropdown -->
    <div
      v-if="open && results.length"
      class="absolute z-50 w-full bg-white border border-gray-200 rounded-lg shadow-lg mt-1 max-h-48 overflow-y-auto"
    >
      <div
        v-for="[code, name] in results" :key="code"
        class="flex items-center gap-3 px-3 py-2.5 hover:bg-blue-50 cursor-pointer text-sm border-b border-gray-50 last:border-0"
        @mousedown.prevent="select(code, name)"
      >
        <span class="font-mono font-semibold text-gray-800 w-16 flex-shrink-0">{{ code }}</span>
        <span class="text-gray-500 truncate">{{ name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { store } from '../store.js'

const props = defineProps({
  modelValue: { type: String, default: '' },
  name:       { type: String, default: '' },
  readonly:   { type: Boolean, default: false },
  placeholder:{ type: String, default: '输入代码或名称搜索' },
})

const emit = defineEmits(['update:modelValue', 'update:name'])

const query = ref(props.modelValue)
const open  = ref(false)

// Keep query in sync when parent resets the value
watch(() => props.modelValue, v => { query.value = v })

const results = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q || props.readonly) return []
  return Object.entries(store.etfList)
    .filter(([code, name]) => code.includes(q) || name.includes(q))
    .slice(0, 15)
})

function onInput() {
  const val = query.value.trim()
  emit('update:modelValue', val)
  // Auto-fill name if exact code entered
  if (store.etfList[val]) emit('update:name', store.etfList[val])
}

function select(code, name) {
  query.value = code
  emit('update:modelValue', code)
  emit('update:name', name)
  open.value = false
}

function onBlur() {
  setTimeout(() => { open.value = false }, 150)
}
</script>
