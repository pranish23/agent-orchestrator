<template>
  <div class="actions-list">
    <h4>Actions Taken</h4>
    
    <div class="actions" v-if="actions.length">
      <div 
        v-for="(action, index) in actions" 
        :key="index"
        class="action"
      >
        <div class="action-icon" :class="action.status">
          <svg v-if="action.status === 'success'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 6L9 17l-5-5"/>
          </svg>
          <svg v-else-if="action.status === 'failed'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M5 12h14"/>
          </svg>
        </div>
        
        <div class="action-content">
          <div class="action-header">
            <span class="service-badge" :class="action.service">{{ action.service }}</span>
            <span class="operation">{{ action.operation }}</span>
          </div>
          <p class="action-details" v-if="action.details">{{ action.details }}</p>
        </div>
        
        <span class="status-badge" :class="action.status">{{ action.status }}</span>
      </div>
    </div>
    
    <div class="no-actions" v-else>
      <p>No write operations were performed for this query.</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  actions: {
    type: Array,
    required: true
  }
})
</script>

<style scoped>
.actions-list {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 16px;
}

.actions-list h4 {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
}

.action-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.action-icon.success {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.action-icon.failed {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.action-icon.skipped {
  background: rgba(156, 163, 175, 0.2);
  color: #9ca3af;
}

.action-content {
  flex: 1;
}

.action-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.service-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.service-badge.gmail {
  background: rgba(234, 67, 53, 0.2);
  color: #ea4335;
}

.service-badge.gcal {
  background: rgba(66, 133, 244, 0.2);
  color: #4285f4;
}

.service-badge.drive {
  background: rgba(52, 168, 83, 0.2);
  color: #34a853;
}

.operation {
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.8);
}

.action-details {
  margin: 6px 0 0 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.status-badge {
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
  flex-shrink: 0;
}

.status-badge.success {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.status-badge.failed {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.status-badge.skipped {
  background: rgba(156, 163, 175, 0.2);
  color: #9ca3af;
}

.no-actions {
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.4);
  font-size: 13px;
  text-align: center;
}
</style>
