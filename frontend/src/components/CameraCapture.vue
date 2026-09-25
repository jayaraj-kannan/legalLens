<script setup>
import { ref } from 'vue';
import { Camera, X, Check, RefreshCw } from 'lucide-vue-next';

const emit = defineEmits(['capture', 'close']);

const videoRef = ref(null);
const stream = ref(null);
const capturedImage = ref(null);
const cameraActive = ref(false);
const errorMsg = ref('');

async function startCamera() {
  try {
    errorMsg.value = '';
    const mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } }
    });
    stream.value = mediaStream;
    if (videoRef.value) {
      videoRef.value.srcObject = mediaStream;
    }
    cameraActive.value = true;
  } catch (err) {
    errorMsg.value = 'Could not access camera. Please check browser permissions.';
  }
}

function takePhoto() {
  if (!videoRef.value) return;
  const canvas = document.createElement('canvas');
  canvas.width = videoRef.value.videoWidth || 1280;
  canvas.height = videoRef.value.videoHeight || 720;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(videoRef.value, 0, 0, canvas.width, canvas.height);
  
  canvas.toBlob((blob) => {
    capturedImage.value = {
      blob,
      previewUrl: URL.createObjectURL(blob),
      filename: `contract_snap_${Date.now()}.jpg`
    };
  }, 'image/jpeg', 0.92);
}

function retake() {
  capturedImage.value = null;
}

function confirmUpload() {
  if (capturedImage.value) {
    const file = new File([capturedImage.value.blob], capturedImage.value.filename, { type: 'image/jpeg' });
    emit('capture', file);
    close();
  }
}

function close() {
  if (stream.value) {
    stream.value.getTracks().forEach(t => t.stop());
  }
  emit('close');
}

// Auto start when mounted
import { onMounted, onUnmounted } from 'vue';
onMounted(() => startCamera());
onUnmounted(() => {
  if (stream.value) stream.value.getTracks().forEach(t => t.stop());
});
</script>

<template>
  <div class="camera-backdrop" @click.self="close">
    <div class="camera-modal fade-in">
      <div class="modal-header">
        <div class="title-wrap">
          <Camera :size="20" class="header-icon" />
          <h3>Snap Contract / Agreement Page</h3>
        </div>
        <button class="btn-close" @click="close">
          <X :size="18" />
        </button>
      </div>

      <div class="viewport-area">
        <!-- Live Video Stream -->
        <video 
          v-show="!capturedImage" 
          ref="videoRef" 
          autoplay 
          playsinline 
          class="video-feed"
        ></video>

        <!-- Document Framing Guide Lines -->
        <div v-if="!capturedImage && cameraActive" class="doc-guide">
          <div class="guide-corners"></div>
          <span class="guide-text">Align document within the legal scan frame</span>
        </div>

        <!-- Captured Image Review -->
        <img 
          v-if="capturedImage" 
          :src="capturedImage.previewUrl" 
          alt="Document Snapshot" 
          class="captured-preview" 
        />

        <div v-if="errorMsg" class="camera-error">
          <p>{{ errorMsg }}</p>
        </div>
      </div>

      <div class="modal-footer">
        <div v-if="!capturedImage" class="camera-controls">
          <button class="btn-snap" @click="takePhoto" :disabled="!cameraActive">
            <div class="snap-inner"></div>
          </button>
        </div>

        <div v-else class="review-controls">
          <button class="btn-retake" @click="retake">
            <RefreshCw :size="16" />
            <span>Retake</span>
          </button>
          <button class="btn-confirm" @click="confirmUpload">
            <Check :size="16" />
            <span>Analyze with Legal Agents</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.camera-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.camera-modal {
  width: 100%;
  max-width: 680px;
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--glass-border);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
}

.title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon {
  color: var(--accent-gold);
}

.title-wrap h3 {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
}

.btn-close {
  background: none;
  border: none;
  color: var(--text-sub);
  cursor: pointer;
  padding: 6px;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.btn-close:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}

.viewport-area {
  position: relative;
  width: 100%;
  height: 440px;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.video-feed,
.captured-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.doc-guide {
  position: absolute;
  inset: 30px;
  border: 2px dashed rgba(229, 180, 88, 0.45);
  border-radius: 12px;
  pointer-events: none;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: 16px;
}

.guide-text {
  font-size: 12px;
  color: var(--accent-gold);
  background: rgba(10, 13, 20, 0.85);
  padding: 4px 12px;
  border-radius: var(--radius-full);
}

.camera-error {
  position: absolute;
  padding: 16px 24px;
  background: rgba(244, 63, 94, 0.15);
  border: 1px solid var(--accent-danger);
  border-radius: var(--radius-md);
  color: #fff;
  font-size: 13px;
}

.modal-footer {
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border-top: 1px solid var(--border-subtle);
}

.btn-snap {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  border: 3px solid #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.15s;
}

.btn-snap:hover {
  transform: scale(1.05);
}

.snap-inner {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--accent-gold);
}

.review-controls {
  display: flex;
  gap: 16px;
}

.btn-retake {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--glass-border);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}

.btn-confirm {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--accent-gold) 0%, #ca8a04 100%);
  border: none;
  color: #0a0d14;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: var(--shadow-glow);
}
</style>
