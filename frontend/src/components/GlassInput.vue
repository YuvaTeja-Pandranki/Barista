<template>
  <div class="glass-input-wrapper">
    <label v-if="label" class="glass-label">{{ label }}</label>

    <select
      v-if="options.length"
      class="glass-field"
      :value="modelValue"
      @change="$emit('update:modelValue', $event.target.value)"
    >
      <option value="" disabled>{{ placeholder }}</option>
      <option v-for="opt in options" :key="opt" :value="opt">{{ opt }}</option>
    </select>

    <input
      v-else
      class="glass-field"
      :type="type"
      :placeholder="placeholder"
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value)"
    />
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: String, default: '' },
  label:       { type: String, default: '' },
  placeholder: { type: String, default: '' },
  type:        { type: String, default: 'text' },
  options:     { type: Array,  default: () => [] },
})

defineEmits(['update:modelValue'])
</script>

<style scoped>
.glass-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.glass-label {
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: rgba(55, 53, 80, 0.72);
  text-transform: uppercase;
}

.glass-field {
  width: 100%;
  padding: 14px 18px;
  font-size: 0.95rem;
  font-family: inherit;
  color: #2d2b42;
  background: rgba(255, 255, 255, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: 14px;
  outline: none;
  transition: border-color 0.3s, box-shadow 0.3s, background 0.3s;
  appearance: none;
  -webkit-appearance: none;
}

.glass-field::placeholder {
  color: rgba(55, 53, 80, 0.4);
}

.glass-field:focus {
  border-color: rgba(127, 90, 240, 0.6);
  box-shadow: 0 0 0 3px rgba(127, 90, 240, 0.15);
  background: rgba(255, 255, 255, 0.35);
}

select.glass-field {
  cursor: pointer;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='7'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%236b6b8d' stroke-width='1.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 16px center;
  padding-right: 40px;
}
</style>
