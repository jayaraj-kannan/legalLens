<script setup>
import { ref, computed } from 'vue';
import { 
  FileText, ShieldAlert, AlertTriangle, CheckCircle2, Clock, 
  Calendar, DollarSign, Gavel, Scale, AlertCircle, Sparkles, 
  RefreshCw, Copy, Check, ChevronRight, MessageSquare, ArrowUpRight,
  HelpCircle, ShieldCheck, Layers, Landmark, UserCheck
} from 'lucide-vue-next';

const props = defineProps({
  analysis: {
    type: Object,
    default: null
  },
  document: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  sessionId: {
    type: String,
    default: ''
  }
});

const emit = defineEmits([
  'upload-file',
  'open-camera',
  'reanalyze',
  'ask-ai',
  'load-sample'
]);

// Active Navigation Tab
const activeTab = ref('overview');
const copiedSummary = ref(false);

const tabs = [
  { id: 'overview', label: '🏛️ Overview & Case', count: null },
  { id: 'risks', label: '🚨 Risks & Red Flags', count: computed(() => props.analysis?.risks_and_inconsistencies?.length || 0) },
  { id: 'clauses', label: '📑 Key Clauses', count: computed(() => props.analysis?.important_clauses?.length || 0) },
  { id: 'deadlines', label: '⏳ Deadlines & Dates', count: computed(() => props.analysis?.deadlines?.length || 0) },
  { id: 'obligations', label: '📋 Obligations Matrix', count: computed(() => props.analysis?.obligations?.length || 0) },
  { id: 'policies', label: '📜 Policies & Law', count: computed(() => props.analysis?.agreements_and_policies?.length || 0) },
  { id: 'lawyer', label: '💼 Lawyer Prep', count: computed(() => props.analysis?.lawyer_checklist?.length || 0) },
];

// Computed helpers
const nature = computed(() => props.analysis?.nature_of_document || {});
const legalCase = computed(() => props.analysis?.legal_case || {});
const deadlines = computed(() => props.analysis?.deadlines || []);
const details = computed(() => props.analysis?.contract_details || {});
const clauses = computed(() => props.analysis?.important_clauses || []);
const obligations = computed(() => props.analysis?.obligations || []);
const risks = computed(() => props.analysis?.risks_and_inconsistencies || []);
const policies = computed(() => props.analysis?.agreements_and_policies || []);
const checklist = computed(() => props.analysis?.lawyer_checklist || []);
const metrics = computed(() => props.analysis?.metrics || {
  overall_risk_score: 70,
  overall_risk_label: 'Moderate Risk',
  high_risk_count: 0,
  medium_risk_count: 0,
  deadlines_count: 0,
  key_clauses_count: 0
});

const riskColor = computed(() => {
  const score = metrics.value.overall_risk_score || 50;
  if (score >= 75) return 'var(--accent-success)';
  if (score >= 50) return 'var(--accent-warning)';
  return 'var(--accent-danger)';
});

function copySummaryText() {
  const text = `LegalLens Breakdown for ${nature.value.title || 'Document'}\nType: ${nature.value.document_type}\nSummary: ${legalCase.value.straightforward_summary}\nVerdict: ${legalCase.value.bottom_line_verdict}`;
  navigator.clipboard.writeText(text);
  copiedSummary.value = true;
  setTimeout(() => { copiedSummary.value = false; }, 2000);
}

function handleAskAi(prompt) {
  emit('ask-ai', prompt);
}

function triggerFileInput() {
  document.getElementById('dash-file-input')?.click();
}

const isExtractingOrAnalyzing = computed(() => {
  if (props.loading) return true;
  if (!props.analysis || !props.document) return false;
  // If analysis is in pending or processing extraction state, keep showing the loading state
  if (props.analysis.is_pending || props.analysis.is_processing) return true;
  if (props.analysis.metrics?.overall_risk_label === 'Analysis Pending') return true;
  if (props.analysis.legal_case?.straightforward_summary?.toLowerCase().includes('processing')) return true;
  if (props.analysis.legal_case_summary?.plain_verdict?.toLowerCase().includes('processing')) return true;
  return false;
});

function onFileSelected(event) {
  const file = event.target.files?.[0];
  if (file) {
    emit('upload-file', file);
    event.target.value = '';
  }
}
</script>

