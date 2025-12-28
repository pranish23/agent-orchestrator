<template>
  <div class="query-input">
    <div class="input-container">
      <textarea
        v-model="query"
        placeholder="Ask anything about your Gmail, Calendar, or Drive..."
        @keydown.enter.ctrl="handleSubmit"
        :disabled="loading"
        rows="3"
      ></textarea>
      <button 
        @click="handleSubmit" 
        :disabled="loading || !query.trim()"
        class="submit-btn"
      >
        <span v-if="loading" class="spinner"></span>
        <span v-else>Send</span>
      </button>
    </div>
    
    <div class="quick-actions">
      <span class="label">Try:</span>
      <button 
        v-for="example in examples" 
        :key="example"
        @click="setQuery(example)"
        class="example-btn"
      >
        {{ example }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['submit'])

const query = ref('')
const loading = ref(false)

const examples = [
  "What's on my calendar next week?",
  "Find emails from sarah@company.com",
  "Show me PDFs in Drive",
  "Cancel my Turkish Airlines flight",
]

function setQuery(text) {
  query.value = text
}

function handleSubmit() {
  if (query.value.trim() && !loading.value) {
    emit('submit', query.value)
  }
}

defineExpose({ loading, query })
</script>

<style scoped>
.query-input {
  width: 100%;
}

.input-container {
  display: flex;
  gap: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 16px;
  backdrop-filter: blur(10px);
}

textarea {
  flex: 1;
  background: transparent;
  border: none;
  color: #fff;
  font-size: 16px;
  resize: none;
  outline: none;
  font-family: inherit;
}

textarea::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.submit-btn {
  align-self: flex-end;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 80px;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.3);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  align-items: center;
}

.label {
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
}

.example-btn {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.7);
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.example-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}
</style>
