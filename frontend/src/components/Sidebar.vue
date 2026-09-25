<script setup>
import { 
  Plus, MessageSquare, Scale, Clock, ShieldAlert, 
  FileText, LogOut, ChevronRight, User, Trash2
} from 'lucide-vue-next';

defineProps({
  sessions: { type: Array, default: () => [] },
  activeSessionId: { type: String, default: '' },
  currentUser: { type: Object, required: true },
  collapsed: { type: Boolean, default: false }
});

const emit = defineEmits(['select-session', 'new-chat', 'logout', 'delete-session']);
</script>

<template>
  <aside class="sidebar" :class="{ 'collapsed': collapsed }">
    <!-- Header with Branding -->
    <div class="sidebar-header">
      <div class="brand">
        <div class="logo-mark">
          <Scale :size="20" class="logo-icon" />
        </div>
        <div class="brand-text">
          <span class="brand-name">LegalLens</span>
          <span class="brand-tag">Agentic AI</span>
        </div>
      </div>
    </div>

    <!-- New Consultation Button (Matches "New" in sketch) -->
    <div class="new-action-wrap">
      <button class="btn-new-chat" @click="emit('new-chat')">
        <Plus :size="18" />
        <span>New Consultation</span>
      </button>
    </div>

    <!-- Chat History List (Matches "Chat History" with vertical list in sketch) -->
    <div class="history-section">
      <div class="section-title">
        <span>Chat History</span>
        <Clock :size="14" />
      </div>

      <div class="history-list">
        <div 
          v-for="sess in sessions" 
          :key="sess.id"
          class="history-item"
          :class="{ active: sess.id === activeSessionId }"
          @click="emit('select-session', sess.id)"
        >
          <MessageSquare :size="16" class="item-icon" />
          <div class="item-info">
            <span class="item-title">{{ sess.title || 'Legal Consultation' }}</span>
            <span class="item-date">{{ sess.created_at ? new Date(sess.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' }) : 'Today' }}</span>
          </div>
          <div class="item-actions">
            <button 
              type="button"
              class="btn-delete-session" 
              title="Delete consultation"
              @click.stop="emit('delete-session', sess.id)"
            >
              <Trash2 :size="13" />
            </button>
            <ChevronRight :size="14" class="item-arrow" />
          </div>
        </div>

        <div v-if="sessions.length === 0" class="empty-history">
          <FileText :size="24" class="empty-icon" />
          <p>No consultations yet.<br/>Start by uploading a contract or asking a legal question.</p>
        </div>
      </div>
    </div>

    <!-- Specialist Agents Directory Quick-view -->
    <div class="agents-preview">
      <span class="section-title">Active AI Specialists</span>
      <div class="agent-badges">
        <span class="agent-chip" title="Risk & Attention Specialist">Risk & Attention</span>
        <span class="agent-chip" title="Timeline & Obligations">Timeline</span>
        <span class="agent-chip" title="Plain-Language Simplifier">Plain Language</span>
        <span class="agent-chip" title="Contract Redline Comparison">Comparison</span>
        <span class="agent-chip" title="Lawyer Question Generator">Lawyer Prep</span>
        <span class="agent-chip" title="Indian Regional Translation">Multilingual</span>
      </div>
    </div>

    <!-- User Profile Footer (Matches "Logged in user info" with circle Avatar (J) in sketch) -->
    <div class="sidebar-footer">
      <div class="user-pill">
        <div class="user-avatar">{{ currentUser.avatar || 'J' }}</div>
        <div class="user-details">
          <span class="user-name">{{ currentUser.name }}</span>
          <span class="user-role">Legal Professional</span>
        </div>
        <button class="btn-logout" @click="emit('logout')" title="Log out">
          <LogOut :size="16" />
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 300px;
  height: 100vh;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.3s ease;
  user-select: none;
}

.sidebar-header {
  padding: 24px 20px 16px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-mark {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, rgba(229, 180, 88, 0.2) 0%, rgba(229, 180, 88, 0.05) 100%);
  border: 1px solid rgba(229, 180, 88, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-icon {
  color: var(--accent-gold);
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.brand-name {
  font-size: 18px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.5px;
}

.brand-tag {
  font-size: 10px;
  font-weight: 600;
  color: var(--accent-cyan);
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

.new-action-wrap {
  padding: 0 16px 16px;
}

.btn-new-chat {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, rgba(229, 180, 88, 0.15) 0%, rgba(229, 180, 88, 0.05) 100%);
  border: 1px solid rgba(229, 180, 88, 0.35);
  color: var(--accent-gold);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-new-chat:hover {
  background: linear-gradient(135deg, rgba(229, 180, 88, 0.25) 0%, rgba(229, 180, 88, 0.1) 100%);
  box-shadow: 0 0 15px rgba(229, 180, 88, 0.2);
  transform: translateY(-1px);
}

.history-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0 12px;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 8px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-sub);
  text-transform: uppercase;
  letter-spacing: 0.9px;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
  color: var(--text-muted);
}

.history-item:hover {
  background: rgba(255, 255, 255, 0.04);
  color: #fff;
}

.history-item.active {
  background: var(--bg-tertiary);
  border-color: rgba(229, 180, 88, 0.25);
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.item-icon {
  flex-shrink: 0;
  color: var(--text-sub);
}

.history-item.active .item-icon {
  color: var(--accent-gold);
}

.item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.item-title {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-date {
  font-size: 11px;
  color: var(--text-sub);
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.btn-delete-session {
  background: transparent;
  border: none;
  color: var(--text-sub);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: all 0.2s ease;
}

.history-item:hover .btn-delete-session,
.history-item.active .btn-delete-session {
  opacity: 0.5;
}

.btn-delete-session:hover {
  opacity: 1 !important;
  color: #f87171;
  background: rgba(239, 68, 68, 0.15);
  transform: scale(1.1);
}

.item-arrow {
  opacity: 0;
  transition: opacity 0.15s ease;
  color: var(--text-sub);
}

.history-item:hover .item-arrow,
.history-item.active .item-arrow {
  opacity: 0.8;
}

.empty-history {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
  text-align: center;
  color: var(--text-sub);
}

.empty-icon {
  margin-bottom: 12px;
  opacity: 0.4;
}

.empty-history p {
  font-size: 12px;
  line-height: 1.5;
}

.agents-preview {
  padding: 14px 16px;
  border-top: 1px solid var(--border-subtle);
  background: rgba(10, 13, 20, 0.3);
}

.agent-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.agent-chip {
  font-size: 11px;
  font-weight: 500;
  padding: 3px 8px;
  border-radius: var(--radius-full);
  background: rgba(56, 189, 248, 0.08);
  border: 1px solid rgba(56, 189, 248, 0.2);
  color: var(--accent-cyan);
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg-primary);
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  border: 1px solid var(--glass-border);
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent-gold) 0%, #b8860b 100%);
  color: #0a0d14;
  font-weight: 800;
  font-size: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(229, 180, 88, 0.3);
}

.user-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.user-name {
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: 11px;
  color: var(--accent-cyan);
}

.btn-logout {
  background: none;
  border: none;
  color: var(--text-sub);
  cursor: pointer;
  padding: 6px;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-logout:hover {
  color: var(--accent-danger);
  background: rgba(244, 63, 94, 0.1);
}
</style>
