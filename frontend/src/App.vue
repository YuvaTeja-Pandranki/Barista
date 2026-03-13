<template>
  <div class="app-bg">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>

    <main class="app-container">
      <header class="app-header">
        <h1 class="app-title">Visual Barista <span class="title-icon">☕</span></h1>
        <p class="app-subtitle">AI-powered mood-based coffee recommendations</p>
      </header>

      <section class="glass-card form-card">
        <!-- mood -->
        <div class="field-group">
          <div class="input-row">
            <GlassInput
              v-model="mood"
              label="Mood"
              placeholder="e.g. I feel burned out after work..."
              class="row-input"
            />
            <button
              class="mic-btn"
              :class="{ recording: isMoodRecording }"
              :disabled="!speechSupported"
              title="Speak your mood"
              @click="toggleMoodSpeech"
            >
              <Mic :size="18" />
            </button>
            <button class="pill-btn" @click="showMoodList = !showMoodList">
              {{ showMoodList ? 'Hide' : 'Show Moods' }}
            </button>
          </div>

          <p v-if="isMoodRecording" class="field-hint recording-hint">Listening...</p>

          <transition name="dropdown">
            <ul v-if="showMoodList" class="chip-grid">
              <li
                v-for="m in MOODS"
                :key="m"
                class="chip"
                :class="{ active: mood.trim().toLowerCase() === m }"
                @click="selectMood(m)"
              >{{ m }}</li>
            </ul>
          </transition>

          <p v-if="moodError" class="field-error">{{ moodError }}</p>
          <p v-else-if="!mood.trim()" class="field-hint">e.g. "I feel tired after work"</p>
        </div>

        <!-- location -->
        <div class="field-group">
          <div class="input-row">
            <GlassInput
              v-model="location"
              label="Location"
              placeholder="e.g. Seattle, Tokyo, London..."
              class="row-input"
            />
            <button
              class="mic-btn"
              :class="{ recording: isLocRecording }"
              :disabled="!speechSupported"
              title="Speak your location"
              @click="toggleLocSpeech"
            >
              <Mic :size="18" />
            </button>
          </div>

          <p v-if="isLocRecording" class="field-hint recording-hint">Listening...</p>
          <p v-if="locationError" class="field-error">{{ locationError }}</p>
          <p v-else-if="weatherError" class="field-error">{{ weatherError }}</p>
          <div v-else-if="weatherText" class="weather-preview">
            <p>Weather: {{ weatherText }}</p>
            <p v-if="weatherTemp !== null">Temperature: {{ weatherTemp }}°C</p>
            <p v-if="localTime">Local time: {{ localTime }}</p>
          </div>
        </div>

        <!-- action row -->
        <div class="action-row">
          <button
            class="generate-btn"
            :disabled="loading || !isFormValid"
            @click="generate"
          >
            <span v-if="loading" class="spinner"></span>
            <span v-else>Generate Drink</span>
          </button>
          <button class="pill-btn" @click="openDrinksModal">Show Drinks</button>
        </div>

        <p v-if="error" class="error-msg">{{ error }}</p>
      </section>

      <DrinkCard :drink="drink" @disliked="generate" />
    </main>

    <!-- drinks modal -->
    <transition name="modal-fade">
      <div v-if="showDrinksModal" class="modal-overlay" @click.self="showDrinksModal = false">
        <div class="modal-panel">
          <div class="modal-header">
            <h2 class="modal-title">Available Drinks</h2>
            <button class="modal-close" @click="showDrinksModal = false">&times;</button>
          </div>
          <ul v-if="menuDrinks.length" class="drinks-list">
            <li v-for="d in menuDrinks" :key="d.drink_name" class="drinks-row">
              <span class="drinks-name">{{ d.drink_name }}</span>
              <span class="drinks-price">${{ d.price.toFixed(2) }}</span>
            </li>
          </ul>
          <p v-else class="drinks-loading">Loading menu...</p>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { Mic } from 'lucide-vue-next'
import GlassInput from './components/GlassInput.vue'
import DrinkCard from './components/DrinkCard.vue'
import { getDrinkRecommendation, fetchMenu } from './api'
import axios from 'axios'

