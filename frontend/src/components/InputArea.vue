<script setup>
import { ref } from 'vue';
import { 
  Paperclip, Send, Camera, FileUp, Sparkles, X, 
  FileText, ShieldCheck, Scale, AlertTriangle, HelpCircle, Layers
} from 'lucide-vue-next';

const props = defineProps({
  loading: { type: Boolean, default: false },
  selectedDocuments: { type: Array, default: () => [] }
});

const emit = defineEmits([
  'submit', 
  'upload-file', 
  'open-camera', 
  'remove-document'
]);

const prompt = ref('');
const fileInputRef = ref(null);
const showAttachMenu = ref(false);

function triggerFileInput() {
  showAttachMenu.value = false;
  if (fileInputRef.value) fileInputRef.value.click();
}

function onFileSelected(e) {
  const file = e.target.files?.[0];
  if (file) {
    emit('upload-file', file);
    e.target.value = '';
  }
}

function handleCameraClick() {
  showAttachMenu.value = false;
  emit('open-camera');
}

function handleSend() {
  if ((!prompt.value.trim() && props.selectedDocuments.length === 0) || props.loading) return;
  emit('submit', prompt.value);
  prompt.value = '';
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
}

function setPresetPrompt(text) {
  prompt.value = text;
}
</script>

<template>
  <div class="input-container">
    <!-- Quick Starter Prompt Chips (matches suggested actions in UI sketch) -->
    <div class="quick-chips">
      <button class="chip" @click="setPresetPrompt('Identify high-risk and unusual clauses in this agreement that require review.')">
        <AlertTriangle :size="13" class="chip-icon danger" />
        <span>Detect Risk Clauses</span>
      </button>

      <button class="chip" @click="setPresetPrompt('List all critical deadlines, milestones, and notice timeframes.')">
        <Scale :size="13" class="chip-icon gold" />
        <span>Extract Timeline & Deadlines</span>
      </button>

      <button class="chip" @click="setPresetPrompt('Explain this contract in simple, plain language with practical examples.')">
        <Sparkles :size="13" class="chip-icon cyan" />
        <span>Plain Language Summary</span>
      </button>

      <button class="chip" @click="setPresetPrompt('Generate strategic questions I should ask my lawyer regarding this contract.')">
        <HelpCircle :size="13" class="chip-icon purple" />
        <span>Ask a Lawyer Questions</span>
      </button>
    </div>

    <!-- Active Attached Document Chips Preview -->
    <div v-if="selectedDocuments.length > 0" class="attached-docs-bar">
      <span class="attach-label">Active Context:</span>
      <div v-for="doc in selectedDocuments" :key="doc.id" class="doc-badge">
        <FileText :size="14" class="doc-icon" />
        <span class="doc-name">{{ doc.original_filename }}</span>
        <button class="btn-remove-doc" @click="emit('remove-document', doc.id)">
          <X :size="12" />
        </button>
      </div>
    </div>

    <!-- The Centered Input Box (Matches "input area" with (+) and (Play/Send) in sketch) -->
    <div class="input-card" :class="{ 'focused': prompt.length > 0 }">
      <!-- Left (+) Attachment Button (matches (+) in sketch with "attachment file and snap with camera") -->
      <div class="attach-wrapper">
        <button 
          class="btn-attach" 
          @click="showAttachMenu = !showAttachMenu"
          title="Attach document or snap with camera"
          type="button"
        >
          <span class="plus-icon">+</span>
        </button>

        <!-- Dropdown Popover for "file" and "snap with camera" -->
        <div v-if="showAttachMenu" class="attach-menu fade-in">
          <button class="menu-item" @click="triggerFileInput">
            <FileUp :size="16" class="menu-icon cyan" />
            <div class="menu-text">
              <span class="menu-title">Upload File</span>
              <span class="menu-desc">PDF, DOCX, TXT, Images</span>
            </div>
          </button>

          <button class="menu-item" @click="handleCameraClick">
            <Camera :size="16" class="menu-icon gold" />
            <div class="menu-text">
              <span class="menu-title">Snap with Camera</span>
              <span class="menu-desc">Scan physical contract page</span>
            </div>
          </button>
        </div>
      </div>

      <!-- Hidden standard file picker -->
      <input 
        ref="fileInputRef" 
        type="file" 
        accept=".pdf,.docx,.txt,.png,.jpg,.jpeg" 
        class="hidden-file-input" 
        @change="onFileSelected" 
      />

      <!-- Textarea input field -->
      <textarea
        v-model="prompt"
        class="prompt-textarea"
        placeholder="Ask LegalLens anything about your contract or upload an agreement..."
        rows="1"
        @keydown="handleKeydown"
      ></textarea>

      <!-- Right Action / Send Button (matches sketched right circular button) -->
      <button 
        class="btn-send" 
        :disabled="loading || (!prompt.trim() && selectedDocuments.length === 0)"
        @click="handleSend"
        title="Send Query to Legal Multi-Agent System"
      >
        <div v-if="loading" class="spinner"></div>
        <Send v-else :size="18" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.input-container {
  width: 100%;
  max-width: 860px;
  margin: 0 auto;
  padding: 16px 24px 24px;
}

