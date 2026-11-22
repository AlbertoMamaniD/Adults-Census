/**
 * NAVBAR.JS — Barra de Navegación Institucional y Estado de Conectividad
 */

import { apiService } from '../services/apiService.js';
import { stateService } from '../services/stateService.js';

export function renderNavbar(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = `
    <header class="site-header">
      <div class="header-content">
        <div class="brand-wrapper">
          <div class="brand-icon" aria-hidden="true">IA</div>
          <div class="brand-info">
            <h1>Precalificación Crediticia</h1>
            <span>Metodología CRISP-ML(Q) — UCB San Pablo</span>
          </div>
        </div>

        <nav class="nav-tabs" aria-label="Navegación principal">
          <button type="button" class="nav-tab-btn active" data-tab="predictor">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
            Inferencia
          </button>
          <button type="button" class="nav-tab-btn" data-tab="metrics">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
            Métricas MLOps
          </button>
          <button type="button" class="nav-tab-btn" data-tab="history">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>
            Auditoría
          </button>
          <button type="button" class="nav-tab-btn" data-tab="retrain">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
            Reentrenamiento
          </button>
        </nav>

        <div class="system-status" id="system-status-pill">
          <span class="status-dot" id="status-dot"></span>
          <span id="status-text">Conectando...</span>
          <button type="button" id="auth-btn" class="btn btn-secondary btn-sm" style="margin-left: 0.5rem; padding: 0.2rem 0.5rem; font-size: 0.75rem;">
            Login
          </button>
        </div>
      </div>
    </header>
  `;

  // Asignar eventos de tabs
  const tabButtons = container.querySelectorAll('.nav-tab-btn');
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const targetTab = btn.getAttribute('data-tab');
      stateService.setActiveTab(targetTab);
    });
  });

  // Evento botón login
  const authBtn = container.querySelector('#auth-btn');
  authBtn.addEventListener('click', () => {
    if (apiService.isAuthenticated()) {
      if (confirm('¿Desea cerrar la sesión actual de analista?')) {
        apiService.logout();
        updateAuthBtnState();
        window.showToast?.('Sesión cerrada correctamente.', 'success');
      }
    } else {
      window.openLoginModal?.();
    }
  });

  // Comprobar salud periódicamente
  checkHealthStatus();
  const healthInterval = setInterval(checkHealthStatus, 15000);
  if (healthInterval && typeof healthInterval.unref === 'function') {
    healthInterval.unref();
  }
}

export function updateAuthBtnState() {
  const authBtn = document.getElementById('auth-btn');
  if (!authBtn) return;
  if (apiService.isAuthenticated()) {
    authBtn.textContent = 'Salir';
    authBtn.classList.remove('btn-secondary');
    authBtn.classList.add('btn-primary');
  } else {
    authBtn.textContent = 'Login';
    authBtn.classList.add('btn-secondary');
    authBtn.classList.remove('btn-primary');
  }
}

async function checkHealthStatus() {
  const dot = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  if (!dot || !text) return;

  try {
    const health = await apiService.checkHealth();
    dot.className = 'status-dot online';
    text.textContent = `Online (${health.active_model_version || 'v_latest'})`;
    stateService.setSystemStatus(true, health.active_model_version, health.threshold);
  } catch (err) {
    dot.className = 'status-dot';
    text.textContent = 'Backend Offline';
    stateService.setSystemStatus(false);
  }
}