const MOODS = [
  'happy', 'relaxed', 'stressed', 'tired', 'excited',
  'calm', 'focused', 'sleepy', 'energetic', 'anxious',
  'bored', 'motivated', 'sad', 'joyful', 'curious',
  'content', 'restless', 'peaceful', 'creative', 'hungry',
]

const WEATHER_KEY = import.meta.env.VITE_WEATHER_API_KEY || ''

const mood            = ref('')
const location        = ref('')
const drink           = ref(null)
const loading         = ref(false)
const error           = ref('')
const showMoodList    = ref(false)
const weatherText     = ref('')
const weatherTemp     = ref(null)
const localTime       = ref('')
const weatherError    = ref('')
const showDrinksModal = ref(false)
const menuDrinks      = ref([])

let weatherTimer = null

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
const speechSupported = !!SpeechRecognition
const isMoodRecording = ref(false)
const isLocRecording  = ref(false)

let moodRecognition = null
let locRecognition  = null

if (speechSupported) {
  moodRecognition = new SpeechRecognition()
  moodRecognition.lang = 'en-US'
  moodRecognition.interimResults = false
  moodRecognition.maxAlternatives = 1
  moodRecognition.addEventListener('result', (e) => {
    mood.value = e.results[0][0].transcript
    isMoodRecording.value = false
  })
  moodRecognition.addEventListener('error', () => { isMoodRecording.value = false })
  moodRecognition.addEventListener('end', () => { isMoodRecording.value = false })

  locRecognition = new SpeechRecognition()
  locRecognition.lang = 'en-US'
  locRecognition.interimResults = false
  locRecognition.maxAlternatives = 1
  locRecognition.addEventListener('result', (e) => {
    location.value = e.results[0][0].transcript
    isLocRecording.value = false
  })
  locRecognition.addEventListener('error', () => { isLocRecording.value = false })
  locRecognition.addEventListener('end', () => { isLocRecording.value = false })
}

function toggleMoodSpeech() {
  if (!moodRecognition) return
  if (isMoodRecording.value) { moodRecognition.stop(); isMoodRecording.value = false }
  else { moodRecognition.start(); isMoodRecording.value = true }
}

function toggleLocSpeech() {
  if (!locRecognition) return
  if (isLocRecording.value) { locRecognition.stop(); isLocRecording.value = false }
  else { locRecognition.start(); isLocRecording.value = true }
}

onBeforeUnmount(() => {
  if (moodRecognition && isMoodRecording.value) moodRecognition.stop()
  if (locRecognition && isLocRecording.value) locRecognition.stop()
})

function normalizeLocation(text) {
  return text.trim().replace(/\s+/g, ' ')
}

function selectMood(m) {
  mood.value = m
  showMoodList.value = false
}

async function openDrinksModal() {
  showDrinksModal.value = true
  if (!menuDrinks.value.length) {
    try {
      menuDrinks.value = await fetchMenu()
    } catch {
      menuDrinks.value = []
    }
  }
}

const moodSignals = [
  'tired', 'exhausted', 'happy', 'sad', 'relaxed', 'excited',
  'stressed', 'energetic', 'calm', 'anxious', 'bored', 'motivated',
  'sleepy', 'burned', 'active', 'great', 'good', 'awful', 'terrible',
  'overwhelmed', 'joyful', 'curious', 'creative', 'content', 'restless',
  'peaceful', 'hungry', 'focused', 'lazy', 'drained', 'cozy', 'chill',
  'angry', 'frustrated', 'lonely', 'cheerful', 'pumped', 'wired',
  'mellow', 'gloomy',
]

const moodError = ref('')

function hasMoodSignal(text) {
  const lower = text.toLowerCase()
  return moodSignals.some(kw => lower.includes(kw))
}

watch(mood, (val) => {
  const trimmed = val.trim()
  if (!trimmed) { moodError.value = ''; return }
  moodError.value = hasMoodSignal(trimmed)
    ? ''
    : 'Describe your mood better (e.g. "I feel tired after work")'
})

const locationRegex = /^[a-zA-Z\s]{3,}$/
const locationError = ref('')

