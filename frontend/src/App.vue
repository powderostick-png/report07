<script setup>
import { reactive, ref } from 'vue'
import {
  Camera,
  CheckCircle2,
  ExternalLink,
  Globe2,
  MapPin,
  PackageCheck,
  Phone,
  Send,
  ShieldCheck,
  Sparkles,
  Truck,
  UserRound,
} from '@lucide/vue'
import viltroxLogo from './assets/viltrox-logo-white-cropped.png'

const form = reactive({
  fullName: '',
  accountName: '',
  phone: '',
  country: '',
  countryOther: '',
  stateProvince: '',
  city: '',
  postalCode: '',
  streetAddress: '',
  cameraVersion: '',
  cameraVersionOther: '',
  notes: '',
  glsConfirm: false,
})

const errors = ref({})
const isSubmitted = ref(false)
const isSubmitting = ref(false)
const submitError = ref('')
const trackingLookupFullName = ref('')
const trackingLookupMessage = ref('')
const trackingLookupNumber = ref('')
const trackingLookupUrl = ref('')
const isTrackingLookupLoading = ref(false)

const countries = [
  'Germany',
  'France',
  'Italy',
  'Spain',
  'Netherlands',
  'Belgium',
  'Poland',
  'Austria',
  'Sweden',
  'Denmark',
  'Finland',
  'Portugal',
  'United Kingdom',
  'United States',
  'Canada',
  'Australia',
  'Other',
]

const cameraVersions = ['Sony', 'Canon', 'Fujifilm', 'Nikon', 'Other']

const requiredFields = [
  ['fullName', 'Full name is required.'],
  ['accountName', 'Account name is required.'],
  ['phone', 'Phone number is required.'],
  ['country', 'Country or region is required.'],
  ['city', 'City is required.'],
  ['postalCode', 'Postal code is required.'],
  ['streetAddress', 'Address is required.'],
  ['cameraVersion', 'Camera version is required.'],
]

function validateForm() {
  const nextErrors = {}

  for (const [field, message] of requiredFields) {
    if (!String(form[field]).trim()) {
      nextErrors[field] = message
    }
  }

  if (form.country === 'Other' && !form.countryOther.trim()) {
    nextErrors.countryOther = 'Please enter the country or region.'
  }

  if (form.cameraVersion === 'Other' && !form.cameraVersionOther.trim()) {
    nextErrors.cameraVersionOther = 'Please enter the camera version.'
  }

  if (!form.glsConfirm) {
    nextErrors.glsConfirm = 'Please confirm delivery.'
  }

  errors.value = nextErrors
  return Object.keys(nextErrors).length === 0
}

function getCookie(name) {
  const cookie = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`))

  return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : ''
}

async function handleSubmit() {
  isSubmitted.value = false
  submitError.value = ''

  if (!validateForm()) {
    return
  }

  isSubmitting.value = true

  try {
    const response = await fetch('/api/shipping-information/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify({ ...form }),
    })
    const result = await response.json().catch(() => ({}))

    if (!response.ok) {
      errors.value = { ...errors.value, ...(result.errors || {}) }
      submitError.value = result.message || 'Unable to save your request. Please check the form and try again.'
      return
    }

    isSubmitted.value = true
  } catch (error) {
    submitError.value = 'Unable to connect to the server. Please try again later.'
  } finally {
    isSubmitting.value = false
  }
}

async function handleTrackingLookup() {
  const fullName = trackingLookupFullName.value.trim()
  trackingLookupMessage.value = ''
  trackingLookupNumber.value = ''
  trackingLookupUrl.value = ''

  if (!fullName) {
    trackingLookupMessage.value = 'Please enter your full name.'
    return
  }

  isTrackingLookupLoading.value = true

  try {
    const response = await fetch(`/api/tracking-lookup/?fullName=${encodeURIComponent(fullName)}`)
    const result = await response.json().catch(() => ({}))

    trackingLookupMessage.value = result.message || 'Unable to check tracking status.'

    if (response.ok && result.trackingNumber) {
      trackingLookupNumber.value = result.trackingNumber
      trackingLookupUrl.value = result.trackingUrl || `https://t.17track.net/en#nums=${encodeURIComponent(result.trackingNumber)}`
    }
  } catch (error) {
    trackingLookupMessage.value = 'Unable to connect to the server. Please try again later.'
  } finally {
    isTrackingLookupLoading.value = false
  }
}
</script>

