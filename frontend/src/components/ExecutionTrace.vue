<template>
  <div class="execution-trace">
    <div class="trace-header">
      <h4>Execution Steps</h4>
      <span class="execution-type">{{ executionType }}</span>
    </div>
    
    <div class="steps">
      <div 
        v-for="(step, index) in steps" 
        :key="index"
        class="step"
        :class="{ 'parallel': isParallel(index) }"
      >
        <div class="step-number">{{ index + 1 }}</div>
        <div class="step-content">
          <span class="step-name">{{ formatStepName(step) }}</span>
          <span class="step-type" v-if="isParallel(index)">parallel</span>
        </div>
        <div class="step-connector" v-if="index < steps.length - 1">
          <svg v-if="isParallel(index) && isParallel(index + 1)" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 9l6 6 6-6"/>
          </svg>
          <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5v14M12 19l-7-7M12 19l7-7"/>
          </svg>
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
    required: true
  }
})

// Determine if steps can run in parallel based on their names
const parallelSteps = computed(() => {
  const searchSteps = props.steps.filter(s => 
    s.includes('search') || s.includes('find') || s.includes('get')
  )
  return searchSteps.length > 1 ? searchSteps : []
})

const executionType = computed(() => {
  if (parallelSteps.value.length > 1) {
    return 'Mixed (Parallel + Sequential)'
  }
  return 'Sequential'
})

function isParallel(index) {
  return parallelSteps.value.includes(props.steps[index])
}

function formatStepName(step) {
  return step
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}
</script>

<style scoped>
.execution-trace {
  background: rgba(139, 92, 246, 0.1);
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.trace-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.trace-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.execution-type {
  background: rgba(139, 92, 246, 0.3);
  color: #c4b5fd;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
}

.steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.step {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
}

.step-number {
  width: 28px;
  height: 28px;
  background: rgba(139, 92, 246, 0.3);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #c4b5fd;
  flex-shrink: 0;
}

.step.parallel .step-number {
  background: rgba(34, 197, 94, 0.3);
  color: #86efac;
}

.step-content {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.step-name {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
}

.step-type {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 500;
}

.step-connector {
  position: absolute;
  left: 14px;
  top: 28px;
  color: rgba(139, 92, 246, 0.4);
}
</style>