<template>
  <div class="dashboard-container">
    <!-- 1. LOADING & EXTRACTION STATE -->
    <div v-if="isExtractingOrAnalyzing" class="dash-loading-card fade-in">
      <div class="spinner-ring"></div>
      <div class="loading-text-group">
        <div class="loading-doc-badge" v-if="props.document">
          <FileText :size="15" />
          <span>{{ props.document?.original_filename || 'Legal Document' }}</span>
        </div>
        <h3>Extracting Document & Analyzing Clauses...</h3>
        <p>
          Full text and scanned pages are being extracted. Google ADK specialist agents are cataloging obligations, detecting unilateral risks, and synthesizing plain-language answers.
        </p>

        <!-- Dynamic 3-stage progress indicator -->
        <div class="loading-stepper">
          <div class="step-badge done">
            <CheckCircle2 :size="14" />
            <span>Document Uploaded</span>
          </div>
          <div class="step-divider done"></div>
          <div class="step-badge active">
            <RefreshCw :size="14" class="spin-icon" />
            <span>Full-Text & OCR Extraction</span>
          </div>
          <div class="step-divider"></div>
          <div class="step-badge pending">
            <Sparkles :size="14" />
            <span>Multi-Agent Breakdown</span>
          </div>
        </div>

        <div class="loading-actions">
          <button class="btn-check-status" @click="emit('reanalyze')">
            <RefreshCw :size="14" />
            <span>Refresh Analysis Status</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 2. EMPTY STATE: UPLOAD & SAMPLE TRIGGER -->
    <div v-else-if="!analysis || !props.document" class="dash-empty-state fade-in">
      <div class="empty-hero-card">
        <div class="empty-icon-halo">
          <Scale :size="48" class="hero-scale-icon" />
        </div>
        <h2>LegalLens Consultation Breakdown</h2>
        <p class="hero-subtitle">
          Upload any legal contract to immediately generate a comprehensive, structured dashboard with straightforward answers on document nature, deadlines, high-risk clauses, obligations, and lawyer prep.
        </p>

        <div class="hero-actions-row">
          <input 
            type="file" 
            id="dash-file-input" 
            class="hidden-file-input" 
            accept=".pdf,.docx,.txt,image/*" 
            @change="onFileSelected" 
          />
          <button class="btn-primary-action" @click="triggerFileInput">
            <FileText :size="18" />
            <span>Upload Contract (PDF / DOCX / TXT)</span>
          </button>

          <button class="btn-secondary-action" @click="emit('open-camera')">
            <Camera :size="18" />
            <span>Snap Physical Contract with Camera</span>
          </button>
        </div>

        <!-- Quick Sample Document Selectors for instant testing -->
        <div class="samples-section">
          <span class="sample-label">Or test with pre-analyzed sample contract:</span>
          <div class="samples-badges">
            <button class="sample-btn" @click="emit('load-sample', 'nda')">
              <span>📄 Mutual NDA</span>
              <ArrowUpRight :size="14" />
            </button>
            <button class="sample-btn" @click="emit('load-sample', 'lease')">
              <span>🏢 Commercial Lease</span>
              <ArrowUpRight :size="14" />
            </button>
            <button class="sample-btn" @click="emit('load-sample', 'employment')">
              <span>💼 Employment Agreement</span>
              <ArrowUpRight :size="14" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. ACTIVE BREAKDOWN DASHBOARD VIEW -->
    <div v-else class="dash-active-content fade-in">
      <!-- TOP HERO BANNER: NATURE OF DOCUMENT & BOTTOM LINE -->
      <section class="dash-hero-header">
        <div class="header-left">
          <div class="doc-badge-row">
            <span class="type-pill">
              <Landmark :size="13" />
              {{ nature.document_type || 'Legal Agreement' }}
            </span>
            <span class="category-pill">{{ nature.category || 'Commercial' }}</span>
            <span class="status-pill">{{ nature.execution_status || 'Under Review' }}</span>
          </div>
          <h1 class="doc-main-title">{{ nature.title || document?.original_filename || 'Legal Consultation' }}</h1>
          <div class="doc-meta-sub">
            <span><strong>Governing Law:</strong> {{ nature.governing_law }}</span>
            <span class="separator">•</span>
            <span><strong>Jurisdiction:</strong> {{ nature.jurisdiction }}</span>
          </div>
        </div>

        <div class="header-right">
          <!-- Overall Risk Gauge Card -->
          <div class="risk-gauge-card">
            <div class="gauge-label">
              <span>Contract Risk Score</span>
              <span class="risk-text" :style="{ color: riskColor }">{{ metrics.overall_risk_label }}</span>
            </div>
            <div class="gauge-meter-wrapper">
              <div class="meter-bar">
                <div class="meter-fill" :style="{ width: `${metrics.overall_risk_score}%`, backgroundColor: riskColor }"></div>
              </div>
              <span class="gauge-score" :style="{ color: riskColor }">{{ metrics.overall_risk_score }}/100</span>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="hero-actions">
            <button class="btn-dash-action" @click="copySummaryText" title="Copy Executive Summary">
              <Check v-if="copiedSummary" :size="16" class="check-icon" />
              <Copy v-else :size="16" />
              <span>{{ copiedSummary ? 'Copied' : 'Share Summary' }}</span>
            </button>
            <button class="btn-dash-action highlight" @click="emit('reanalyze')" title="Run Deep Re-analysis">
              <RefreshCw :size="16" />
              <span>Re-analyze</span>
            </button>
          </div>
        </div>
      </section>

      <!-- STRAIGHTFORWARD ANSWER BANNER (HERO VERDICT) -->
      <section class="verdict-banner-card">
        <div class="verdict-header">
          <div class="verdict-icon-box">
            <Sparkles :size="20" />
          </div>
          <div class="verdict-title-group">
            <h3>Straightforward Legal Verdict</h3>
            <span class="verdict-sub">Direct, jargon-free summary & bottom-line consultation advice</span>
          </div>
        </div>
        
        <p class="verdict-summary">{{ legalCase.straightforward_summary }}</p>
        
        <div class="verdict-footer-quote">
          <AlertCircle :size="16" class="alert-icon" />
          <span><strong>Bottom Line:</strong> {{ legalCase.bottom_line_verdict }}</span>
        </div>
      </section>

      <!-- KPI METRIC CARDS ROW -->
      <section class="kpi-grid">
        <div class="kpi-card" @click="activeTab = 'deadlines'">
          <div class="kpi-icon-box blue">
            <Clock :size="18" />
          </div>
          <div class="kpi-content">
            <span class="kpi-label">Critical Deadlines</span>
            <span class="kpi-val">{{ deadlines.length }} Notice / Dates</span>
            <span class="kpi-sub">Term: {{ legalCase.validity_term || '12 Months' }}</span>
          </div>
        </div>

        <div class="kpi-card" @click="activeTab = 'risks'">
          <div class="kpi-icon-box red">
            <ShieldAlert :size="18" />
          </div>
          <div class="kpi-content">
            <span class="kpi-label">Flagged Risks</span>
            <span class="kpi-val">{{ metrics.high_risk_count }} High • {{ metrics.medium_risk_count }} Medium</span>
            <span class="kpi-sub">Unbalanced clauses identified</span>
          </div>
        </div>

        <div class="kpi-card" @click="activeTab = 'overview'">
          <div class="kpi-icon-box gold">
            <DollarSign :size="18" />
          </div>
          <div class="kpi-content">
            <span class="kpi-label">Financial Terms</span>
            <span class="kpi-val">{{ details.financial_consideration || 'Mutual Consideration' }}</span>
            <span class="kpi-sub">{{ details.payment_schedule || 'Net Terms' }}</span>
          </div>
        </div>

        <div class="kpi-card" @click="activeTab = 'clauses'">
          <div class="kpi-icon-box green">
            <Layers :size="18" />
          </div>
          <div class="kpi-content">
            <span class="kpi-label">Key Clauses</span>
            <span class="kpi-val">{{ clauses.length }} Categorized</span>
            <span class="kpi-sub">Citations & Quotes verified</span>
          </div>
        </div>
      </section>

      <!-- DASHBOARD NAVIGATION TABS -->
      <nav class="dash-tabs-nav">
        <button 
          v-for="t in tabs" 
          :key="t.id" 
          class="dash-tab-btn" 
          :class="{ active: activeTab === t.id }"
          @click="activeTab = t.id"
        >
          <span>{{ t.label }}</span>
          <span v-if="t.count !== null && t.count > 0" class="tab-badge">{{ t.count }}</span>
        </button>
      </nav>

      <!-- TAB CONTENT PANES -->
      <main class="dash-tab-body">
        <!-- 1. OVERVIEW & CASE CONTEXT TAB -->
        <section v-if="activeTab === 'overview'" class="tab-pane fade-in">
          <div class="grid-2-col">
            <!-- Left: Document Nature & Parties -->
            <div class="glass-card">
              <div class="card-header">
                <Landmark :size="18" class="card-icon" />
                <h4>Nature of Document & Parties</h4>
              </div>
              <div class="card-body">
                <div class="field-item">
                  <span class="field-label">Document Nature:</span>
                  <span class="field-value">{{ nature.document_type }}</span>
                </div>
                <div class="field-item">
                  <span class="field-label">Governing Law:</span>
                  <span class="field-value">{{ nature.governing_law }}</span>
                </div>
                <div class="field-item">
                  <span class="field-label">Jurisdiction & Forum:</span>
                  <span class="field-value">{{ nature.jurisdiction }}</span>
                </div>
                <div class="field-item">
                  <span class="field-label">Primary Commercial Intent:</span>
                  <span class="field-value">{{ legalCase.primary_intent }}</span>
                </div>

                <div class="parties-list-section">
                  <span class="field-label">Identified Contracting Parties:</span>
                  <div class="parties-grid">
                    <div v-for="(p, idx) in nature.parties" :key="idx" class="party-badge-card">
                      <UserCheck :size="16" class="party-icon" />
                      <div class="party-info">
                        <strong>{{ p.name }}</strong>
                        <span class="party-role">{{ p.role }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Right: Contract Details & Financials -->
            <div class="glass-card">
              <div class="card-header">
                <DollarSign :size="18" class="card-icon" />
                <h4>Financial Terms & Contract Duration</h4>
              </div>
              <div class="card-body">
                <div class="field-item">
                  <span class="field-label">Financial Consideration:</span>
                  <span class="field-value highlight-gold">{{ details.financial_consideration || 'None specified' }}</span>
                </div>
                <div class="field-item">
                  <span class="field-label">Security Deposit / Escrow:</span>
                  <span class="field-value">{{ details.security_deposit || 'N/A' }}</span>
                </div>
                <div class="field-item">
                  <span class="field-label">Payment Due Schedule:</span>
                  <span class="field-value">{{ details.payment_schedule || 'Standard' }}</span>
                </div>
                <div class="field-item">
                  <span class="field-label">Late Payment Penalties:</span>
                  <span class="field-value">{{ details.late_penalty || 'Statutory Interest' }}</span>
                </div>
                <div class="field-item">
                  <span class="field-label">Term Length:</span>
                  <span class="field-value">{{ details.duration || legalCase.validity_term }}</span>
                </div>
                <div class="field-item">
                  <span class="field-label">Renewal Provisions:</span>
                  <span class="field-value">{{ details.renewal_terms }}</span>
                </div>
                <div class="field-item">
                  <span class="field-label">Termination for Convenience:</span>
                  <span class="field-value">{{ details.termination_convenience }}</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 2. RISKS & INCONSISTENCIES TAB -->
        <section v-if="activeTab === 'risks'" class="tab-pane fade-in">
          <div class="section-intro">
            <div class="intro-left">
              <h3>🚨 Highlighted Risks, Red Flags & Hidden Traps</h3>
              <p>Evaluated across unilateral indemnities, automatic renewals, harsh penalties, and liability loopholes.</p>
            </div>
            <button class="btn-ask-ai-inline" @click="handleAskAi('Summarize all high-risk clauses in this contract and recommend counter-proposals')">
              <Sparkles :size="15" />
              <span>Ask AI to Redline Risks</span>
            </button>
          </div>

          <div v-if="risks.length === 0" class="empty-tab-notice">
            <ShieldCheck :size="32" class="clean-icon" />
            <p>No high or medium-risk red flags detected in this agreement text.</p>
          </div>

          <div v-else class="risks-stack">
            <div 
              v-for="(r, idx) in risks" 
              :key="idx" 
              class="risk-card"
              :class="[r.risk_level.toLowerCase()]"
            >
              <div class="risk-card-top">
                <div class="risk-title-group">
                  <span class="risk-badge" :class="[r.risk_level.toLowerCase()]">{{ r.risk_level }} RISK</span>
                  <h4 class="risk-title">{{ r.title }}</h4>
                  <span v-if="r.clause_ref" class="clause-pill">{{ r.clause_ref }}</span>
                </div>

                <button class="btn-card-ask" @click="handleAskAi(`How can I negotiate or modify the risk in ${r.clause_ref} (${r.title})?`)" title="Ask AI about this risk">
                  <MessageSquare :size="14" />
                  <span>Ask AI</span>
                </button>
              </div>

              <div class="risk-body-grid">
                <div class="risk-issue-box">
                  <strong>The Issue:</strong>
                  <p>{{ r.issue }}</p>
                </div>
                <div class="risk-impact-box">
                  <strong>Practical Impact:</strong>
                  <p>{{ r.practical_impact }}</p>
                </div>
              </div>

              <div class="risk-remedy-box">
                <Sparkles :size="14" class="remedy-icon" />
                <span><strong>Recommended Redline Remedy:</strong> {{ r.recommended_remedy }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- 3. IMPORTANT CLAUSES TAB -->
        <section v-if="activeTab === 'clauses'" class="tab-pane fade-in">
          <div class="section-intro">
            <div class="intro-left">
              <h3>📑 Cataloged Contract Clauses</h3>
              <p>Key clauses categorized with verified quotes, plain explanations, and attention ratings.</p>
            </div>
            <button class="btn-ask-ai-inline" @click="handleAskAi('Explain all important clauses in plain language')">
              <Sparkles :size="15" />
              <span>Translate All Clauses to Plain English</span>
            </button>
          </div>

          <div class="clauses-grid">
            <div 
              v-for="(c, idx) in clauses" 
              :key="idx" 
              class="clause-card"
              :class="[c.severity || 'standard']"
            >
              <div class="clause-header">
                <div class="clause-name-group">
                  <h4>{{ c.name }}</h4>
                  <span class="clause-section-badge">{{ c.section }}</span>
                </div>
                <span class="severity-tag" :class="[c.severity]">{{ c.severity || 'standard' }}</span>
              </div>

              <blockquote v-if="c.verbatim_quote" class="clause-quote">
                "{{ c.verbatim_quote }}"
              </blockquote>

              <div class="clause-explanation">
                <strong>Plain Meaning:</strong>
                <p>{{ c.simple_explanation }}</p>
              </div>

              <div class="clause-footer">
                <button class="btn-clause-query" @click="handleAskAi(`Can you analyze the clause '${c.name}' in section '${c.section}' and explain its standard market terms?`)">
                  <MessageSquare :size="13" />
                  <span>Drill down with AI</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- 4. DEADLINES & TIMELINE TAB -->
        <section v-if="activeTab === 'deadlines'" class="tab-pane fade-in">
          <div class="section-intro">
            <div class="intro-left">
              <h3>⏳ Chronological Deadlines & Key Milestone Dates</h3>
              <p>Timeframes for notice windows, payment schedules, cure periods, and expiration.</p>
            </div>
          </div>

          <div class="timeline-stepper">
            <div 
              v-for="(d, idx) in deadlines" 
              :key="idx" 
              class="timeline-item"
              :class="[d.type]"
            >
              <div class="timeline-marker">
                <Clock :size="14" />
              </div>
              <div class="timeline-content-card">
                <div class="timeline-header">
                  <span class="timeline-timeframe">{{ d.timeframe }}</span>
                  <span class="timeline-type-pill" :class="[d.type]">{{ d.type }}</span>
                  <span v-if="d.clause_ref" class="timeline-ref">{{ d.clause_ref }}</span>
                </div>
                <h4 class="timeline-title">{{ d.title }}</h4>
                <p class="timeline-desc">{{ d.description }}</p>
              </div>
            </div>
          </div>
        </section>

        <!-- 5. OBLIGATIONS MATRIX TAB -->
        <section v-if="activeTab === 'obligations'" class="tab-pane fade-in">
          <div class="section-intro">
            <div class="intro-left">
              <h3>📋 Party Obligations & Affirmative Duties</h3>
              <p>Clear division of affirmative responsibilities, performance schedules, and breach penalties.</p>
            </div>
          </div>

          <div class="obligations-table-wrapper">
            <table class="obligations-table">
              <thead>
                <tr>
                  <th>Contracting Party</th>
                  <th>Affirmative Duty / Obligation</th>
                  <th>Timeline / Frequency</th>
                  <th>Consequence of Breach</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(o, idx) in obligations" :key="idx">
                  <td class="party-col">
                    <strong>{{ o.party }}</strong>
                  </td>
                  <td class="duty-col">{{ o.duty }}</td>
                  <td class="time-col">
                    <span class="time-chip">{{ o.timeframe }}</span>
                  </td>
                  <td class="breach-col">
                    <span class="breach-warning">{{ o.consequence_of_breach }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- 6. AGREEMENTS & POLICIES TAB -->
        <section v-if="activeTab === 'policies'" class="tab-pane fade-in">
          <div class="section-intro">
            <div class="intro-left">
              <h3>📜 Referenced Agreements, Compliance & Statutory Policies</h3>
              <p>Statutory standards, dispute resolution procedures, and corporate governance compliance.</p>
            </div>
          </div>

          <div class="policies-grid">
            <div v-for="(pol, idx) in policies" :key="idx" class="policy-card">
              <div class="policy-top">
                <Gavel :size="18" class="policy-icon" />
                <h4>{{ pol.name }}</h4>
              </div>
              <div class="policy-field">
                <span class="pol-label">Scope & Standard:</span>
                <p>{{ pol.scope }}</p>
              </div>
              <div class="policy-field">
                <span class="pol-label">Enforcement Mechanism:</span>
                <p>{{ pol.enforcement }}</p>
              </div>
            </div>
          </div>
        </section>

        <!-- 7. LAWYER PREP TAB -->
        <section v-if="activeTab === 'lawyer'" class="tab-pane fade-in">
          <div class="section-intro">
            <div class="intro-left">
              <h3>💼 Lawyer Consultation Questions & Briefing Sheet</h3>
              <p>Prioritized strategic questions to ask your attorney during formal legal consultation.</p>
            </div>
            <button class="btn-ask-ai-inline" @click="handleAskAi('Generate 5 more strategic questions for my lawyer consultation focusing on liability and enforceability')">
              <Sparkles :size="15" />
              <span>Generate More Questions</span>
            </button>
          </div>

          <div class="lawyer-card-list">
            <div v-for="(q, idx) in checklist" :key="idx" class="lawyer-q-card">
              <div class="q-num">Q{{ idx + 1 }}</div>
              <div class="q-content">
                <p class="q-text">{{ q }}</p>
              </div>
              <button class="btn-q-ask" @click="handleAskAi(`What is the legal implication of this question for my attorney: '${q}'?`)">
                <MessageSquare :size="14" />
                <span>Simulate Answer</span>
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<style scoped>
.dashboard-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  padding: 24px 32px;
  background: var(--bg-primary);
  color: var(--text-main);
}

/* Loading state */
.dash-loading-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin: auto;
  padding: 48px 32px;
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  max-width: 600px;
  text-align: center;
}

.spinner-ring {
  width: 50px;
  height: 50px;
  border: 3px solid rgba(229, 180, 88, 0.15);
  border-top-color: var(--accent-gold);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text-group h3 {
  font-size: 1.25rem;
  color: var(--text-main);
  margin-bottom: 8px;
}

.loading-text-group p {
  font-size: 0.9rem;
  color: var(--text-muted);
  line-height: 1.5;
  margin-bottom: 24px;
}

.loading-doc-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(229, 180, 88, 0.12);
  border: 1px solid rgba(229, 180, 88, 0.25);
  color: var(--accent-gold);
  padding: 6px 14px;
  border-radius: 9999px;
  font-size: 0.85rem;
  font-weight: 500;
  margin-bottom: 16px;
}

.loading-stepper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.step-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.78rem;
  font-weight: 500;
}

