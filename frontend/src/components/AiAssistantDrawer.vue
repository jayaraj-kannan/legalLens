<script setup>
import { ref, nextTick, watch } from 'vue';
import { 
  Sparkles, Send, X, Bot, User, FileText, ChevronRight, 
  RotateCcw, Globe, ShieldAlert, FileSearch, ArrowRight, CornerDownLeft
} from 'lucide-vue-next';

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: true
  },
  messages: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  attachedDocuments: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['close', 'send-query']);

const inputPrompt = ref('');

const suggestedPrompts = [
  { icon: ShieldAlert, label: 'Clarify High Risks', prompt: 'Highlight the top 3 most dangerous or one-sided clauses in this contract and propose redline counter-proposals.' },
  { icon: FileSearch, label: 'Plain Explanation', prompt: 'Explain the core obligations and consequences in simple, everyday English without legal jargon.' },
  { icon: Globe, label: 'Translate to Indian Language', prompt: 'Translate and explain the key findings and obligations in Tamil and Hindi.' },
  { icon: Sparkles, label: 'Draft Negotiation Email', prompt: 'Draft a professional, courteous email to the counter-party requesting amendments to the indemnification and termination clauses.' }
];

function submitMessage() {
  if (!inputPrompt.value.trim() || props.loading) return;
  const text = inputPrompt.value.trim();
  inputPrompt.value = '';
  emit('send-query', text);
}

function handleKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submitMessage();
  }
}

function sendSuggestion(promptText) {
  emit('send-query', promptText);
}

// Auto scroll on new messages
watch(() => props.messages.length, async () => {
  await nextTick();
  const el = document.getElementById('drawer-scroll-feed');
  if (el) el.scrollTop = el.scrollHeight;
});
</script>

<template>
  <aside class="ai-drawer" :class="{ 'drawer-open': isOpen, 'drawer-closed': !isOpen }">
    <!-- Drawer Header -->
    <header class="drawer-header">
      <div class="header-branding">
        <div class="bot-halo">
          <Sparkles :size="16" />
        </div>
        <div class="branding-text">
          <h3>AI Legal Copilot</h3>
          <span class="sub-status">Multi-Agent Orchestrator</span>
        </div>
      </div>

      <div class="header-actions">
        <button class="btn-close-drawer" @click="emit('close')" title="Collapse AI Copilot">
          <X :size="18" />
        </button>
      </div>
    </header>

    <!-- Drawer Body / Messages Scroll Area -->
    <section id="drawer-scroll-feed" class="drawer-feed">
      <!-- Quick Prompt Suggestions Bar -->
      <div v-if="messages.length <= 2" class="suggestions-dock">
        <span class="suggestions-title">Quick Inquiries:</span>
        <div class="suggestions-list">
          <button 
            v-for="(s, idx) in suggestedPrompts" 
            :key="idx" 
            class="suggestion-chip"
            @click="sendSuggestion(s.prompt)"
          >
            <component :is="s.icon" :size="13" />
            <span>{{ s.label }}</span>
          </button>
        </div>
      </div>

      <!-- Messages Loop -->
      <div class="messages-stack">
        <div 
          v-for="(msg, idx) in messages" 
          :key="idx" 
          class="chat-bubble-card"
          :class="[msg.role]"
        >
          <div class="bubble-header">
            <div class="role-identity">
              <span v-if="msg.role === 'assistant'" class="agent-tag">
                <Bot :size="12" />
                {{ msg.agentName || 'orchestrator_agent' }}
              </span>
              <span v-else class="user-tag">
                <User :size="12" />
                You
              </span>
            </div>
            <span v-if="msg.documents?.length" class="doc-context-ref">
              <FileText :size="11" />
              {{ msg.documents[0] }}
            </span>
          </div>

          <div class="bubble-body">
            <p>{{ msg.text }}</p>
          </div>
        </div>

        <!-- Typing / Agent Execution Indicator -->
        <div v-if="loading" class="chat-bubble-card assistant typing-indicator">
          <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <span class="typing-text">ADK specialist agents analyzing...</span>
        </div>
      </div>
    </section>

    <!-- Drawer Footer Input -->
    <footer class="drawer-footer">
      <div class="drawer-input-wrapper">
        <textarea
          v-model="inputPrompt"
          class="drawer-textarea"
          placeholder="Ask AI Copilot about this contract..."
          rows="2"
          @keydown="handleKeyDown"
        ></textarea>
        <button 
          class="btn-drawer-send" 
          :disabled="!inputPrompt.trim() || loading"
          @click="submitMessage"
        >
          <Send :size="15" />
        </button>
      </div>
      <div class="footer-hint">
        <span>Press <strong>Enter</strong> to send • <strong>Shift+Enter</strong> for newline</span>
      </div>
    </footer>
  </aside>
