<script setup>
import { ref, onMounted, computed, nextTick } from 'vue';
import { 
  Scale, FileText, Camera, UploadCloud, 
  Sparkles, CheckCircle, AlertCircle, Menu, PanelLeftClose, PanelLeft
} from 'lucide-vue-next';

import AuthModal from './components/AuthModal.vue';
import Sidebar from './components/Sidebar.vue';
import InputArea from './components/InputArea.vue';
import MessageFeed from './components/MessageFeed.vue';
import CameraCapture from './components/CameraCapture.vue';

import { 
  uploadDocument, listDocuments, createSession, 
  listSessions, deleteSession, queryAgent 
} from './api';

// Authentication State (defaults to logged in user matching sketch avatar 'J')
const currentUser = ref({
  id: 'user_default_advocate',
  name: 'Jayaraj Kannan',
  email: 'jrajfx@gmail.com',
  avatar: 'J'
});
const showAuthModal = ref(false);

// App Navigation & Session State
const sessions = ref([]);
const activeSessionId = ref('');
const messages = ref([]);
const loading = ref(false);
const sidebarCollapsed = ref(false);

// Document & Attachment State
const attachedDocuments = ref([]);
const showCamera = ref(false);
const toastMessage = ref('');
const toastType = ref('success');

// Active Session Title computed
const activeSessionTitle = computed(() => {
  const current = sessions.value.find(s => s.id === activeSessionId.value);
  return current ? current.title : 'Legal Contract Analysis';
});

function showToast(msg, type = 'success') {
  toastMessage.value = msg;
  toastType.value = type;
  setTimeout(() => { toastMessage.value = ''; }, 3500);
}

// 1. Initialize sessions on mount
async function initializeApp() {
  try {
    const list = await listSessions(currentUser.value.id);
    sessions.value = list;

    if (list.length > 0) {
      activeSessionId.value = list[0].id;
      // Load sample welcome message
      messages.value = [
        {
          role: 'assistant',
          agentName: 'orchestrator_agent',
          text: `Welcome back, **${currentUser.value.name}**.\n\nI am the **LegalLens Response Orchestrator**. You can upload any agreement (Rental, NDA, Employment, Loan, Service Agreement) or snap a photo of a physical contract page to:\n\n• **Detect risky or hidden clauses** (indemnity, auto-renewal, liabilities)\n• **Generate a chronological timeline** of notice deadlines and payment terms\n• **Translate & explain** in plain language or regional Indian languages\n• **Prepare strategic questions** for your lawyer consultation\n\nHow may I assist you today?`,
          documents: []
        }
      ];
    } else {
      await startNewSession();
    }
  } catch (err) {
    console.warn('Backend offline or initializing:', err);
    // Create local fallback session
    activeSessionId.value = 'session_local_01';
    sessions.value = [{
      id: 'session_local_01',
      title: 'Lease Agreement Review',
      created_at: new Date().toISOString()
    }];
    messages.value = [
      {
        role: 'assistant',
        agentName: 'orchestrator_agent',
        text: `Welcome to **LegalLens Multi-Agent Copilot**.\n\nAttach any legal document or ask a question below. Our specialist agents are standing by to parse clauses, verify citations, and identify risks.`,
        documents: []
      }
    ];
  }
}

async function startNewSession() {
  try {
    const newSession = await createSession(currentUser.value.id, 'New Legal Consultation', []);
    sessions.value.unshift(newSession);
    activeSessionId.value = newSession.id;
    messages.value = [
      {
        role: 'assistant',
        agentName: 'orchestrator_agent',
        text: `New consultation started. Attach your legal agreement (via the **+** button) or snap a page with your camera to begin.`,
        documents: []
      }
    ];
    attachedDocuments.value = [];
  } catch (err) {
    const fallbackId = 'session_' + Math.random().toString(36).substring(2, 8);
    activeSessionId.value = fallbackId;
    sessions.value.unshift({ id: fallbackId, title: 'New Legal Consultation', created_at: new Date().toISOString() });
    messages.value = [];
  }
}

function handleSelectSession(sessionId) {
  activeSessionId.value = sessionId;
  showToast('Switched consultation session');
}

