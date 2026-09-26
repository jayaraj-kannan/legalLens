<script setup>
import { ref, onMounted, computed, nextTick } from 'vue';
import { 
  Scale, FileText, Camera, UploadCloud, 
  Sparkles, CheckCircle, AlertCircle, Menu, PanelLeftClose, PanelLeft,
  MessageSquare, PanelRightClose, PanelRight, Edit2, Check, X
} from 'lucide-vue-next';

import AuthModal from './components/AuthModal.vue';
import Sidebar from './components/Sidebar.vue';
import InputArea from './components/InputArea.vue';
import MessageFeed from './components/MessageFeed.vue';
import CameraCapture from './components/CameraCapture.vue';
import ConsultationDashboard from './components/ConsultationDashboard.vue';
import AiAssistantDrawer from './components/AiAssistantDrawer.vue';

import { 
  uploadDocument, listDocuments, createSession, 
  listSessions, deleteSession, queryAgent,
  getSessionDashboard, analyzeDocument, analyzeSession,
  renameSession, getSessionDetails, getSessionEvents,
  saveSessionDashboard
} from './api';

// Authentication State
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

// Dashboard & AI Assistant Drawer State
const activeAnalysis = ref(null);
const activeDocument = ref(null);
const analysisLoading = ref(false);
const aiDrawerOpen = ref(true); // Default open aside with toggle

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
      await handleSelectSession(list[0].id);
      
      // Only show default welcome if no messages were restored from DB
      if (!messages.value || messages.value.length === 0) {
        messages.value = [
          {
            role: 'assistant',
            agentName: 'orchestrator_agent',
            text: `Welcome back, **${currentUser.value.name}**.\n\nI am the **LegalLens Multi-Agent Copilot**. Your active consultation breakdown and conversation history have been loaded from the database.\n\n• **Review highlighted risks & deadlines** in the center dashboard\n• **Ask follow-up questions** anytime in this AI Assistant panel\n• **Translate or redline** clauses with one click.`,
            documents: []
          }
        ];
      }
    } else {
      await startNewSession();
    }
  } catch (err) {
    console.warn('Backend initializing or offline:', err);
    activeSessionId.value = 'session_local_01';
    sessions.value = [{
      id: 'session_local_01',
      title: 'Commercial Lease Analysis',
      created_at: new Date().toISOString()
    }];
    await loadDefaultSample('lease');
  }
}

async function startNewSession() {
  try {
    const newSession = await createSession(currentUser.value.id, 'New Legal Consultation', []);
    sessions.value.unshift(newSession);
    activeSessionId.value = newSession.id;
    activeAnalysis.value = null;
    activeDocument.value = null;
    attachedDocuments.value = [];

    messages.value = [
      {
        role: 'assistant',
        agentName: 'orchestrator_agent',
        text: `New consultation opened. Upload a legal agreement or snap a photo of a contract to generate your structured breakdown dashboard.`,
        documents: []
      }
    ];
  } catch (err) {
    const fallbackId = 'session_' + Math.random().toString(36).substring(2, 8);
    activeSessionId.value = fallbackId;
    sessions.value.unshift({ id: fallbackId, title: 'New Legal Consultation', created_at: new Date().toISOString() });
    activeAnalysis.value = null;
    activeDocument.value = null;
  }
}

// Helper to reliably parse and reconstruct messages from database session events
function reconstructMessagesFromEvents(events) {
  const loadedMessages = [];
  for (const ev of events) {
    let payload = ev.payload;
    if (typeof payload === 'string') {
      try { payload = JSON.parse(payload); } catch (e) { payload = {}; }
    }
    payload = payload || {};

    const evType = ev.type || ev.event_type || payload.type;
    const promptText = ev.prompt || payload.prompt;
    const responseText = ev.text || payload.text || ev.response_text;
    const agentName = ev.agent_name || payload.agent_name || 'orchestrator_agent';
    const docNames = ev.document_ids || payload.document_ids || [];

    if (evType === 'user_query' || evType === 'user_stream_query') {
      loadedMessages.push({
        role: 'user',
        text: promptText || 'Consultation query',
        documents: docNames
      });
    } else if (evType === 'agent_response' || evType === 'agent_stream_response' || evType === 'document_uploaded') {
      loadedMessages.push({
        role: 'assistant',
        agentName: agentName,
        text: responseText || 'Analysis response',
        documents: docNames
      });
    }
  }
  return loadedMessages;
}

