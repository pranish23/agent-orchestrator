<template>
  <div class="app">
    <header class="app-header">
      <div class="logo">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="url(#gradient)" stroke-width="2"/>
          <path d="M12 6v6l4 2" stroke="url(#gradient)" stroke-width="2" stroke-linecap="round"/>
          <defs>
            <linearGradient id="gradient" x1="0" y1="0" x2="24" y2="24">
              <stop stop-color="#6366f1"/>
              <stop offset="1" stop-color="#8b5cf6"/>
            </linearGradient>
          </defs>
        </svg>
        <span>Agent Orchestrator</span>
      </div>
      <div class="status">
        <span class="status-dot" :class="{ connected: isConnected }"></span>
        <span>{{ isConnected ? 'Connected' : 'Connecting...' }}</span>
      </div>
    </header>
    
    <main class="app-main">
      <div class="query-section">
        <h1>Test Your Queries</h1>
        <p class="subtitle">Ask questions about your Gmail, Calendar, and Drive</p>
        
        <QueryInput ref="queryInput" @submit="handleQuery" />
        
        <div class="error-message" v-if="error">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 8v4M12 16h.01"/>
          </svg>
          {{ error }}
        </div>
        
        <ResponsePanel :response="response" />
      </div>
      
      <div class="data-section">
        <h2>Database Content</h2>
        <p class="section-subtitle">Data used for embedding and semantic search</p>
        
        <TabPanel :tabs="dataTabs" default-tab="gmail">
          <template #gmail>
            <DataTable 
              :columns="gmailColumns" 
              :items="gmailData" 
              :loading="loadingGmail"
              @refresh="loadGmailData"
            />
          </template>
          
          <template #gcal>
            <DataTable 
              :columns="gcalColumns" 
              :items="gcalData"
              :loading="loadingGcal"
              @refresh="loadGcalData"
            />
          </template>
          
          <template #gdrive>
            <DataTable 
              :columns="gdriveColumns" 
              :items="gdriveData"
              :loading="loadingGdrive"
              @refresh="loadGdriveData"
            />
          </template>
        </TabPanel>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useApi } from './composables/useApi'
import QueryInput from './components/QueryInput.vue'
import ResponsePanel from './components/ResponsePanel.vue'
import TabPanel from './components/TabPanel.vue'
import DataTable from './components/DataTable.vue'

const api = useApi()

// State
const isConnected = ref(false)
const response = ref(null)
const error = ref(null)
const queryInput = ref(null)

// Data state
const gmailData = ref([])
const gcalData = ref([])
const gdriveData = ref([])
const loadingGmail = ref(false)
const loadingGcal = ref(false)
const loadingGdrive = ref(false)

// Tab configuration
const dataTabs = computed(() => [
  { key: 'gmail', label: 'Gmail', count: gmailData.value.length },
  { key: 'gcal', label: 'Calendar', count: gcalData.value.length },
  { key: 'gdrive', label: 'Drive', count: gdriveData.value.length },
])

// Column definitions
const gmailColumns = [
  { key: 'subject', label: 'Subject', maxLength: 50 },
  { key: 'sender', label: 'From', maxLength: 30 },
  { key: 'body_preview', label: 'Preview', maxLength: 60 },
  { key: 'received_at', label: 'Date', type: 'date' },
]

const gcalColumns = [
  { key: 'title', label: 'Title', maxLength: 40 },
  { key: 'description', label: 'Description', maxLength: 50 },
  { key: 'location', label: 'Location', maxLength: 30 },
  { key: 'start_time', label: 'Start', type: 'date' },
  { key: 'attendees', label: 'Attendees', type: 'array' },
]

const gdriveColumns = [
  { key: 'name', label: 'Name', maxLength: 40 },
  { key: 'mime_type', label: 'Type', maxLength: 30 },
  { key: 'content_preview', label: 'Preview', maxLength: 60 },
  { key: 'modified_at', label: 'Modified', type: 'date' },
]

// Methods
async function handleQuery(query) {
  error.value = null
  
  if (queryInput.value) {
    queryInput.value.loading = true
  }
  
  try {
    response.value = await api.submitQuery(query)
    
    // Refresh data tables in case query caused changes
    await Promise.all([
      loadGmailData(),
      loadGcalData(),
      loadGdriveData(),
    ])
  } catch (e) {
    error.value = e.message || 'Failed to process query'
  } finally {
    if (queryInput.value) {
      queryInput.value.loading = false
    }
  }
}

async function loadGmailData() {
  loadingGmail.value = true
  try {
    const result = await api.getGmailData()
    gmailData.value = result.items
  } catch (e) {
    console.error('Failed to load Gmail data:', e)
  } finally {
    loadingGmail.value = false
  }
}

async function loadGcalData() {
  loadingGcal.value = true
  try {
    const result = await api.getGcalData()
    gcalData.value = result.items
  } catch (e) {
    console.error('Failed to load Calendar data:', e)
  } finally {
    loadingGcal.value = false
  }
}

async function loadGdriveData() {
  loadingGdrive.value = true
  try {
    const result = await api.getGdriveData()
    gdriveData.value = result.items
  } catch (e) {
    console.error('Failed to load Drive data:', e)
  } finally {
    loadingGdrive.value = false
  }
}

async function checkConnection() {
  try {
    await api.healthCheck()
    isConnected.value = true
  } catch {
    isConnected.value = false
  }
}

// Lifecycle
onMounted(async () => {
  await checkConnection()
  
  // Update connection status every 30 seconds
  setInterval(checkConnection, 30000)
  
  // Load initial data
  await Promise.all([
    loadGmailData(),
    loadGcalData(),
    loadGdriveData(),
  ])
})
</script>

<style scoped>
.app {
  min-height: 100vh;
  background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 50%, #0f0f23 100%);
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(15, 15, 35, 0.8);
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 18px;
  font-weight: 600;
  color: white;
}

.status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
}

.status-dot.connected {
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.5);
}

.app-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 32px;
}

.query-section {
  margin-bottom: 48px;
}

.query-section h1 {
  margin: 0 0 8px 0;
  font-size: 32px;
  font-weight: 700;
  background: linear-gradient(135deg, #fff 0%, #a5b4fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  margin: 0 0 24px 0;
  color: rgba(255, 255, 255, 0.5);
  font-size: 16px;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 16px 0;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  color: #fca5a5;
  font-size: 14px;
}

.data-section h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
  color: white;
}

.section-subtitle {
  margin: 0 0 20px 0;
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
}
</style>