.step-badge.done {
  background: rgba(46, 213, 115, 0.12);
  border: 1px solid rgba(46, 213, 115, 0.25);
  color: var(--accent-success);
}

.step-badge.active {
  background: rgba(229, 180, 88, 0.15);
  border: 1px solid rgba(229, 180, 88, 0.35);
  color: var(--accent-gold);
}

.step-badge.pending {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
}

.step-divider {
  width: 20px;
  height: 2px;
  background: var(--border-subtle);
}

.step-divider.done {
  background: var(--accent-success);
}

.spin-icon {
  animation: spin 1.2s linear infinite;
}

.loading-actions {
  display: flex;
  justify-content: center;
  margin-top: 8px;
}

.btn-check-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--glass-border);
  color: var(--text-muted);
  padding: 7px 14px;
  border-radius: var(--radius-sm);
  font-size: 0.82rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-check-status:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-main);
  border-color: rgba(255, 255, 255, 0.2);
}

/* Empty Hero state */
.dash-empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: auto;
  max-width: 760px;
  width: 100%;
}

.empty-hero-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  padding: 48px 36px;
  box-shadow: var(--shadow-lg);
}

.empty-icon-halo {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(229, 180, 88, 0.1);
  border: 1px solid rgba(229, 180, 88, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
}

.hero-scale-icon {
  color: var(--accent-gold);
}

.empty-hero-card h2 {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 12px;
}

.hero-subtitle {
  font-size: 1rem;
  color: var(--text-muted);
  line-height: 1.6;
  max-width: 620px;
  margin-bottom: 32px;
}

.hero-actions-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  justify-content: center;
  margin-bottom: 32px;
}