// Top Nav Inline Rename State
const isRenamingTop = ref(false);
const topRenameTitle = ref('');

function startTopRename() {
  isRenamingTop.value = true;
  topRenameTitle.value = activeSessionTitle.value;
  nextTick(() => {
    const input = document.getElementById('top-rename-input');
    if (input) {
      input.focus();
      input.select();
    }
  });
}

async function saveTopRename() {
  if (topRenameTitle.value.trim() && activeSessionId.value) {
    await handleRenameSession({ id: activeSessionId.value, title: topRenameTitle.value.trim() });
  }
  isRenamingTop.value = false;
}

function cancelTopRename() {
  isRenamingTop.value = false;
}

async function handleRenameSession({ id, title }) {
  try {
    const updated = await renameSession(id, title);
    const idx = sessions.value.findIndex(s => (s.id === id || s.session_id === id));
    if (idx !== -1) {
      sessions.value[idx].title = updated.title;
    }
    showToast(`Consultation renamed to "${updated.title}"`, 'success');
  } catch (err) {
    showToast('Failed to rename consultation: ' + err.message, 'error');
  }
}

async function handleSelectSession(sessionId) {
  activeSessionId.value = sessionId;
  analysisLoading.value = true;

  try {
    // 1. Fetch consultation details from Database (maps & seeds ADK session memory)
    const sessDetails = await getSessionDetails(sessionId);
    if (sessDetails) {
      const idx = sessions.value.findIndex(s => (s.id === sessionId || s.session_id === sessionId));
      if (idx !== -1) {
        sessions.value[idx] = { ...sessions.value[idx], ...sessDetails };
      }
    }

    // 2. Fetch structured breakdown dashboard for attached document
    const dash = await getSessionDashboard(sessionId);
    if (dash && dash.has_document && dash.analysis) {
      activeAnalysis.value = dash.analysis;
      activeDocument.value = dash.document;
      if (dash.document && !attachedDocuments.value.some(d => d.id === dash.document.id)) {
        attachedDocuments.value = [dash.document];
      }
    } else {
      activeAnalysis.value = null;
      activeDocument.value = null;
      attachedDocuments.value = [];
    }

    // 3. Fetch past conversation audit events from Database and reconstruct chat dialogue
    const eventData = await getSessionEvents(sessionId);
    if (eventData && eventData.events && eventData.events.length > 0) {
      const loadedMessages = reconstructMessagesFromEvents(eventData.events);
      if (loadedMessages.length > 0) {
        messages.value = loadedMessages;
      } else {
        messages.value = [
          {
            role: 'assistant',
            agentName: 'orchestrator_agent',
            text: `Consultation session **${activeSessionTitle.value}** loaded from database with ADK session memory mapped.\n\nAsk questions about the attached document or request clause redlines anytime.`,
            documents: []
          }
        ];
      }
    } else {
      messages.value = [
        {
          role: 'assistant',
          agentName: 'orchestrator_agent',
          text: `Consultation session **${activeSessionTitle.value}** loaded from database with ADK session memory mapped.\n\nAsk questions about the attached document or request clause redlines anytime.`,
          documents: []
        }
      ];
    }
  } catch (err) {
    console.warn('Could not load session details:', err);
  } finally {
    analysisLoading.value = false;
  }
}

