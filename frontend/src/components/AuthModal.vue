<script setup>
import { ref } from 'vue';
import { Scale, Lock, Mail, User, ArrowRight, ShieldCheck } from 'lucide-vue-next';

const emit = defineEmits(['auth-success']);

const isSignUp = ref(false);
const email = ref('advocate.sharma@legallens.ai');
const password = ref('••••••••');
const name = ref('Jayaraj Sharma');

function handleEmailSubmit() {
  const user = {
    id: 'user_' + Math.random().toString(36).substring(2, 8),
    name: name.value || 'Legal Professional',
    email: email.value || 'advocate@legallens.ai',
    avatar: (name.value || 'J').charAt(0).toUpperCase()
  };
  emit('auth-success', user);
}

function handleGoogleSignIn() {
  const user = {
    id: 'user_google_7849',
    name: 'Jayaraj Kannan',
    email: 'jrajfx@gmail.com',
    avatar: 'J'
  };
  emit('auth-success', user);
}
</script>

<template>
  <div class="auth-container">
    <!-- Left Decorative Column with Ambient Legal Branding -->
    <div class="auth-hero">
      <div class="hero-badge">
        <Scale class="hero-badge-icon" :size="18" />
        <span>Autonomous Legal Multi-Agent System</span>
      </div>
      <h1 class="hero-title">
        LegalLens<span class="gold-dot">.</span>
      </h1>
      <p class="hero-subtitle">
        Intelligent contract parsing, clause risk detection, multi-document comparison, and grounded Q&A with verifiable evidence citations.
      </p>

      <div class="hero-features">
        <div class="feature-card">
          <ShieldCheck class="feat-icon" :size="20" />
          <div>
            <h4>10 Specialized AI Agents</h4>
            <p>From Risk & Attention to Timeline & Indian Multilingual translation</p>
          </div>
        </div>
        <div class="feature-card">
          <Scale class="feat-icon" :size="20" />
          <div>
            <h4>Educational & Safe</h4>
            <p>Built-in lawyer consultation prep & regulatory guardrails</p>
          </div>
        </div>
      </div>

      <div class="hero-footer">
        Powered by Google ADK & Gemini 2.5 Flash on Vertex AI
      </div>
    </div>

    <!-- Right Column: Login / Signup Box as sketched -->
    <div class="auth-form-wrapper">
      <div class="auth-card fade-in">
        <div class="card-header">
          <div class="brand-avatar">J</div>
          <h2 class="card-title">{{ isSignUp ? 'Create your Account' : 'Welcome to LegalLens' }}</h2>
          <p class="card-subtitle">
            {{ isSignUp ? 'Sign up to upload & analyze legal agreements' : 'Sign in to access your legal consultations and documents' }}
          </p>
        </div>

        <!-- Google Sign In Button (matching sketch) -->
        <button class="btn-google" @click="handleGoogleSignIn" type="button">
          <svg class="google-svg" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
          </svg>
          <span>Continue with Google</span>
        </button>

        <div class="divider">
          <span>or sign in with email</span>
        </div>

        <form @submit.prevent="handleEmailSubmit" class="form-body">
          <div v-if="isSignUp" class="input-group">
            <label>Full Name</label>
            <div class="input-field">
              <User :size="18" class="field-icon" />
              <input v-model="name" type="text" placeholder="Advocate Jayaraj" required />
            </div>
          </div>

          <div class="input-group">
            <label>Email Address</label>
            <div class="input-field">
              <Mail :size="18" class="field-icon" />
              <input v-model="email" type="email" placeholder="name@lawfirm.com" required />
            </div>
          </div>

          <div class="input-group">
            <label>Password</label>
            <div class="input-field">
              <Lock :size="18" class="field-icon" />
              <input v-model="password" type="password" placeholder="••••••••" required />
            </div>
          </div>

          <!-- Action button matching sketch ("Sign up" / "Sign in") -->
          <button class="btn-primary" type="submit">
            <span>{{ isSignUp ? 'Sign Up' : 'Sign In' }}</span>
            <ArrowRight :size="18" />
          </button>
        </form>

        <div class="card-footer">
          <button class="link-toggle" @click="isSignUp = !isSignUp">
            {{ isSignUp ? 'Already have an account? Sign in' : "Don't have an account? Sign up" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-container {
  display: flex;
  width: 100vw;
  height: 100vh;
  background: radial-gradient(circle at 15% 20%, rgba(229, 180, 88, 0.08) 0%, transparent 45%),
              radial-gradient(circle at 85% 80%, rgba(56, 189, 248, 0.06) 0%, transparent 45%),
              var(--bg-primary);
}

.auth-hero {
  flex: 1.1;
  padding: 80px 70px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-right: 1px solid var(--border-subtle);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.015) 0%, transparent 100%);
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  background: rgba(229, 180, 88, 0.12);
  border: 1px solid rgba(229, 180, 88, 0.3);
  color: var(--accent-gold);
  font-size: 13px;
  font-weight: 600;
  width: fit-content;
  margin-bottom: 24px;
}