.hidden-file-input {
  display: none;
}

.btn-primary-action, .btn-secondary-action {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 22px;
  font-size: 0.95rem;
  font-weight: 600;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary-action {
  background: linear-gradient(135deg, #e5b458 0%, #caa049 100%);
  color: #0b0f19;
  border: none;
  box-shadow: 0 4px 14px rgba(229, 180, 88, 0.35);
}

.btn-primary-action:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(229, 180, 88, 0.45);
}

.btn-secondary-action {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  color: var(--text-main);
}

.btn-secondary-action:hover {
  background: var(--bg-elevated);
  border-color: rgba(255, 255, 255, 0.2);
}

.samples-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding-top: 20px;
  border-top: 1px solid var(--border-subtle);
  width: 100%;
}

.sample-label {
  font-size: 0.85rem;
  color: var(--text-sub);
}

.samples-badges {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}

.sample-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  padding: 6px 14px;
  border-radius: var(--radius-full);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}

.sample-btn:hover {
  background: rgba(229, 180, 88, 0.12);
  border-color: var(--accent-gold);
  color: var(--accent-gold);
}

/* ACTIVE DASHBOARD STYLES */
.dash-active-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1280px;
  margin: 0 auto;
  width: 100%;
}

/* HERO HEADER */
.dash-hero-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  padding: 24px;
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(12px);
}