async function handleDeleteSession(sessionId) {
  try {
    await deleteSession(sessionId, currentUser.value.id);
    sessions.value = sessions.value.filter(s => s.id !== sessionId);
    showToast('Consultation removed', 'info');

    if (activeSessionId.value === sessionId) {
      if (sessions.value.length > 0) {
        await handleSelectSession(sessions.value[0].id);
      } else {
        await startNewSession();
      }
    }
  } catch (err) {
    sessions.value = sessions.value.filter(s => s.id !== sessionId);
    if (activeSessionId.value === sessionId) {
      if (sessions.value.length > 0) {
        await handleSelectSession(sessions.value[0].id);
      } else {
        await startNewSession();
      }
    }
    showToast('Consultation removed', 'info');
  }
}

// 2. Handle File Upload & Dynamic Breakdown Extraction
async function handleFileUpload(file) {
  analysisLoading.value = true;
  showToast(`Uploading & extracting ${file.name}...`);

  try {
    const resp = await uploadDocument(file, currentUser.value.id, '', activeSessionId.value);
    const uploadedDoc = resp.document;

    attachedDocuments.value = [uploadedDoc];
    activeDocument.value = uploadedDoc;
    let analysis = uploadedDoc.custom_metadata?.analysis || null;

    // Check if extraction/analysis is still pending or processing
    const isPending = !analysis ||
      analysis.is_pending ||
      analysis.is_processing ||
      analysis.metrics?.overall_risk_label === 'Analysis Pending' ||
      analysis.legal_case?.straightforward_summary?.toLowerCase().includes('processing') ||
      analysis.legal_case_summary?.plain_verdict?.toLowerCase().includes('processing');

    if (isPending) {
      showToast('Document uploaded. Extracting full text & analyzing clauses...', 'info');
      // Actively wait for complete extraction and analysis to finish
      for (let attempt = 1; attempt <= 3; attempt++) {
        await new Promise(r => setTimeout(r, 1200 * attempt));
        try {
          const analyzeResp = await analyzeDocument(uploadedDoc.id);
          if (analyzeResp && analyzeResp.analysis) {
            const nextAnalysis = analyzeResp.analysis;
            const stillPending = nextAnalysis.is_pending ||
              nextAnalysis.is_processing ||
              nextAnalysis.metrics?.overall_risk_label === 'Analysis Pending' ||
              nextAnalysis.legal_case?.straightforward_summary?.toLowerCase().includes('processing') ||
              nextAnalysis.legal_case_summary?.plain_verdict?.toLowerCase().includes('processing');
            if (!stillPending) {
              analysis = nextAnalysis;
              break;
            }
          }
        } catch (e) {
          console.warn('Extraction retry check notice:', e);
        }
      }
    }

    activeAnalysis.value = analysis;
    showToast(`Breakdown generated for "${file.name}"!`, 'success');

    // Auto-save dashboard breakdown state to consultation record
    if (activeSessionId.value && activeAnalysis.value) {
      try {
        await saveSessionDashboard(activeSessionId.value, activeAnalysis.value);
      } catch (e) {
        console.warn('Dashboard save notice:', e);
      }
    }

    // Refresh messages from database so intake summary appears in chat feed
    try {
      const eventData = await getSessionEvents(activeSessionId.value);
      if (eventData && eventData.events && eventData.events.length > 0) {
        const loaded = reconstructMessagesFromEvents(eventData.events);
        if (loaded.length > 0) {
          messages.value = loaded;
        }
      }
    } catch (e) {
      messages.value.push({
        role: 'assistant',
        agentName: 'intake_parser_agent',
        text: `**Analysis Complete:** \`${uploadedDoc.original_filename}\` has been parsed and cataloged.\n\n• Document Nature: **${activeAnalysis.value?.nature_of_document?.document_type || activeAnalysis.value?.nature_of_document?.category || 'Legal Agreement'}**\n• Verdict: **${activeAnalysis.value?.legal_case_summary?.plain_verdict || 'Analyzed'}**\n• Risks Identified: **${activeAnalysis.value?.risks_and_inconsistencies?.length || 0} items**.\n\nThe central dashboard is updated.`,
        documents: [uploadedDoc.original_filename]
      });
    }
  } catch (err) {
    showToast(err.message || 'File upload failed', 'error');
  } finally {
    analysisLoading.value = false;
  }
}

