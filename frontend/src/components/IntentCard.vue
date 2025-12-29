<template>
  <div class="intent-card">
    <div class="card-header">
      <h4>Intent Classification</h4>
      <div class="confidence" :class="confidenceClass">
        {{ Math.round(intent.confidence * 100) }}% confidence
      </div>
    </div>
    
    <div class="intent-grid">
      <div class="intent-item">
        <label>Intent</label>
        <span class="intent-type">{{ intent.intent }}</span>
      </div>
      
      <div class="intent-item">
        <label>Services</label>
        <div class="services">
          <span 
            v-for="service in intent.services" 
            :key="service"
            class="service-badge"
            :class="service"
          >
            {{ service }}
          </span>
        </div>
      </div>
      
      <div class="intent-item" v-if="filteredEntities.length">
        <label>Entities</label>
        <div class="entities">
          <div v-for="entity in filteredEntities" :key="entity.key" class="entity">
            <span class="entity-key">{{ entity.key }}:</span>
            <span class="entity-value">{{ formatEntity(entity.value) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  intent: {
    type: Object,
    required: true
  }
})

const confidenceClass = computed(() => {
  if (props.intent.confidence >= 0.8) return 'high'
  if (props.intent.confidence >= 0.5) return 'medium'
  return 'low'
})

const filteredEntities = computed(() => {
  if (!props.intent.entities) return []
  return Object.entries(props.intent.entities)
    .filter(([_, value]) => {
      if (value === null || value === undefined) return false
      if (typeof value === 'string' && value.trim() === '') return false
      if (Array.isArray(value) && value.length === 0) return false
      return true
    })
    .map(([key, value]) => ({ key, value }))
})

function formatEntity(value) {
  if (Array.isArray(value)) return value.join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  return value
}
</script>

<style scoped>
.intent-card {
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.confidence {
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.confidence.high {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.confidence.medium {
  background: rgba(234, 179, 8, 0.2);
  color: #eab308;
}

.confidence.low {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.intent-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.intent-item label {
  display: block;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 4px;
}

.intent-type {
  font-size: 14px;
  font-weight: 500;
  color: #a5b4fc;
}

.services {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.service-badge {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.service-badge.gmail {
  background: rgba(66, 133, 244, 0.2);
  color: #4285f4;
}

.service-badge.gcal {
  background: rgba(66, 133, 244, 0.2);
  color: #4285f4;
}

.service-badge.gdrive {
  background: rgba(66, 133, 244, 0.2);
  color: #4285f4;
}

.entities {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.entity {
  font-size: 13px;
}

.entity-key {
  color: rgba(255, 255, 255, 0.5);
  margin-right: 4px;
}

.entity-value {
  color: rgba(255, 255, 255, 0.8);
}
</style>