.doc-badge-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.type-pill {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  background: rgba(229, 180, 88, 0.15);
  border: 1px solid rgba(229, 180, 88, 0.3);
  color: var(--accent-gold);
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: var(--radius-full);
}

.category-pill, .status-pill {
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  font-size: 0.75rem;
  border-radius: var(--radius-full);
}

.doc-main-title {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 6px;
}

.doc-meta-sub {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.separator {
  color: var(--text-sub);
}

.header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.risk-gauge-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 10px 16px;
  min-width: 220px;
}

.gauge-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.78rem;
  margin-bottom: 6px;
  font-weight: 600;
}

.meter-bar {
  flex: 1;
  height: 8px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  overflow: hidden;
  margin-right: 8px;
}

.meter-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.gauge-meter-wrapper {
  display: flex;
  align-items: center;
}

.gauge-score {
  font-size: 0.85rem;
  font-weight: 700;
}

.hero-actions {
  display: flex;
  gap: 8px;
}

.btn-dash-action {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: var(--radius-sm);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  color: var(--text-main);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-dash-action:hover {
  background: var(--bg-elevated);
}

.btn-dash-action.highlight {
  border-color: rgba(229, 180, 88, 0.3);
  color: var(--accent-gold);
}

.btn-dash-action.highlight:hover {
  background: rgba(229, 180, 88, 0.15);
}

.check-icon {
  color: var(--accent-success);
}

/* VERDICT BANNER */
.verdict-banner-card {
  background: linear-gradient(135deg, rgba(22, 28, 45, 0.9) 0%, rgba(31, 41, 64, 0.8) 100%);
  border: 1px solid rgba(229, 180, 88, 0.25);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.verdict-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.verdict-icon-box {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  background: rgba(229, 180, 88, 0.2);
  color: var(--accent-gold);
  display: flex;
  align-items: center;
  justify-content: center;
}

.verdict-title-group h3 {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--accent-gold);
}

.verdict-sub {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.verdict-summary {
  font-size: 0.98rem;
  color: var(--text-main);
  line-height: 1.6;
  margin-bottom: 14px;
}

.verdict-footer-quote {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(0, 0, 0, 0.3);
  border-left: 3px solid var(--accent-gold);
  border-radius: 4px;
  font-size: 0.9rem;
  color: #f1f5f9;
}

.alert-icon {
  color: var(--accent-gold);
  flex-shrink: 0;
}

/* KPI GRID */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.kpi-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
}

.kpi-card:hover {
  transform: translateY(-2px);
  border-color: rgba(255, 255, 255, 0.18);
  box-shadow: var(--shadow-sm);
}

.kpi-icon-box {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
}

.kpi-icon-box.blue { background: rgba(56, 189, 248, 0.15); color: var(--accent-cyan); }
.kpi-icon-box.red { background: rgba(244, 63, 94, 0.15); color: var(--accent-danger); }
.kpi-icon-box.gold { background: rgba(229, 180, 88, 0.15); color: var(--accent-gold); }
.kpi-icon-box.green { background: rgba(16, 185, 129, 0.15); color: var(--accent-success); }

.kpi-content {
  display: flex;
  flex-direction: column;
}

.kpi-label {
  font-size: 0.75rem;
  color: var(--text-sub);
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.kpi-val {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-main);
  margin: 2px 0;
}

.kpi-sub {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* TABS NAVIGATION */
.dash-tabs-nav {
  display: flex;
  gap: 6px;
  border-bottom: 1px solid var(--border-subtle);
  overflow-x: auto;
  padding-bottom: 4px;
}

.dash-tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-muted);
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.dash-tab-btn:hover {
  color: var(--text-main);
}

.dash-tab-btn.active {
  color: var(--accent-gold);
  border-bottom-color: var(--accent-gold);
}

.tab-badge {
  padding: 2px 7px;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  background: rgba(229, 180, 88, 0.15);
  color: var(--accent-gold);
}

/* TAB BODY */
.dash-tab-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-intro {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 6px;
}

.section-intro h3 {
  font-size: 1.15rem;
  color: var(--text-main);
  margin-bottom: 4px;
}

.section-intro p {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.btn-ask-ai-inline {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  background: rgba(229, 180, 88, 0.12);
  border: 1px solid rgba(229, 180, 88, 0.3);
  color: var(--accent-gold);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-ask-ai-inline:hover {
  background: rgba(229, 180, 88, 0.22);
}

/* GRID 2 COL */
.grid-2-col {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.glass-card {
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--border-subtle);
}

.card-icon {
  color: var(--accent-gold);
}

.card-header h4 {
  font-size: 0.95rem;
  font-weight: 600;
}

.card-body {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  font-size: 0.88rem;
}

.field-label {
  color: var(--text-sub);
  flex-shrink: 0;
}

.field-value {
  color: var(--text-main);
  text-align: right;
  font-weight: 500;
}

.highlight-gold {
  color: var(--accent-gold);
  font-weight: 700;
}

.parties-list-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 6px;
}

.parties-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
}

.party-badge-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
}