// 3. Handle Camera Capture
async function handleCameraCapture(file) {
  showCamera.value = false;
  await handleFileUpload(file);
}

function handleRemoveDocument(docId) {
  attachedDocuments.value = attachedDocuments.value.filter(d => d.id !== docId);
  if (activeDocument.value?.id === docId) {
    activeDocument.value = null;
    activeAnalysis.value = null;
  }
  showToast('Document detached from consultation');
}

// 4. Re-analyze current document
async function handleReanalyze() {
  if (!activeSessionId.value) return;
  analysisLoading.value = true;
  showToast('Running deep multi-agent re-analysis...');

  try {
    const res = await analyzeSession(activeSessionId.value);
    if (res.analysis) {
      activeAnalysis.value = res.analysis;
      showToast('Dashboard updated with fresh analysis!', 'success');

      // Refresh messages from database
      try {
        const eventData = await getSessionEvents(activeSessionId.value);
        if (eventData && eventData.events && eventData.events.length > 0) {
          const loaded = reconstructMessagesFromEvents(eventData.events);
          if (loaded.length > 0) {
            messages.value = loaded;
          }
        }
      } catch (e) {
        messages.value.push({
          role: 'assistant',
          agentName: 'orchestrator_agent',
          text: `Re-analysis complete. Found **${res.analysis.risks_and_inconsistencies?.length || 0} risks** and **${res.analysis.deadlines?.length || 0} critical deadlines**.`,
          documents: []
        });
      }
    }
  } catch (err) {
    showToast('Re-analysis failed: ' + err.message, 'error');
  } finally {
    analysisLoading.value = false;
  }
}

// 5. Ask AI Assistant from dashboard or input
async function handleAskAi(promptText) {
  aiDrawerOpen.value = true;
  await handleQuerySubmit(promptText);
}

async function handleQuerySubmit(promptText) {
  if (!promptText) return;

  const currentDocs = [...attachedDocuments.value];
  const docNames = currentDocs.map(d => d.original_filename);
  const docIds = currentDocs.map(d => d.id);

  messages.value.push({
    role: 'user',
    text: promptText,
    documents: docNames
  });

  loading.value = true;

  try {
    const resp = await queryAgent(
      activeSessionId.value,
      currentUser.value.id,
      promptText,
      docIds
    );

    // Refresh chat messages directly from database session events
    try {
      const eventData = await getSessionEvents(activeSessionId.value);
      if (eventData && eventData.events && eventData.events.length > 0) {
        const loaded = reconstructMessagesFromEvents(eventData.events);
        if (loaded.length > 0) {
          messages.value = loaded;
          loading.value = false;
          return;
        }
      }
    } catch (e) {
      // Fallback
    }

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
      text: `⚠️ **Notice:** ${err.message}\n\nPlease ensure LegalLens backend and ADK server are running.`,
      documents: []
    });
  } finally {
    loading.value = false;
  }
}

// 6. Quick Load Sample Documents
async function handleLoadSample(type) {
  await loadDefaultSample(type);
}

