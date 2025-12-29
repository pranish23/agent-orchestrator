<template>
  <div class="execution-trace">
    <div class="trace-header">
      <h4>Execution Steps</h4>
      <span class="execution-type">{{ executionType }}</span>
    </div>
    
    <div class="steps">
      <div 
        v-for="(group, groupIndex) in executionGroups" 
        :key="groupIndex"
        class="step-group"
        :class="{ 'is-parallel': group.items.length > 1 }"
      >
        <!-- Connector Line -->
        <div class="group-connector" v-if="groupIndex < executionGroups.length - 1"></div>

        <!-- Single Step -->
        <div v-if="group.items.length === 1" class="step single">
          <div class="step-number">{{ group.startIndex + 1 }}</div>
          <div class="step-content">
            <span class="step-name">{{ group.items[0].description }}</span>
            <span class="step-badge service">{{ group.items[0].service }}</span>
          </div>
        </div>

        <!-- Parallel Steps -->
        <div v-else class="parallel-container">
            <div class="parallel-label">Parallel Block</div>
            <div class="parallel-items">
                <div v-for="(item, itemIndex) in group.items" :key="itemIndex" class="step parallel-item">
                    <div class="step-number">{{ group.startIndex + itemIndex + 1 }}</div>
                    <div class="step-content">
                        <span class="step-name">{{ item.description }}</span>
                        <span class="step-badge service">{{ item.service }}</span>
                    </div>
                </div>
            </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  steps: {
    type: Array,
    default: () => []
  },
  plan: {
    type: Object,
    default: null
  }
})

// Normalize data into groups of steps
const executionGroups = computed(() => {
  // Scenario 1: We have the full Execution Plan (preferred)
  if (props.plan && props.plan.parallel_groups) {
    let currentIndex = 0
    return props.plan.parallel_groups.map(group => {
      const items = group.map(stepId => {
        const step = props.plan.steps.find(s => s.id === stepId)
        return {
          description: step ? step.description : stepId,
          service: step ? step.service || 'unknown' : 'system'
        }
      })
      
      const groupObj = {
        items,
        startIndex: currentIndex
      }
      currentIndex += items.length
      return groupObj
    })
  }

  // Scenario 2: Fallback to flat string array (legacy)
  // We'll treat everything as sequential unless we detect our heuristic (optional, but safer to just list sequential)
  return props.steps.map((step, index) => ({
    items: [{
      description: formatStepName(step),
      service: inferService(step)
    }],
    startIndex: index
  }))
})

const executionType = computed(() => {
  if (props.plan) {
    const hasParallel = props.plan.parallel_groups.some(g => g.length > 1)
    return hasParallel ? 'Optimized Parallel Execution' : 'Sequential Execution'
  }
  return 'Sequential'
})

function formatStepName(step) {
  return step
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}

function inferService(stepName) {
    const lower = stepName.toLowerCase()
    if (lower.includes('gmail') || lower.includes('email')) return 'gmail'
    if (lower.includes('calendar') || lower.includes('event')) return 'gcal'
    if (lower.includes('drive') || lower.includes('file')) return 'gdrive'
    return 'system'
}
</script>

<style scoped>
.execution-trace {
  background: rgba(139, 92, 246, 0.05);
  border: 1px solid rgba(139, 92, 246, 0.15);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.trace-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.trace-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.execution-type {
  background: rgba(139, 92, 246, 0.2);
  color: #c4b5fd;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
}

.steps {
  display: flex;
  flex-direction: column;
  gap: 16px; /* Space between groups */
  position: relative;
}

.step-group {
    position: relative;
}

/* Connectors */
.group-connector {
    position: absolute;
    left: 14px;
    top: 30px;
    bottom: -22px; /* Extend to next group */
    width: 2px;
    background: rgba(139, 92, 246, 0.2);
    z-index: 0;
}
.step-group:last-child .group-connector {
    display: none;
}

/* Single Step Styles */
.step {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
  z-index: 1;
}

.step-number {
  width: 28px;
  height: 28px;
  background: rgba(139, 92, 246, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #c4b5fd;
  flex-shrink: 0;
  border: 2px solid #1e1e2e; /* Cutout effect for connector */
}

.step-content {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  background: rgba(255, 255, 255, 0.03);
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.step-name {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  flex: 1;
}

.step-badge {
    font-size: 10px;
    text-transform: uppercase;
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 600;
    opacity: 0.8;
}

.step-badge.service { background: rgba(255, 255, 255, 0.1); color: #ccc; }

/* Parallel Styles */
.parallel-container {
    border: 1px dashed rgba(34, 197, 94, 0.3);
    background: rgba(34, 197, 94, 0.05);
    border-radius: 12px;
    padding: 12px;
    margin-left: 0;
}

.parallel-label {
    font-size: 10px;
    text-transform: uppercase;
    color: #4ade80;
    margin-bottom: 8px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

.parallel-items {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.parallel-item .step-number {
    background: rgba(34, 197, 94, 0.2);
    color: #86efac;
    width: 24px;
    height: 24px;
    font-size: 11px;
}
</style>