.party-icon {
  color: var(--accent-cyan);
}

.party-info {
  display: flex;
  flex-direction: column;
}

.party-info strong {
  font-size: 0.85rem;
  color: var(--text-main);
}

.party-role {
  font-size: 0.75rem;
  color: var(--text-sub);
}

/* RISKS SECTION */
.risks-stack {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.risk-card {
  padding: 18px;
  background: var(--glass-surface);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--accent-warning);
  border-top: 1px solid var(--glass-border);
  border-right: 1px solid var(--glass-border);
  border-bottom: 1px solid var(--glass-border);
}

.risk-card.high {
  border-left-color: var(--accent-danger);
}

.risk-card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.risk-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.risk-badge {
  padding: 3px 8px;
  border-radius: var(--radius-full);
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
}

.risk-badge.high {
  background: rgba(244, 63, 94, 0.2);
  color: var(--accent-danger);
}

.risk-badge.medium {
  background: rgba(245, 158, 11, 0.2);
  color: var(--accent-warning);
}

.risk-title {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text-main);
}

.clause-pill {
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  color: var(--text-muted);
}

.btn-card-ask {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-card-ask:hover {
  background: rgba(229, 180, 88, 0.15);
  border-color: var(--accent-gold);
  color: var(--accent-gold);
}

.risk-body-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 12px;
  font-size: 0.88rem;
}