async function loadDefaultSample(type) {
  analysisLoading.value = true;
  let filename = 'Sample_Contract.txt';
  let sampleContent = '';

  if (type === 'nda') {
    filename = 'Mutual_Non_Disclosure_Agreement.txt';
    sampleContent = `MUTUAL NON-DISCLOSURE AND CONFIDENTIALITY AGREEMENT
This Agreement is entered into as of November 1, 2026, by and between Apex Global Solutions Inc. ("Disclosing Party") and Veritas Analytics LLC ("Receiving Party").
Section 1. Purpose. The parties wish to explore a potential strategic software partnership.
Section 2. Confidentiality. Receiving Party agrees to hold all Proprietary Information in strict confidence for a term of 5 years.
Section 3. Non-Circumvention. Neither party shall directly contact or solicit employees or suppliers of the other for 24 months.
Section 4. Termination. Either party may terminate discussions upon 30 days prior written notice.
Section 5. Indemnification. Receiving Party agrees to defend, indemnify and hold harmless Disclosing Party against any and all claims, liabilities, and attorney fees arising from unauthorized disclosure.
Section 6. Governing Law. This Agreement shall be governed by the laws of the State of California, USA, with exclusive jurisdiction in San Francisco County.`;
  } else if (type === 'lease') {
    filename = 'Commercial_Office_Lease_Agreement.txt';
    sampleContent = `COMMERCIAL TRIPLE-NET LEASE AGREEMENT
This Commercial Lease Agreement is executed on October 15, 2026, by and between Metro Gateway Properties Ltd ("Landlord") and NovaTech Labs Corp ("Tenant").
Section 1. Leased Premises. Suite 400, 3,500 square feet situated at 100 Innovation Blvd, California.
Section 2. Term. Initial term of 36 months commencing December 1, 2026, and expiring November 30, 2029.
Section 3. Base Rent. Tenant shall pay Base Rent of $8,500.00 per month, due on the 1st day of each calendar month. A late charge of 5% applies after 5 business days, plus 18% annual interest.
Section 4. Security Deposit. Tenant shall deposit $17,000.00 (two months rent) upon signing.
Section 5. Auto-Renewal. This lease automatically renews for consecutive 1-year terms unless Tenant provides 60 days prior written notice.
Section 6. Maintenance & Taxes. Tenant shall be solely responsible for all interior maintenance, property taxes, and utility expenses.
Section 7. Default & Cure. Landlord may terminate upon 10 days notice for monetary default, and 15 days notice for non-monetary default.
Section 8. Indemnity & Uncapped Liability. Tenant agrees to indemnify Landlord from any casualty, damage, or legal dispute occurring on the premises.
Section 9. Dispute Resolution. All disputes shall be settled by binding arbitration in accordance with California law.`;
  } else {
    filename = 'Executive_Employment_Agreement.txt';
    sampleContent = `EXECUTIVE EMPLOYMENT AGREEMENT
Effective as of January 1, 2027, by and between Zenith Horizon Software Corp ("Company") and Jane Doe ("Executive").
Section 1. Position & Duties. Executive shall serve as Vice President of Engineering.
Section 2. Compensation. Annual base salary of $210,000, payable semi-monthly, plus eligibility for a 20% annual performance bonus.
Section 3. Intellectual Property. Executive assigns all inventions, patents, and copyrighted software created during employment to Company.
Section 4. Termination. Company may terminate Executive's employment with or without Cause upon 14 days written notice.
Section 5. Severance. Upon termination without Cause, Executive is entitled to 3 months severance salary conditioned on a full release of claims.
Section 6. Strict Non-Compete. Executive shall not engage in competing software activities within 50 miles for a period of 12 months post-employment.
Section 7. Governing Law. This contract is governed by the laws of the State of Delaware.`;
  }

  const blob = new Blob([sampleContent], { type: 'text/plain' });
  const file = new File([blob], filename, { type: 'text/plain' });
  await handleFileUpload(file);
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
    <!-- Left Column: Sessions Sidebar -->
    <Sidebar 
      v-if="!showAuthModal"
      :sessions="sessions"
      :active-session-id="activeSessionId"
      :current-user="currentUser"
      :collapsed="sidebarCollapsed"
      @select-session="handleSelectSession"
      @new-chat="startNewSession"
      @delete-session="handleDeleteSession"
      @rename-session="handleRenameSession"
      @logout="handleLogout"
    />

    <!-- Main Center Area: Top Navigation + Consultation Breakdown Dashboard -->
    <div v-if="!showAuthModal" class="main-center-wrapper">
      <!-- Top Navigation Bar -->
      <header class="top-nav">
        <div class="nav-left">
          <button class="btn-toggle-sidebar" @click="sidebarCollapsed = !sidebarCollapsed" title="Toggle Sidebar">
            <PanelLeft v-if="sidebarCollapsed" :size="20" />
            <PanelLeftClose v-else :size="20" />
          </button>
          
          <div class="logo-group">
            <span class="logo-title">LegalLens</span>

            <!-- Top Rename Inline -->
            <div v-if="isRenamingTop" class="top-rename-wrapper">
              <input 
                id="top-rename-input"
                v-model="topRenameTitle"
                class="top-rename-input"
                type="text"
                @keydown.enter="saveTopRename"
                @keydown.esc="cancelTopRename"
              />
              <button class="btn-top-save" @click="saveTopRename" title="Save Title"><Check :size="14" /></button>
              <button class="btn-top-cancel" @click="cancelTopRename" title="Cancel"><X :size="14" /></button>
            </div>

            <!-- Standard Top Session Badge with Edit Pen -->
            <div v-else class="session-badge-wrapper" @dblclick="startTopRename">
              <span class="session-badge">{{ activeSessionTitle }}</span>
              <button class="btn-edit-title-top" @click="startTopRename" title="Rename consultation">
                <Edit2 :size="12" />
              </button>
            </div>
          </div>
        </div>

        <div class="nav-right">
          <!-- Active Document Indicator -->
          <div class="context-indicator" :class="{ active: attachedDocuments.length > 0 }">
            <FileText :size="16" />
            <span>{{ activeDocument ? activeDocument.original_filename : 'No Active Document' }}</span>
          </div>

          <!-- AI Assistant Drawer Toggle Button -->
          <button 
            class="btn-toggle-ai-copilot" 
            :class="{ active: aiDrawerOpen }" 
            @click="aiDrawerOpen = !aiDrawerOpen"
            title="Toggle AI Legal Copilot"
          >
            <Sparkles :size="16" class="sparkle-icon" />
            <span>{{ aiDrawerOpen ? 'Hide AI Assistant' : 'AI Assistant' }}</span>
            <span class="badge-dot"></span>
          </button>

          <!-- Circular User Avatar Icon -->
          <button class="top-avatar-btn" @click="showAuthModal = true" title="View Account Details">
            <span>{{ currentUser.avatar || 'J' }}</span>
          </button>
        </div>
      </header>

      <!-- Center Hero: Consultation Breakdown Dashboard -->
      <main class="center-dashboard-stage">
        <ConsultationDashboard
          :analysis="activeAnalysis"
          :document="activeDocument"
          :loading="analysisLoading"
          :session-id="activeSessionId"
          @upload-file="handleFileUpload"
          @open-camera="showCamera = true"
          @reanalyze="handleReanalyze"
          @ask-ai="handleAskAi"
          @load-sample="handleLoadSample"
        />
      </main>
    </div>

    <!-- Right Column: Collapsible AI Assistant Drawer -->
    <AiAssistantDrawer
      v-if="!showAuthModal"
      :is-open="aiDrawerOpen"
      :messages="messages"
      :loading="loading"
      :attached-documents="attachedDocuments"
      @close="aiDrawerOpen = false"
      @send-query="handleQuerySubmit"
    />

    <!-- Auth Modal -->
    <AuthModal 
      v-if="showAuthModal"
      @auth-success="handleAuthSuccess" 
    />

    <!-- Camera Scanner View -->
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

/* Center Stage Area */
.main-center-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100vh;
  min-width: 0;
  position: relative;
  background: var(--bg-primary);
}