async function handleDeleteSession(sessionId) {
  try {
    await deleteSession(sessionId, currentUser.value.id);
    sessions.value = sessions.value.filter(s => s.id !== sessionId);
    showToast('Consultation deleted', 'info');

    // If the currently viewed session was deleted, switch or start a new one
    if (activeSessionId.value === sessionId) {
      if (sessions.value.length > 0) {
        activeSessionId.value = sessions.value[0].id;
        messages.value = [
          {
            role: 'assistant',
            agentName: 'orchestrator_agent',
            text: `Consultation switched to **${sessions.value[0].title || 'Legal Consultation'}**. How can I help you with this matter?`,
            documents: []
          }
        ];
      } else {
        await startNewSession();
      }
    }
  } catch (err) {
    console.error('Delete session error:', err);
    // Remove locally as fallback
    sessions.value = sessions.value.filter(s => s.id !== sessionId);
    if (activeSessionId.value === sessionId) {
      if (sessions.value.length > 0) {
        activeSessionId.value = sessions.value[0].id;
      } else {
        await startNewSession();
      }
    }
    showToast('Consultation removed', 'info');
  }
}

// 2. Handle File Upload (Matches (+) attachment in sketch)
async function handleFileUpload(file) {
  try {
    showToast(`Uploading ${file.name} to Google Cloud Storage...`);
    const resp = await uploadDocument(file, currentUser.value.id);
    attachedDocuments.value.push(resp.document);
    showToast(`Uploaded "${file.name}" to GCS!`, 'success');

    // Notify user in chat feed
    messages.value.push({
      role: 'assistant',
      agentName: 'intake_parser_agent',
      text: `**Document Ingested:** \`${resp.document.original_filename}\` has been parsed and stored in Google Cloud Storage.\n\nYou can now ask specific questions or request risk analysis, clause breakdown, and timeline extraction.`,
      documents: [resp.document.original_filename]
    });
  } catch (err) {
    showToast(err.message || 'File upload failed', 'error');
  }
}

// 3. Handle Camera Capture (Matches "snap with camera" in sketch)
async function handleCameraCapture(file) {
  showCamera.value = false;
  await handleFileUpload(file);
}

function handleRemoveDocument(docId) {
  attachedDocuments.value = attachedDocuments.value.filter(d => d.id !== docId);
  showToast('Document detached from active context');
}

// 4. Handle Query Submit (Matches send in sketch)
async function handleQuerySubmit(promptText) {
  if (!promptText && attachedDocuments.value.length === 0) return;

  const currentDocs = [...attachedDocuments.value];
  const docNames = currentDocs.map(d => d.original_filename);
  const docIds = currentDocs.map(d => d.id);

  // Push user prompt to message list
  messages.value.push({
    role: 'user',
    text: promptText,
    documents: docNames
  });

  loading.value = true;
  await nextTick();
  scrollToBottom();

  try {
    const resp = await queryAgent(
      activeSessionId.value,
      currentUser.value.id,
      promptText,
      docIds
    );

    messages.value.push({
      role: 'assistant',
      agentName: resp.agent_name || 'orchestrator_agent',
      text: resp.response_text,
      documents: docNames
    });
  } catch (err) {
    messages.value.push({
      role: 'assistant',
      agentName: 'orchestrator_agent',
      text: `⚠️ **Agent Execution Notice:** ${err.message}\n\nPlease verify that the LegalLens backend (` + 'http://127.0.0.1:8080' + `) and ADK server are running.`,
      documents: []
    });
  } finally {
    loading.value = false;
    await nextTick();
    scrollToBottom();
  }
}

function scrollToBottom() {
  const container = document.getElementById('chat-scroll-container');
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
}

function handleAuthSuccess(user) {
  currentUser.value = user;
  showAuthModal.value = false;
  showToast(`Welcome, ${user.name}!`);
}

function handleLogout() {
  showAuthModal.value = true;
}

onMounted(() => {
  initializeApp();
});
</script>

