<template>
  <div class="response-panel" v-if="response">
    <div class="response-header">
      <h3>Response</h3>
      <span class="execution-time">{{ response.execution_time_ms }}ms</span>
    </div>
    
    <div class="response-content">
      <p class="response-text">{{ response.response }}</p>
    </div>
    
    <!-- Intent Card -->
    <IntentCard v-if="response.intent" :intent="response.intent" />
    
    <!-- Execution Trace -->
    <ExecutionTrace v-if="response.intent?.steps" :steps="response.intent.steps" />
    
    <!-- Actions Taken -->
    <ActionsList :actions="response.actions_taken || []" />
  </div>
  
  <div class="response-panel empty" v-else>
    <div class="empty-state">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
      <p>Enter a query above to see the response</p>
    </div>
  </div>
</template>

<script setup>
import IntentCard from './IntentCard.vue'
import ExecutionTrace from './ExecutionTrace.vue'
import ActionsList from './ActionsList.vue'

defineProps({
  response: {
    type: Object,
    default: null
  }
})
</script>

<style scoped>
.response-panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 24px;
  backdrop-filter: blur(10px);
}

.response-panel.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.empty-state {
  text-align: center;
  color: rgba(255, 255, 255, 0.3);
}

.empty-state svg {
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-state p {
  font-size: 14px;
}

.response-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.response-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.execution-time {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.response-content {
  margin-bottom: 20px;
}

.response-text {
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.6;
  font-size: 15px;
  margin: 0;
  white-space: pre-wrap;
}
</style>