.center-dashboard-stage {
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* Top Navigation Bar */
.top-nav {
  height: 64px;
  background: var(--glass-surface);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  backdrop-filter: blur(12px);
  z-index: 20;
  flex-shrink: 0;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.btn-toggle-sidebar {
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

.btn-toggle-sidebar:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-main);
}

.logo-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-title {
  font-size: 1.25rem;
  font-weight: 800;
  letter-spacing: -0.5px;
  background: linear-gradient(135deg, #f1f5f9 0%, #e5b458 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.session-badge-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.session-badge {
  font-size: 0.8rem;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.04);
  padding: 4px 10px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-subtle);
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: all 0.2s;
}

.session-badge-wrapper:hover .session-badge {
  border-color: rgba(229, 180, 88, 0.35);
  color: var(--text-main);
}

.btn-edit-title-top {
  background: transparent;
  border: none;
  color: var(--text-sub);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.6;
  transition: all 0.2s;
}

.session-badge-wrapper:hover .btn-edit-title-top {
  opacity: 1;
  color: var(--accent-gold);
}

.btn-edit-title-top:hover {
  background: rgba(229, 180, 88, 0.15);
  transform: scale(1.1);
}

.top-rename-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
}

.top-rename-input {
  background: var(--bg-tertiary);
  border: 1px solid var(--accent-gold);
  border-radius: var(--radius-sm);
  color: #fff;
  font-size: 0.82rem;
  padding: 4px 10px;
  outline: none;
  font-family: inherit;
  min-width: 200px;
}

