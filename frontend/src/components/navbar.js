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
          <div class="brand-icon" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="3" y1="21" x2="21" y2="21"></line>
              <line x1="3" y1="10" x2="21" y2="10"></line>
              <polyline points="5 6 12 3 19 6"></polyline>
              <line x1="4" y1="10" x2="4" y2="21"></line>
              <line x1="20" y1="10" x2="20" y2="21"></line>
              <line x1="8" y1="14" x2="8" y2="17"></line>
              <line x1="12" y1="14" x2="12" y2="17"></line>
              <line x1="16" y1="14" x2="16" y2="17"></line>
            </svg>
          </div>
          <div class="brand-info">
            <h1>Plataforma de Precalificación Crediticia</h1>
            <span>Metodología CRISP-ML(Q) &bull; Scoring Automatizado de Riesgo Bancario</span>
          </div>
        </div>

        <nav class="nav-tabs" aria-label="Navegación principal">
          <button type="button" class="nav-tab-btn active" data-tab="predictor">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
            Scoring Crediticio
          </button>
          <button type="button" class="nav-tab-btn" data-tab="metrics">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
            Métricas de Riesgo
          </button>
          <button type="button" class="nav-tab-btn" data-tab="history">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>
            Auditoría Bancaria
          </button>
          <button type="button" class="nav-tab-btn" data-tab="retrain">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
            Actualización MLOps
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