</template>

<style scoped>
.ai-drawer {
  width: 400px;
  height: 100%;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.16, 1, 0.3, 1), transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
  z-index: 40;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.4);
}

.ai-drawer.drawer-closed {
  width: 0;
  border-left: none;
  visibility: hidden;
  pointer-events: none;
}

/* Header */
.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--border-subtle);
}

.header-branding {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bot-halo {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: rgba(229, 180, 88, 0.15);
  border: 1px solid rgba(229, 180, 88, 0.3);
  color: var(--accent-gold);
  display: flex;
  align-items: center;
  justify-content: center;
}

.branding-text h3 {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.2;
}

.sub-status {
  font-size: 0.72rem;
  color: var(--accent-gold);
}

.btn-close-drawer {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 6px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-close-drawer:hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-main);
}

/* Feed */
.drawer-feed {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.suggestions-dock {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}

.suggestions-title {
  font-size: 0.72rem;
  color: var(--text-sub);
  text-transform: uppercase;
  font-weight: 600;
}

.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.suggestion-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 0.8rem;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.suggestion-chip:hover {
  background: rgba(229, 180, 88, 0.12);
  border-color: rgba(229, 180, 88, 0.3);
  color: var(--accent-gold);
}

/* Messages */
.messages-stack {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.chat-bubble-card {
  padding: 12px 14px;
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 0.88rem;
  line-height: 1.5;
}

.chat-bubble-card.user {
  background: rgba(56, 189, 248, 0.08);
  border: 1px solid rgba(56, 189, 248, 0.2);
  align-self: flex-end;
  max-width: 90%;
}

.chat-bubble-card.assistant {
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  align-self: flex-start;
  max-width: 98%;
}

.bubble-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.agent-tag {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--accent-gold);
}

.user-tag {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--accent-cyan);
}

.doc-context-ref {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.72rem;
  color: var(--text-sub);
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bubble-body p {
  color: var(--text-main);
  white-space: pre-wrap;
}

/* Typing animation */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 5px;
  height: 5px;
  background: var(--accent-gold);
  border-radius: 50%;
  animation: bounce 1.2s infinite ease-in-out both;
}

.typing-dots span:nth-child(1) { animation-delay: -0.32s; }
.typing-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.typing-text {
  font-size: 0.78rem;
  color: var(--text-muted);
}

/* Footer Input */
.drawer-footer {
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-top: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.drawer-input-wrapper {
  position: relative;
  display: flex;
  align-items: flex-end;
}

.drawer-textarea {
  width: 100%;
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-main);
  font-family: inherit;
  font-size: 0.85rem;
  padding: 8px 36px 8px 10px;
  resize: none;
  outline: none;
  transition: border-color 0.2s;
}

.drawer-textarea:focus {
  border-color: var(--accent-gold);
}

.btn-drawer-send {
  position: absolute;
  right: 6px;
  bottom: 8px;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  background: var(--accent-gold);
  color: #0b0f19;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-drawer-send:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-drawer-send:not(:disabled):hover {
  transform: scale(1.05);
}

.footer-hint {
  font-size: 0.7rem;
  color: var(--text-sub);
  text-align: center;
}
</style>