.risk-issue-box p, .risk-impact-box p {
  color: var(--text-muted);
  margin-top: 4px;
  line-height: 1.5;
}

.risk-remedy-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(16, 185, 129, 0.08);
  border-radius: var(--radius-sm);
  border: 1px solid rgba(16, 185, 129, 0.2);
  font-size: 0.85rem;
  color: #6ee7b7;
}

.remedy-icon {
  flex-shrink: 0;
  color: var(--accent-success);
}

/* CLAUSES GRID */
.clauses-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 16px;
}

.clause-card {
  padding: 18px;
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.clause-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.clause-name-group h4 {
  font-size: 1rem;
  color: var(--text-main);
  margin-bottom: 3px;
}

.clause-section-badge {
  font-size: 0.75rem;
  color: var(--text-sub);
}

.severity-tag {
  font-size: 0.72rem;
  text-transform: uppercase;
  padding: 2px 7px;
  border-radius: var(--radius-full);
  font-weight: 600;
}

.severity-tag.critical { background: rgba(244, 63, 94, 0.2); color: var(--accent-danger); }
.severity-tag.attention { background: rgba(245, 158, 11, 0.2); color: var(--accent-warning); }
.severity-tag.standard { background: rgba(56, 189, 248, 0.2); color: var(--accent-cyan); }
.severity-tag.favorable { background: rgba(16, 185, 129, 0.2); color: var(--accent-success); }

.clause-quote {
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.25);
  border-left: 2px solid var(--accent-cyan);
  font-size: 0.82rem;
  color: var(--text-muted);
  font-style: italic;
  line-height: 1.4;
  border-radius: 2px;
}

