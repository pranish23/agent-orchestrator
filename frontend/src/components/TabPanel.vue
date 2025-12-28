<template>
  <div class="tab-panel">
    <div class="tabs">
      <button 
        v-for="tab in tabs" 
        :key="tab.key"
        @click="activeTab = tab.key"
        class="tab"
        :class="{ active: activeTab === tab.key }"
      >
        <component :is="tab.icon" v-if="tab.icon" />
        <span>{{ tab.label }}</span>
        <span class="count" v-if="tab.count !== undefined">{{ tab.count }}</span>
      </button>
    </div>
    
    <div class="tab-content">
      <slot :name="activeTab" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  tabs: {
    type: Array,
    required: true
    // [{ key: 'gmail', label: 'Gmail', count: 10 }]
  },
  defaultTab: String
})

const activeTab = ref(props.defaultTab || props.tabs[0]?.key)

watch(() => props.defaultTab, (newVal) => {
  if (newVal) activeTab.value = newVal
})
</script>

<style scoped>
.tab-panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  overflow: hidden;
}

.tabs {
  display: flex;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0 8px;
  background: rgba(255, 255, 255, 0.02);
}

.tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.tab:hover {
  color: rgba(255, 255, 255, 0.8);
}

.tab.active {
  color: #a5b4fc;
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 12px;
  right: 12px;
  height: 2px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 2px 2px 0 0;
}

.count {
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
}

.tab.active .count {
  background: rgba(99, 102, 241, 0.3);
}

.tab-content {
  padding: 0;
}
</style>