function validateLocation(text) {
  return locationRegex.test(text.trim())
}

const isFormValid = computed(() =>
  mood.value.trim()
  && !moodError.value
  && location.value.trim()
  && !locationError.value
  && !weatherError.value
)

watch(location, (val) => {
  clearTimeout(weatherTimer)
  weatherText.value = ''
  weatherTemp.value = null
  localTime.value = ''
  weatherError.value = ''
  locationError.value = ''

  const trimmed = val.trim()
  if (!trimmed) return

  if (!validateLocation(trimmed)) {
    locationError.value = 'Invalid location'
    return
  }

  if (!WEATHER_KEY) return
  weatherTimer = setTimeout(() => fetchWeather(trimmed), 500)
})

async function fetchWeather(loc) {
  const normalizedLoc = loc.trim().toLowerCase()
  try {
    const { data } = await axios.get('https://api.weatherapi.com/v1/current.json', {
      params: { key: WEATHER_KEY, q: normalizedLoc },
      timeout: 8000,
    })

    const returnedCity = (data.location.name || '').toLowerCase()
    if (returnedCity !== normalizedLoc) {
      weatherText.value = ''
      weatherTemp.value = null
      localTime.value = ''
      locationError.value = 'Invalid location'
      return
    }

    weatherText.value = data.current.condition.text
    weatherTemp.value = Math.round(data.current.temp_c)
    weatherError.value = ''
    locationError.value = ''

    const raw = data.location.localtime
    if (raw) {
      const dt = new Date(raw.replace(' ', 'T'))
      localTime.value = dt.toLocaleTimeString('en-US', {
        hour: 'numeric', minute: '2-digit', hour12: true,
      })
    }
  } catch {
    weatherText.value = ''
    weatherTemp.value = null
    localTime.value = ''
    weatherError.value = 'Invalid location'
  }
}

async function generate() {
  error.value = ''
  drink.value = null
  loading.value = true

  try {
    drink.value = await getDrinkRecommendation({
      mood_text: mood.value.trim(),
      location:  normalizeLocation(location.value),
    })
  } catch (err) {
    error.value =
      err.response?.data?.detail
      || err.message
      || 'Something went wrong — please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.app-bg {
  position: relative;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 60px 20px 80px;
  overflow: hidden;
}

.orb {
  position: fixed;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.55;
  pointer-events: none;
  z-index: 0;
}
.orb-1 {
  width: 420px; height: 420px;
  background: #c3b1f5;
  top: -80px; left: -100px;
  animation: drift 18s ease-in-out infinite alternate;
}
.orb-2 {
  width: 340px; height: 340px;
  background: #94c4f7;
  bottom: -60px; right: -80px;
  animation: drift 22s ease-in-out infinite alternate-reverse;
}
.orb-3 {
  width: 260px; height: 260px;
  background: #f7c4dc;
  top: 40%; left: 55%;
  animation: drift 15s ease-in-out infinite alternate;
}

@keyframes drift {
  0%   { transform: translate(0, 0) scale(1); }
  100% { transform: translate(40px, -30px) scale(1.08); }
}

.app-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 480px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.app-header { text-align: center; }

.app-title {
  font-size: 2.2rem;
  font-weight: 800;
  color: #1a1830;
  margin: 0;
}

.title-icon {
  display: inline-block;
  animation: wobble 2.5s ease-in-out infinite;
}

@keyframes wobble {
  0%, 100% { transform: rotate(0deg); }
  25%      { transform: rotate(8deg); }
  75%      { transform: rotate(-6deg); }
}

.app-subtitle {
  margin: 6px 0 0;
  font-size: 0.92rem;
  color: rgba(26, 24, 48, 0.5);
  letter-spacing: 0.01em;
}

.glass-card {
  background: rgba(255, 255, 255, 0.22);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
}

.form-card {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 32px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-error {
  margin: 0;
  font-size: 0.82rem;
  color: #e53e3e;
  padding-left: 4px;
  font-weight: 500;
}

.field-hint {
  margin: 0;
  font-size: 0.82rem;
  color: #555168;
  padding-left: 4px;
  font-style: italic;
}

.recording-hint {
  color: #7f5af0;
  font-style: normal;
  font-weight: 600;
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.4; }
}

.weather-preview {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: 4px;
}

.weather-preview p {
  margin: 0;
  font-size: 0.82rem;
  color: #555168;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.row-input {
  flex: 1;
  min-width: 0;
}

.mic-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.35);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  color: #3d3960;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mic-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.5);
  transform: scale(1.05);
}

