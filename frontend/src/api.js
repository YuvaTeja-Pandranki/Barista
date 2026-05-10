import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

export async function getDrinkRecommendation({ mood_text, location }) {
  const { data } = await client.post('/recommend-drink', {
    mood_text,
    location,
  })
  return data
}

export async function fetchMenu() {
  const { data } = await client.get('/menu')
  return data
}

export async function submitFeedback(payload) {
  const { data } = await client.post('/feedback', payload)
  return data
}

export async function fetchWeather(location) {
  const { data } = await client.get('/weather', { params: { location } })
  return data
}
