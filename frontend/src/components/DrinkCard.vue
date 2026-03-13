<template>
  <transition name="card-fade">
    <div v-if="drink" class="drink-card">
      <img
        v-if="drink.image_url"
        :src="drink.image_url"
        :alt="drink.drink_name"
        class="drink-image"
      />

      <!-- header -->
      <div class="card-header">
        <span class="card-emoji">{{ drink.context?.mood_emoji || '☕' }}</span>
        <h2 class="drink-name">{{ drink.drink_name }}</h2>
      </div>

      <p class="drink-description">{{ drink.description }}</p>

      <!-- details table -->
      <div class="details-table">
        <div class="detail-row">
          <span class="detail-label">Base:</span>
          <span class="detail-value">{{ drink.base }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Temperature:</span>
          <span class="detail-value">{{ drink.temperature_label }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Ingredients:</span>
          <span class="detail-value">{{ drink.ingredients.join(', ') }}</span>
        </div>
        <div v-if="drink.customizations?.length" class="detail-row">
          <span class="detail-label">Customizations:</span>
          <span class="detail-value">{{ drink.customizations.join(', ') }}</span>
        </div>
      </div>

      <!-- why this blend -->
      <div v-if="drink.context" class="why-section">
        <h3 class="why-title">Why This Blend?</h3>
        <p class="why-item">Your mood: <strong>{{ capitalize(drink.context.mood) }}</strong></p>
        <p class="why-item">Weather: <strong>{{ drink.context.weather }}</strong></p>
        <p class="why-item">Time: <strong>{{ drink.context.time_of_day }}</strong></p>
        <p class="why-item">Temperature: <strong>{{ tempC }}°C</strong></p>
      </div>

      <!-- price + feedback -->
      <div class="card-footer">
        <span class="drink-price">${{ drink.price.toFixed(2) }}</span>
        <div class="feedback-btns">
          <button
            class="fb-btn fb-love"
            :disabled="feedbackSent"
            @click="sendFeedback('thumbs_up')"
          >
            👍 Love It
          </button>
          <button
            class="fb-btn fb-nope"
            :disabled="feedbackSent"
            @click="sendFeedback('thumbs_down')"
          >
            👎 Not for Me
          </button>
        </div>
      </div>
      <p v-if="feedbackSent && feedbackType === 'thumbs_down'" class="fb-thanks fb-next">
        {{ loadingNext ? 'Finding you something better... ☕' : 'Got it! Not for you.' }}
      </p>
      <p v-else-if="feedbackSent && feedbackType === 'thumbs_up'" class="fb-thanks fb-love">
        Glad you loved it! 🎉
      </p>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { submitFeedback } from '../api'

const props = defineProps({
  drink: { type: Object, default: null },
})

const emit = defineEmits(['disliked', 'liked'])

const feedbackSent    = ref(false)
const feedbackType    = ref(null)   // 'up' | 'down'
const loadingNext     = ref(false)

watch(() => props.drink, () => {
  feedbackSent.value = false
  feedbackType.value = null
  loadingNext.value  = false
})

function capitalize(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''
}

const tempC = computed(() => {
  if (!props.drink?.context?.temperature_f) return '--'
  return Math.round((props.drink.context.temperature_f - 32) * 5 / 9)
})

async function sendFeedback(type) {
  if (!props.drink || feedbackSent.value) return

  feedbackSent.value = true
  feedbackType.value = type

  const ctx = props.drink.context || {}
  try {
    await submitFeedback({
      drink_name: props.drink.drink_name,
      coffee_profile: {
        temperature: (props.drink.temperature_label || '').toLowerCase(),
        flavor: props.drink.ingredients[0] || 'unknown',
      },
      environment: {
        weather: ctx.weather || 'unknown',
      },
      feedback: type,
    })
  } catch {
    /* feedback stored even on API error */
  }

  if (type === 'thumbs_down') {
    loadingNext.value = true
    setTimeout(() => emit('disliked'), 1200)
  } else {
    emit('liked')
  }
}
</script>

<style scoped>
.drink-card {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  padding: 28px;
  animation: slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
  overflow: hidden;
}

.drink-image {
  width: 100%;
  max-height: 220px;
  object-fit: cover;
  border-radius: 14px;
  margin-bottom: 18px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.card-emoji { font-size: 1.6rem; }

.drink-name {
  font-size: 1.3rem;
  font-weight: 700;
  color: #2d2b42;
  margin: 0;
}

.drink-description {
  font-size: 0.88rem;
  color: rgba(55, 53, 80, 0.6);
  line-height: 1.5;
  margin: 0 0 16px;
}

.details-table {
  background: rgba(127, 90, 240, 0.04);
  border: 1px solid rgba(127, 90, 240, 0.12);
  border-radius: 14px;
  padding: 14px 18px;
  margin-bottom: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
}

.detail-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: #7f5af0;
  flex-shrink: 0;
}

.detail-value {
  font-size: 0.82rem;
  color: #2d2b42;
  text-align: right;
}

.why-section {
  background: rgba(127, 90, 240, 0.04);
  border: 1px solid rgba(127, 90, 240, 0.12);
  border-radius: 14px;
  padding: 14px 18px;
  margin-bottom: 16px;
}

.why-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: #7f5af0;
  margin: 0 0 8px;
}

.why-item {
  font-size: 0.82rem;
  color: rgba(55, 53, 80, 0.7);
  margin: 0 0 3px;
  line-height: 1.5;
}

.why-item strong {
  color: #5f6fff;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.drink-price {
  font-size: 1.35rem;
  font-weight: 700;
  background: linear-gradient(135deg, #7f5af0, #5f6fff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.feedback-btns {
  display: flex;
  gap: 8px;
}

.fb-btn {
  padding: 9px 16px;
  font-size: 0.78rem;
  font-weight: 600;
  font-family: inherit;
  border-radius: 12px;
  cursor: pointer;
  border: 1px solid;
  transition: all 0.2s ease;
}

.fb-love {
  background: rgba(72, 187, 120, 0.1);
  border-color: rgba(72, 187, 120, 0.3);
  color: #276749;
}

.fb-love:hover:not(:disabled) {
  background: rgba(72, 187, 120, 0.2);
  transform: scale(1.03);
}

.fb-nope {
  background: rgba(229, 62, 62, 0.08);
  border-color: rgba(229, 62, 62, 0.25);
  color: #9b2c2c;
}

.fb-nope:hover:not(:disabled) {
  background: rgba(229, 62, 62, 0.18);
  transform: scale(1.03);
}

.fb-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.fb-thanks {
  margin: 10px 0 0;
  font-size: 0.82rem;
  font-weight: 600;
  text-align: center;
  padding: 8px 14px;
  border-radius: 10px;
}

.fb-next {
  color: #c05621;
  background: rgba(237, 137, 54, 0.1);
  border: 1px solid rgba(237, 137, 54, 0.25);
}

.fb-love {
  color: #276749;
  background: rgba(72, 187, 120, 0.1);
  border: 1px solid rgba(72, 187, 120, 0.3);
}

.card-fade-enter-active {
  transition: opacity 0.4s ease, transform 0.4s ease;
}
.card-fade-leave-active {
  transition: opacity 0.25s ease;
}
.card-fade-enter-from {
  opacity: 0;
  transform: translateY(16px);
}
.card-fade-leave-to {
  opacity: 0;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