.mic-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.mic-btn.recording {
  background: rgba(229, 62, 62, 0.15);
  border-color: rgba(229, 62, 62, 0.5);
  color: #e53e3e;
  box-shadow: 0 0 0 3px rgba(229, 62, 62, 0.12);
  animation: pulse 1s ease-in-out infinite;
}

.pill-btn {
  flex-shrink: 0;
  padding: 11px 14px;
  font-size: 0.78rem;
  font-weight: 600;
  font-family: inherit;
  letter-spacing: 0.02em;
  color: #3d3960;
  background: rgba(255, 255, 255, 0.35);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.pill-btn:hover {
  background: rgba(255, 255, 255, 0.5);
  transform: scale(1.03);
}

.chip-grid {
  list-style: none;
  margin: 0;
  padding: 8px 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  padding: 6px 14px;
  font-size: 0.8rem;
  font-weight: 500;
  color: #3d3960;
  background: rgba(127, 90, 240, 0.07);
  border: 1px solid rgba(127, 90, 240, 0.18);
  border-radius: 20px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.chip:hover {
  background: rgba(127, 90, 240, 0.15);
  border-color: rgba(127, 90, 240, 0.4);
}

.chip.active {
  background: rgba(127, 90, 240, 0.2);
  border-color: rgba(127, 90, 240, 0.55);
  color: #6942d0;
  font-weight: 600;
}

.dropdown-enter-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.dropdown-leave-active { transition: opacity 0.15s ease; }
.dropdown-enter-from   { opacity: 0; transform: translateY(-6px); }
.dropdown-leave-to     { opacity: 0; }

.action-row {
  display: flex;
  gap: 10px;
  align-items: stretch;
}

.generate-btn {
  flex: 1;
  padding: 15px;
  font-size: 1rem;
  font-weight: 700;
  font-family: inherit;
  color: #fff;
  background: linear-gradient(135deg, #7f5af0, #5f6fff);
  border: none;
  border-radius: 14px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.generate-btn:hover:not(:disabled) {
  transform: scale(1.04);
  box-shadow: 0 6px 28px rgba(127, 90, 240, 0.4);
}

.generate-btn:active:not(:disabled) {
  transform: scale(0.98);
}

.generate-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.65s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-msg {
  margin: 0;
  font-size: 0.85rem;
  color: #e53e3e;
  text-align: center;
  font-weight: 500;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

.modal-panel {
  width: 90%;
  max-width: 440px;
  max-height: 75vh;
  display: flex;
  flex-direction: column;
  padding: 28px;
  border-radius: 20px;
  background: rgba(30, 30, 40, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.3);
  color: #fff;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.6rem;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  line-height: 1;
  padding: 0 4px;
  transition: color 0.15s;
}

.modal-close:hover {
  color: #fff;
}

.drinks-list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.drinks-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.08);
  transition: background 0.15s ease;
}

.drinks-row:hover {
  background: rgba(255, 255, 255, 0.18);
}

.drinks-name {
  font-size: 0.88rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.92);
}

.drinks-price {
  font-size: 0.85rem;
  font-weight: 600;
  color: #8b7bff;
  flex-shrink: 0;
  margin-left: 12px;
}

.drinks-loading {
  text-align: center;
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.88rem;
  margin: 24px 0;
}

.modal-fade-enter-active { transition: opacity 0.25s ease; }
.modal-fade-enter-active .modal-panel {
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.modal-fade-leave-active { transition: opacity 0.15s ease; }
.modal-fade-enter-from { opacity: 0; }
.modal-fade-enter-from .modal-panel { transform: translateY(16px) scale(0.97); }
.modal-fade-leave-to { opacity: 0; }
</style>
