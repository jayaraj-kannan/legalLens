<script setup>
import { 
  Bot, User, Scale, ShieldAlert, Clock, 
  HelpCircle, Globe, CheckCircle2, ChevronRight, FileText
} from 'lucide-vue-next';

defineProps({
  messages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
});

function getAgentBadgeColor(agentName) {
  if (!agentName) return 'var(--accent-gold)';
  if (agentName.includes('risk')) return 'var(--accent-danger)';
  if (agentName.includes('timeline')) return 'var(--accent-cyan)';
  if (agentName.includes('qa')) return 'var(--accent-purple)';
  if (agentName.includes('multilingual')) return 'var(--accent-success)';
  return 'var(--accent-gold)';
}

function formatAgentLabel(agentName) {
  if (!agentName) return 'Orchestrator Agent';
  return agentName
    .replace('_agent', '')
    .split('_')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ') + ' Agent';
}
</script>

<template>
  <div class="message-feed">
    <div 
      v-for="(msg, idx) in messages" 
      :key="idx" 
      class="message-row"
      :class="[msg.role]"
    >
      <!-- Message Content Card (matches cards in the right pane of sketch) -->
      <div class="message-card fade-in" :class="[msg.role]">
        <!-- Agent Identity Header -->
        <div v-if="msg.role === 'assistant'" class="agent-header">
          <div class="agent-avatar" :style="{ borderColor: getAgentBadgeColor(msg.agentName) }">
            <Scale :size="16" :style="{ color: getAgentBadgeColor(msg.agentName) }" />
          </div>
          <div class="agent-meta">
            <span class="agent-tag" :style="{ color: getAgentBadgeColor(msg.agentName) }">
              {{ formatAgentLabel(msg.agentName) }}
            </span>
            <span class="verified-pill">
              <CheckCircle2 :size="12" />
              <span>Grounded Evidence</span>
            </span>
          </div>
        </div>

        <div v-else class="user-header">
          <div class="user-avatar-small">
            <User :size="14" />
          </div>
          <span class="user-label">You</span>
        </div>

        <!-- Rendered Text Message Content -->
        <div class="message-body">
          <div class="formatted-text" v-html="msg.text.replace(/\n/g, '<br/>')"></div>
        </div>

        <!-- Referenced Documents Chips (if present) -->
        <div v-if="msg.documents && msg.documents.length > 0" class="msg-docs">
          <div v-for="d in msg.documents" :key="d" class="msg-doc-pill">
            <FileText :size="12" />
            <span>{{ d }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Active Agent Thinking State -->
    <div v-if="loading" class="message-row assistant">
      <div class="message-card assistant thinking-card fade-in">
        <div class="agent-header">
          <div class="agent-avatar pulse">
            <Scale :size="16" style="color: var(--accent-gold);" />
          </div>
          <div class="agent-meta">
            <span class="agent-tag" style="color: var(--accent-gold);">Response Orchestrator Agent</span>
            <span class="routing-text">Routing intent to specialist sub-agents...</span>
          </div>
        </div>
        <div class="thinking-bars">
          <div class="bar"></div>
          <div class="bar short"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.message-feed {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 24px 24px 10px;
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
}

.message-row {
  display: flex;
  width: 100%;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

/* The card outline matching boxes in the right column of user's sketch */
.message-card {
  max-width: 85%;
  padding: 20px 24px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--glass-border);
  box-shadow: var(--shadow-md);
  position: relative;
  line-height: 1.6;
}

.message-card.user {
  background: var(--bg-tertiary);
  border-color: rgba(56, 189, 248, 0.25);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-card.assistant {
  background: var(--bg-secondary);
  border-color: rgba(255, 255, 255, 0.08);
  border-bottom-left-radius: 4px;
}

.agent-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-subtle);
}

.agent-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.04);
  border: 1.5px solid var(--accent-gold);
  display: flex;
  align-items: center;
  justify-content: center;
}

.agent-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.agent-tag {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: -0.2px;
}

.verified-pill {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--accent-success);
  background: rgba(16, 185, 129, 0.1);
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

.user-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.user-avatar-small {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(56, 189, 248, 0.2);
  color: var(--accent-cyan);
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

.message-body {
  font-size: 14.5px;
  color: var(--text-main);
  word-break: break-word;
}

.formatted-text :deep(strong),
.formatted-text :deep(b) {
  color: #fff;
  font-weight: 700;
}

.msg-docs {
  display: flex;
  gap: 8px;
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid var(--border-subtle);
}

.msg-doc-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.04);
  font-size: 12px;
  color: var(--accent-gold);
}

/* Thinking animation */
.thinking-card {
  width: 100%;
  max-width: 480px;
}

.routing-text {
  font-size: 12px;
  color: var(--text-sub);
  font-style: italic;
}

.thinking-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

.bar {
  height: 8px;
  border-radius: 4px;
  background: linear-gradient(90deg, rgba(229, 180, 88, 0.2), rgba(229, 180, 88, 0.5), rgba(229, 180, 88, 0.2));
  background-size: 200% 100%;
  animation: loadingShimmer 1.5s infinite;
}

.bar.short {
  width: 60%;
}

@keyframes loadingShimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.pulse {
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.08); }
}
</style>