.hero-title {
  font-size: 52px;
  font-weight: 800;
  letter-spacing: -1.5px;
  color: #fff;
  line-height: 1.1;
  margin-bottom: 16px;
}

.gold-dot {
  color: var(--accent-gold);
}

.hero-subtitle {
  font-size: 18px;
  color: var(--text-muted);
  line-height: 1.6;
  max-width: 540px;
  margin-bottom: 40px;
}

.hero-features {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-bottom: 50px;
}

.feature-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px 20px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--glass-border);
  max-width: 500px;
}

.feat-icon {
  color: var(--accent-gold);
  margin-top: 2px;
}

.feature-card h4 {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 4px;
}

.feature-card p {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.4;
}

.hero-footer {
  font-size: 13px;
  color: var(--text-sub);
  font-family: var(--font-mono);
}

/* Right Form Wrapper */
.auth-form-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.auth-card {
  width: 100%;
  max-width: 440px;
  padding: 40px;
  border-radius: var(--radius-lg);
  background: var(--glass-surface);
  backdrop-filter: blur(20px);
  border: 1px solid var(--glass-border);
  box-shadow: var(--shadow-lg);
}

.card-header {
  text-align: center;
  margin-bottom: 28px;
}

.brand-avatar {
  width: 48px;
  height: 48px;
  margin: 0 auto 16px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent-gold) 0%, #b8860b 100%);
  color: #0a0d14;
  font-size: 22px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(229, 180, 88, 0.35);
}

.card-title {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 8px;
}

.card-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.5;
}

.btn-google {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 13px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--glass-border);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-google:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
  transform: translateY(-1px);
}

.google-svg {
  width: 20px;
  height: 20px;
}

.divider {
  display: flex;
  align-items: center;
  text-align: center;
  margin: 24px 0;
  color: var(--text-sub);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid var(--glass-border);
}

.divider span {
  padding: 0 12px;
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.input-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.input-field {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: rgba(10, 13, 20, 0.6);
  border: 1px solid var(--glass-border);
  transition: border-color 0.2s;
}

.input-field:focus-within {
  border-color: var(--accent-gold);
  box-shadow: 0 0 0 1px var(--accent-gold-glow);
}

.field-icon {
  color: var(--text-sub);
}

.input-field input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #fff;
  font-size: 14px;
  font-family: inherit;
}

.input-field input::placeholder {
  color: var(--text-sub);
}

.btn-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 14px;
  margin-top: 8px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--accent-gold) 0%, #ca8a04 100%);
  border: none;
  color: #0a0d14;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: var(--shadow-glow);
}

.btn-primary:hover {
  transform: translateY(-1px);
  filter: brightness(1.08);
}

.card-footer {
  margin-top: 24px;
  text-align: center;
}

.link-toggle {
  background: none;
  border: none;
  color: var(--accent-cyan);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 4px;
}

.link-toggle:hover {
  color: #fff;
}
</style>