<template>
  <main>
    <section class="site-hero">
      <div class="page-shell hero-shell">
    <header class="topbar">
      <a class="brand" href="/" aria-label="Viltrox influencer sample portal">
        <img class="brand-logo" :src="viltroxLogo" alt="Viltrox" />
      </a>

      <nav class="top-actions" aria-label="Quick links">
        <a href="https://t.17track.net/" target="_blank" rel="noreferrer">
          <PackageCheck :size="18" />
          Track
        </a>
        <a href="https://viltrox.com/pages/join-affiliate-tutorial" target="_blank" rel="noreferrer">
          <Sparkles :size="18" />
          Affiliate
        </a>
      </nav>
    </header>

    <section class="hero compact-hero">
      <div class="hero-copy">
        <p class="eyebrow">Creator sample portal</p>
        <h1>Apply for your Viltrox sample kit.</h1>
        <p class="lede">
          Submit your shipping details once. The team will prepare the package, upload tracking later, and keep the collaboration moving.
        </p>

        <div class="hero-actions">
          <a class="hero-button" href="#tracking">
            <PackageCheck :size="19" />
            Track your shipment
          </a>
          <a class="hero-button" href="#affiliate">
            <Sparkles :size="19" />
            Earn commission
          </a>
        </div>

        <div class="hero-badges" aria-label="Shipping notes">
          <span>
            <Truck :size="18" />
            Shipping time: 7-15 days
          </span>
          <span>
            <ShieldCheck :size="18" />
            GLS address required
          </span>
        </div>
      </div>
    </section>
      </div>
    </section>

    <section class="page-shell content-grid">
      <form id="request" class="request-form" novalidate @submit.prevent="handleSubmit">
        <div class="section-heading">
          <p>Sample request form</p>
          <h2>Shipping information</h2>
        </div>

        <div class="form-grid">
          <label class="field">
            <span>Full Name *</span>
            <span class="input-wrap">
              <UserRound :size="18" />
              <input v-model.trim="form.fullName" type="text" autocomplete="name" placeholder="Jane Cooper" />
            </span>
            <small v-if="errors.fullName">{{ errors.fullName }}</small>
          </label>

          <label class="field">
            <span>Account / Handle *</span>
            <span class="input-wrap">
              <Camera :size="18" />
              <input v-model.trim="form.accountName" type="text" placeholder="@yourchannel" />
            </span>
            <small v-if="errors.accountName">{{ errors.accountName }}</small>
          </label>

          <label class="field">
            <span>Phone *</span>
            <span class="input-wrap">
              <Phone :size="18" />
              <input v-model.trim="form.phone" type="tel" autocomplete="tel" placeholder="+49 170 0000000" />
            </span>
            <small v-if="errors.phone">{{ errors.phone }}</small>
          </label>

          <label class="field">
            <span>Country / Region *</span>
            <span class="input-wrap">
              <Globe2 :size="18" />
              <select v-model="form.country" autocomplete="country-name">
                <option value="" disabled>Select country / region</option>
                <option v-for="country in countries" :key="country" :value="country">{{ country }}</option>
              </select>
            </span>
            <small v-if="errors.country">{{ errors.country }}</small>
          </label>

          <label v-if="form.country === 'Other'" class="field">
            <span>Country / Region Details *</span>
            <span class="input-wrap">
              <Globe2 :size="18" />
              <input v-model.trim="form.countryOther" type="text" placeholder="Enter country / region" />
            </span>
            <small v-if="errors.countryOther">{{ errors.countryOther }}</small>
          </label>

          <label class="field">
            <span>State / Region</span>
            <span class="input-wrap">
              <MapPin :size="18" />
              <input v-model.trim="form.stateProvince" type="text" autocomplete="address-level1" placeholder="State / Region" />
            </span>
          </label>

          <label class="field">
            <span>City *</span>
            <span class="input-wrap">
              <MapPin :size="18" />
              <input v-model.trim="form.city" type="text" autocomplete="address-level2" placeholder="Berlin" />
            </span>
            <small v-if="errors.city">{{ errors.city }}</small>
          </label>

          <label class="field">
            <span>Postal Code *</span>
            <span class="input-wrap">
              <MapPin :size="18" />
              <input v-model.trim="form.postalCode" type="text" autocomplete="postal-code" placeholder="10115" />
            </span>
            <small v-if="errors.postalCode">{{ errors.postalCode }}</small>
          </label>

          <label class="field">
            <span>Address *</span>
            <span class="input-wrap">
              <MapPin :size="18" />
              <input
                v-model.trim="form.streetAddress"
                type="text"
                autocomplete="street-address"
              />
            </span>
            <small v-if="errors.streetAddress">{{ errors.streetAddress }}</small>
          </label>

          <label class="field full">
            <span>Camera Version *</span>
            <span class="input-wrap">
              <Camera :size="18" />
              <select v-model="form.cameraVersion">
                <option value="" disabled>Select camera version</option>
                <option v-for="version in cameraVersions" :key="version" :value="version">{{ version }}</option>
              </select>
            </span>
            <small v-if="errors.cameraVersion">{{ errors.cameraVersion }}</small>
          </label>

          <label v-if="form.cameraVersion === 'Other'" class="field full">
            <span>Camera Version Details *</span>
            <span class="input-wrap">
              <Camera :size="18" />
              <input v-model.trim="form.cameraVersionOther" type="text" placeholder="Enter camera brand or mount" />
            </span>
            <small v-if="errors.cameraVersionOther">{{ errors.cameraVersionOther }}</small>
          </label>

          <label class="field full">
            <span>Notes</span>
            <textarea v-model.trim="form.notes" rows="4" placeholder="Content schedule, delivery notes, preferred contact time..." />
          </label>
        </div>

        <label class="confirm-line">
          <input v-model="form.glsConfirm" type="checkbox" />
          <span>
            I confirm this address can receive GLS delivery if it is in Europe.
          </span>
        </label>
        <small v-if="errors.glsConfirm" class="checkbox-error">{{ errors.glsConfirm }}</small>

        <button class="submit-button" type="submit" :disabled="isSubmitting">
          <Send :size="19" />
          {{ isSubmitting ? 'Submitting...' : 'Submit sample request' }}
        </button>

        <div v-if="isSubmitted" class="success-message submit-status" role="status">
          <CheckCircle2 :size="20" />
          Request submitted successfully. Your shipping information has been saved.
        </div>

        <div v-if="submitError" class="error-message submit-status" role="alert">
          {{ submitError }}
        </div>
      </form>

      <aside class="side-panel">
        <article id="tracking" class="info-card tracking-card">
          <div class="card-icon">
            <PackageCheck :size="22" />
          </div>
          <h2>Track your shipment</h2>
          <p>
            After the team uploads your tracking number, use your full name to find the shipment status.
          </p>
          <label>
            <span>Full Name</span>
            <input v-model.trim="trackingLookupFullName" type="text" placeholder="Jane Cooper" />
          </label>
          <button class="lookup-button" type="button" :disabled="isTrackingLookupLoading" @click="handleTrackingLookup">
            {{ isTrackingLookupLoading ? 'Checking...' : 'Check tracking status' }}
          </button>
          <p v-if="trackingLookupMessage" class="tracking-note">{{ trackingLookupMessage }}</p>
          <p v-if="trackingLookupNumber" class="tracking-number">
            Tracking Number: <strong>{{ trackingLookupNumber }}</strong>
          </p>
          <a
            class="side-link secondary-link"
            :href="trackingLookupUrl || 'https://t.17track.net/'"
            target="_blank"
            rel="noreferrer"
          >
            {{ trackingLookupUrl ? 'Track on 17TRACK' : 'Open 17TRACK' }}
            <ExternalLink :size="17" />
          </a>
        </article>

        <article id="affiliate" class="info-card affiliate-card">
          <div class="card-icon">
            <Sparkles :size="22" />
          </div>
          <h2>Earn commission</h2>
          <p>
            Join the Viltrox Affiliate Program and earn commission while sharing products with your audience.
          </p>
          <a class="side-link" href="https://viltrox.com/pages/join-affiliate-tutorial" target="_blank" rel="noreferrer">
            Join affiliate program
            <ExternalLink :size="17" />
          </a>
        </article>
      </aside>
    </section>
  </main>
</template>