.clause-explanation strong {
  font-size: 0.8rem;
  color: var(--text-sub);
}

.clause-explanation p {
  font-size: 0.88rem;
  color: var(--text-main);
  line-height: 1.5;
  margin-top: 2px;
}

.clause-footer {
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
}

.btn-clause-query {
  display: flex;
  align-items: center;
  gap: 5px;
  background: transparent;
  border: none;
  color: var(--accent-cyan);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}

.btn-clause-query:hover {
  text-decoration: underline;
}

/* TIMELINE */
.timeline-stepper {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
  padding-left: 28px;
}

.timeline-stepper::before {
  content: '';
  position: absolute;
  left: 9px;
  top: 12px;
  bottom: 12px;
  width: 2px;
  background: var(--border-subtle);
}

.timeline-item {
  position: relative;
}

.timeline-marker {
  position: absolute;
  left: -28px;
  top: 12px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--bg-secondary);
  border: 2px solid var(--accent-gold);
  color: var(--accent-gold);
  display: flex;
  align-items: center;
  justify-content: center;
}

.timeline-item.critical .timeline-marker {
  border-color: var(--accent-danger);
  color: var(--accent-danger);
}

.timeline-content-card {
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  padding: 14px 18px;
}

.timeline-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.timeline-timeframe {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--accent-gold);
}

.timeline-type-pill {
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: 0.72rem;
  text-transform: uppercase;
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-muted);
}

.timeline-ref {
  font-size: 0.75rem;
  color: var(--text-sub);
}

.timeline-title {
  font-size: 1rem;
  color: var(--text-main);
  margin-bottom: 4px;
}

.timeline-desc {
  font-size: 0.85rem;
  color: var(--text-muted);
  line-height: 1.5;
}

/* OBLIGATIONS TABLE */
.obligations-table-wrapper {
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  overflow-x: auto;
}

.obligations-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.88rem;
}

.obligations-table th {
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-sub);
  font-size: 0.78rem;
  text-transform: uppercase;
  font-weight: 600;
  border-bottom: 1px solid var(--border-subtle);
}

.obligations-table td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-subtle);
  vertical-align: top;
}

.party-col {
  width: 20%;
  color: var(--accent-gold);
}

.duty-col {
  width: 45%;
  color: var(--text-main);
  line-height: 1.5;
}

.time-col {
  width: 15%;
}

.time-chip {
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 4px;
  font-size: 0.78rem;
  color: var(--text-muted);
}

.breach-col {
  width: 20%;
}

.breach-warning {
  color: #fca5a5;
  font-size: 0.82rem;
}

/* POLICIES GRID */
.policies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}

.policy-card {
  padding: 18px;
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
}

.policy-top {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.policy-icon {
  color: var(--accent-purple);
}

.policy-top h4 {
  font-size: 1rem;
  color: var(--text-main);
}

.policy-field {
  margin-bottom: 10px;
}

.pol-label {
  font-size: 0.75rem;
  color: var(--text-sub);
  display: block;
  margin-bottom: 2px;
}

.policy-field p {
  font-size: 0.85rem;
  color: var(--text-muted);
  line-height: 1.4;
}

/* LAWYER PREP */
.lawyer-card-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.lawyer-q-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  transition: all 0.2s;
}

.lawyer-q-card:hover {
  border-color: rgba(229, 180, 88, 0.35);
}

.q-num {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--accent-gold);
  width: 38px;
  height: 38px;
  background: rgba(229, 180, 88, 0.12);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.q-content {
  flex: 1;
}

.q-text {
  font-size: 0.95rem;
  color: var(--text-main);
  line-height: 1.5;
}

.btn-q-ask {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 0.8rem;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.btn-q-ask:hover {
  background: rgba(229, 180, 88, 0.15);
  border-color: var(--accent-gold);
  color: var(--accent-gold);
}
</style>