<template>
  <div class="app-layout">
    <!-- Left Column: Chat History & User Profile (Middle-Left sketched column) -->
    <Sidebar 
      v-if="!showAuthModal"
      :sessions="sessions"
      :active-session-id="activeSessionId"
      :current-user="currentUser"
      :collapsed="sidebarCollapsed"
      @select-session="handleSelectSession"
      @new-chat="startNewSession"
      @delete-session="handleDeleteSession"
      @logout="handleLogout"
    />

    <!-- Main Consultation Pane (Right side of sketch with Header, Logo, Feed & Input) -->
    <main v-if="!showAuthModal" class="main-content">
      <!-- Top Navigation Bar matching Logo + Profile Icon (J) in sketch -->
      <header class="top-nav">
        <div class="nav-left">
          <button class="btn-toggle-sidebar" @click="sidebarCollapsed = !sidebarCollapsed" title="Toggle Sidebar">
            <PanelLeft v-if="sidebarCollapsed" :size="20" />
            <PanelLeftClose v-else :size="20" />
          </button>
          
          <div class="logo-group">
            <span class="logo-title">LegalLens</span>
            <span class="session-badge">{{ activeSessionTitle }}</span>
          </div>
        </div>

        <div class="nav-right">
          <!-- Attached Document Count indicator (matches [file] in sketch top right) -->
          <div class="context-indicator" :class="{ active: attachedDocuments.length > 0 }">
            <FileText :size="16" />
            <span>{{ attachedDocuments.length }} Active {{ attachedDocuments.length === 1 ? 'Doc' : 'Docs' }}</span>
          </div>

          <!-- Circular User Avatar Icon (Matches (J) in sketch top right) -->
          <button class="top-avatar-btn" @click="showAuthModal = true" title="View Account Details">
            <span>{{ currentUser.avatar || 'J' }}</span>
          </button>
        </div>
      </header>

      <!-- Message History Display Area (matches stacked message bubbles/boxes in sketch) -->
      <section id="chat-scroll-container" class="conversation-scroll">
        <MessageFeed 
          :messages="messages" 
          :loading="loading" 
        />
      </section>

      <!-- Centered Input Area with (+) attachment and send button (matches input area in sketch) -->
      <footer class="input-dock">
        <InputArea 
          :loading="loading"
          :selected-documents="attachedDocuments"
          @submit="handleQuerySubmit"
          @upload-file="handleFileUpload"
          @open-camera="showCamera = true"
          @remove-document="handleRemoveDocument"
        />
      </footer>
    </main>

    <!-- Auth Modal / View (matching left column of user's sketch with Google Sign In & Sign Up) -->
    <AuthModal 
      v-if="showAuthModal"
      @auth-success="handleAuthSuccess" 
    />

    <!-- Camera Scanner View (matches "snap with camera" annotation in sketch) -->
    <CameraCapture 
      v-if="showCamera"
      @capture="handleCameraCapture"
      @close="showCamera = false"
    />

    <!-- Toast Notification Overlay -->
    <div v-if="toastMessage" class="toast-box fade-in" :class="[toastType]">
      <CheckCircle v-if="toastType === 'success'" :size="16" />
      <AlertCircle v-else :size="16" />
      <span>{{ toastMessage }}</span>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  width: 100vw;
  height: 100vh;
  background: var(--bg-primary);
  overflow: hidden;
  position: relative;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: relative;
  background: radial-gradient(circle at 50% 0%, rgba(56, 189, 248, 0.03) 0%, transparent 50%),
              radial-gradient(circle at 100% 100%, rgba(229, 180, 88, 0.03) 0%, transparent 50%),
              var(--bg-primary);
}

/* Top Nav matching Logo + Avatar (J) in sketch */
.top-nav {
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-subtle);
  background: rgba(10, 13, 20, 0.85);
  backdrop-filter: blur(12px);
  z-index: 10;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.btn-toggle-sidebar {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 6px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
}
.btn-toggle-sidebar:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.06);
}

.logo-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-title {
  font-size: 19px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.5px;
}

.session-badge {
  font-size: 12px;
  color: var(--text-sub);
  background: var(--bg-tertiary);
  padding: 4px 10px;
  border-radius: var(--radius-full);
  border: 1px solid var(--glass-border);
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.context-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-full);
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  font-size: 12px;
  color: var(--text-sub);
  transition: all 0.2s ease;
}

.context-indicator.active {
  background: rgba(56, 189, 248, 0.1);
  border-color: rgba(56, 189, 248, 0.35);
  color: var(--accent-cyan);
}

/* Sketched circle Avatar (J) at top right */
.top-avatar-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent-gold) 0%, #b8860b 100%);
  border: 2px solid rgba(255, 255, 255, 0.15);
  color: #0a0d14;
  font-weight: 800;
  font-size: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(229, 180, 88, 0.3);
  transition: transform 0.15s ease;
}

.top-avatar-btn:hover {
  transform: scale(1.08);
}

/* Chat scroll area */
.conversation-scroll {
  flex: 1;
  overflow-y: auto;
  scroll-behavior: smooth;
  display: flex;
  flex-direction: column;
}

/* Input dock at the bottom */
.input-dock {
  background: linear-gradient(180deg, transparent 0%, rgba(10, 13, 20, 0.95) 40%, var(--bg-primary) 100%);
  backdrop-filter: blur(8px);
}

/* Toast Overlay */
.toast-box {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 12px 18px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  font-weight: 600;
  box-shadow: var(--shadow-lg);
  z-index: 2000;
}

.toast-box.success {
  background: var(--bg-tertiary);
  border: 1px solid rgba(16, 185, 129, 0.35);
  color: #fff;
}

.toast-box.error {
  background: rgba(244, 63, 94, 0.15);
  border: 1px solid var(--accent-danger);
  color: #fff;
}
</style>
