<template>
  <div class="particle-backdrop" :class="{ 'particle-backdrop--quiet': quiet }" aria-hidden="true">
    <canvas ref="canvasRef" class="particle-canvas"></canvas>
    <div class="mine-haze"></div>
    <div class="mine-grid"></div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';

withDefaults(defineProps<{ quiet?: boolean }>(), {
  quiet: false
});

type Particle = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  alpha: number;
};

const canvasRef = ref<HTMLCanvasElement>();
let ctx: CanvasRenderingContext2D | null = null;
let particles: Particle[] = [];
let animationFrame = 0;
let mediaQuery: MediaQueryList | null = null;
let reducedMotion = false;

function resizeCanvas() {
  const canvas = canvasRef.value;
  if (!canvas) return;

  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const { width, height } = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.floor(width * dpr));
  canvas.height = Math.max(1, Math.floor(height * dpr));
  ctx = canvas.getContext('2d');
  ctx?.setTransform(dpr, 0, 0, dpr, 0, 0);
  seedParticles(width, height);
}

function seedParticles(width: number, height: number) {
  const count = reducedMotion ? 28 : Math.min(96, Math.max(44, Math.floor((width * height) / 18000)));
  particles = Array.from({ length: count }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    vx: (Math.random() - 0.5) * 0.18,
    vy: -0.08 - Math.random() * 0.18,
    size: 0.8 + Math.random() * 1.8,
    alpha: 0.22 + Math.random() * 0.55
  }));
}

function drawFrame() {
  const canvas = canvasRef.value;
  if (!canvas || !ctx) return;

  const { width, height } = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, width, height);

  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, 'rgba(28, 199, 255, 0.08)');
  gradient.addColorStop(0.48, 'rgba(57, 231, 159, 0.025)');
  gradient.addColorStop(1, 'rgba(47, 124, 255, 0.06)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  ctx.lineWidth = 1;
  for (let i = 0; i < particles.length; i += 1) {
    const p = particles[i];

    if (!reducedMotion) {
      p.x += p.vx;
      p.y += p.vy;
      if (p.y < -12) p.y = height + 12;
      if (p.x < -12) p.x = width + 12;
      if (p.x > width + 12) p.x = -12;
    }

    ctx.beginPath();
    ctx.fillStyle = `rgba(100, 221, 255, ${p.alpha})`;
    ctx.shadowColor = 'rgba(28, 199, 255, 0.55)';
    ctx.shadowBlur = 8;
    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
    ctx.fill();

    for (let j = i + 1; j < particles.length; j += 1) {
      const q = particles[j];
      const dx = p.x - q.x;
      const dy = p.y - q.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 112) {
        ctx.beginPath();
        ctx.strokeStyle = `rgba(67, 203, 255, ${(1 - dist / 112) * 0.13})`;
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(q.x, q.y);
        ctx.stroke();
      }
    }
  }

  ctx.shadowBlur = 0;
  animationFrame = window.requestAnimationFrame(drawFrame);
}

onMounted(() => {
  mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  reducedMotion = mediaQuery.matches;
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);
  mediaQuery.addEventListener('change', resizeCanvas);
  drawFrame();
});

onUnmounted(() => {
  window.removeEventListener('resize', resizeCanvas);
  mediaQuery?.removeEventListener('change', resizeCanvas);
  window.cancelAnimationFrame(animationFrame);
});
</script>

<style scoped>
.particle-backdrop {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  background:
    linear-gradient(180deg, rgba(2, 8, 18, 0.26), rgba(2, 8, 18, 0.82)),
    linear-gradient(115deg, #06111c 0%, #081a29 45%, #03101d 100%);
}

.particle-canvas,
.mine-haze,
.mine-grid {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.mine-haze {
  background:
    linear-gradient(115deg, transparent 0 12%, rgba(28, 199, 255, 0.05) 24%, transparent 42%),
    linear-gradient(28deg, transparent 0 40%, rgba(57, 231, 159, 0.04) 58%, transparent 78%);
  opacity: 0.9;
}

.mine-grid {
  background-image:
    linear-gradient(rgba(84, 197, 255, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(84, 197, 255, 0.08) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: linear-gradient(to bottom, transparent 0%, black 42%, black 100%);
  opacity: 0.34;
  transform: perspective(460px) rotateX(56deg) translateY(34%);
  transform-origin: bottom center;
}

.particle-backdrop--quiet .mine-grid {
  opacity: 0.18;
}

@media (prefers-reduced-motion: reduce) {
  .particle-canvas {
    opacity: 0.55;
  }
}
</style>