.quick-chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 12px;
  scrollbar-width: none;
}
.quick-chips::-webkit-scrollbar {
  display: none;
}

.chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 13px;
  border-radius: var(--radius-full);
  background: rgba(22, 28, 45, 0.65);
  border: 1px solid var(--glass-border);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}

.chip:hover {
  background: var(--bg-tertiary);
  border-color: rgba(255, 255, 255, 0.15);
  color: #fff;
  transform: translateY(-1px);
}

.chip-icon.danger { color: var(--accent-danger); }
.chip-icon.gold { color: var(--accent-gold); }
.chip-icon.cyan { color: var(--accent-cyan); }
.chip-icon.purple { color: var(--accent-purple); }

.attached-docs-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 8px;
  background: rgba(56, 189, 248, 0.08);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: var(--radius-md);
  font-size: 12px;
}

.attach-label {
  color: var(--accent-cyan);
  font-weight: 600;
}

.doc-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background: var(--bg-tertiary);
  color: #fff;
  border: 1px solid var(--glass-border);
}

.doc-icon {
  color: var(--accent-gold);
}

.doc-name {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-remove-doc {
  background: none;
  border: none;
  color: var(--text-sub);
  cursor: pointer;
  display: flex;
  align-items: center;
}
.btn-remove-doc:hover {
  color: var(--accent-danger);
}

/* The Main Input Card as drawn in user sketch */
.input-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-radius: 28px;
  background: var(--bg-secondary);
  border: 1.5px solid var(--glass-border);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
  transition: all 0.2s ease;
}

.input-card:focus-within,
.input-card.focused {
  border-color: var(--accent-gold);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5), 0 0 20px var(--accent-gold-glow);
}

.attach-wrapper {
  position: relative;
}

/* The (+) circular button from the sketch */
.btn-attach {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--bg-tertiary);
  border: 1px solid var(--glass-border);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-attach:hover {
  background: rgba(229, 180, 88, 0.15);
  border-color: var(--accent-gold);
  color: var(--accent-gold);
  transform: scale(1.05);
}

.plus-icon {
  font-size: 24px;
  font-weight: 300;
  line-height: 1;
  margin-top: -2px;
}

/* Attachment Menu */
.attach-menu {
  position: absolute;
  bottom: 52px;
  left: 0;
  width: 240px;
  background: var(--bg-tertiary);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  padding: 8px;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  gap: 4px;
  z-index: 50;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
  width: 100%;
}

.menu-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.menu-icon.cyan { color: var(--accent-cyan); }
.menu-icon.gold { color: var(--accent-gold); }

.menu-text {
  display: flex;
  flex-direction: column;
}

.menu-title {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.menu-desc {
  font-size: 11px;
  color: var(--text-sub);
}

.hidden-file-input {
  display: none;
}

.prompt-textarea {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #fff;
  font-size: 15px;
  font-family: inherit;
  resize: none;
  max-height: 120px;
  line-height: 1.5;
  padding: 8px 0;
}

.prompt-textarea::placeholder {
  color: var(--text-sub);
}

/* The right circular Send button from the sketch */
.btn-send {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent-gold) 0%, #ca8a04 100%);
  border: none;
  color: #0a0d14;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 10px rgba(229, 180, 88, 0.3);
  flex-shrink: 0;
}

.btn-send:hover:not(:disabled) {
  transform: scale(1.06);
  filter: brightness(1.1);
}

.btn-send:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  transform: none;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(10, 13, 20, 0.3);
  border-top-color: #0a0d14;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