.btn-top-save, .btn-top-cancel {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.btn-top-save {
  color: var(--accent-success);
}

.btn-top-save:hover {
  background: rgba(16, 185, 129, 0.2);
}

.btn-top-cancel {
  color: var(--text-sub);
}

.btn-top-cancel:hover {
  color: var(--accent-danger);
  background: rgba(244, 63, 94, 0.2);
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.context-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-full);
  font-size: 0.82rem;
  color: var(--text-sub);
  max-width: 240px;
}

.context-indicator span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.context-indicator.active {
  background: rgba(56, 189, 248, 0.1);
  border-color: rgba(56, 189, 248, 0.3);
  color: var(--accent-cyan);
}

/* AI Copilot Toggle Button */
.btn-toggle-ai-copilot {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 16px;
  border-radius: var(--radius-full);
  background: rgba(229, 180, 88, 0.1);
  border: 1px solid rgba(229, 180, 88, 0.3);
  color: var(--accent-gold);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
}

.btn-toggle-ai-copilot:hover {
  background: rgba(229, 180, 88, 0.2);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(229, 180, 88, 0.2);
}

.btn-toggle-ai-copilot.active {
  background: linear-gradient(135deg, rgba(229, 180, 88, 0.25) 0%, rgba(202, 160, 73, 0.35) 100%);
  border-color: var(--accent-gold);
  color: #fff;
}

.sparkle-icon {
  color: var(--accent-gold);
  animation: pulseGlow 2s infinite ease-in-out;
}

.badge-dot {
  width: 7px;
  height: 7px;
  background: var(--accent-success);
  border-radius: 50%;
}

.top-avatar-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border: 1.5px solid var(--accent-gold);
  color: var(--accent-gold);
  font-weight: 700;
  font-size: 0.95rem;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 0 12px rgba(229, 180, 88, 0.2);
}

.top-avatar-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 0 16px rgba(229, 180, 88, 0.35);
}

/* Toast Notifications */
.toast-box {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-full);
  font-size: 0.88rem;
  color: var(--text-main);
  box-shadow: var(--shadow-lg);
  z-index: 100;
}

.toast-box.success {
  border-color: rgba(16, 185, 129, 0.4);
  color: var(--accent-success);
}

.toast-box.error {
  border-color: rgba(244, 63, 94, 0.4);
  color: var(--accent-danger);
}

.toast-box.info {
  border-color: rgba(56, 189, 248, 0.4);
  color: var(--accent-cyan);
}
</style>
