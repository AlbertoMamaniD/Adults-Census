/**
 * APP.JS — Punto de Entrada Principal de la Aplicación Web
 * Inicializa componentes, enrutamiento por pestañas, modales y notificaciones.
 */

import { renderNavbar, updateAuthBtnState } from './components/navbar.js';
import { renderPredictor } from './components/predictor.js';
import { renderMetricsDashboard } from './components/metricsDashboard.js';
import { renderHistoryTable } from './components/historyTable.js';
import { renderRetrainCenter } from './components/retrainCenter.js';
import { stateService } from './services/stateService.js';
import { apiService } from './services/apiService.js';

// ==========================================================================
// 1. SISTEMA GLOBAL DE NOTIFICACIONES TOAST
// ==========================================================================
window.showToast = function(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type === 'success' ? 'toast-success' : type === 'error' ? 'toast-error' : ''}`;
  
  const icon = type === 'success' 
    ? '✓' 
    : type === 'error' 
      ? '✕' 
      : 'ℹ';

  toast.innerHTML = `
    <span style="font-weight: bold;">${icon}</span>
    <span>${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(1rem)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
};

// ==========================================================================
// 2. CONTROLADOR DEL MODAL DE AUTENTICACIÓN
// ==========================================================================
window.openLoginModal = function() {
  const modal = document.getElementById('login-modal');
  if (!modal) return;
  modal.classList.remove('hidden');
  const userInput = document.getElementById('login-username');
  if (userInput) userInput.focus();
};

window.closeLoginModal = function() {
  const modal = document.getElementById('login-modal');
  if (!modal) return;
  modal.classList.add('hidden');
  const errorMsg = document.getElementById('login-error-msg');
  if (errorMsg) errorMsg.classList.add('hidden');
};

function setupLoginModal() {
  const modal = document.getElementById('login-modal');
  const btnClose = document.getElementById('btn-close-modal');
  const btnCancel = document.getElementById('btn-cancel-modal');
  const loginForm = document.getElementById('login-form');

  btnClose?.addEventListener('click', window.closeLoginModal);
  btnCancel?.addEventListener('click', window.closeLoginModal);

  modal?.addEventListener('click', (e) => {
    if (e.target === modal) {
      window.closeLoginModal();
    }
  });

  loginForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('login-username')?.value?.trim();
    const password = document.getElementById('login-password')?.value;
    const submitBtn = document.getElementById('login-submit-btn');
    const errorMsg = document.getElementById('login-error-msg');

    if (!username || !password) return;

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner"></span> Verificando...';
    }
    if (errorMsg) errorMsg.classList.add('hidden');

    try {
      await apiService.login(username, password);
      updateAuthBtnState();
      window.showToast('Autenticación exitosa. Privilegios concedidos.', 'success');
      window.closeLoginModal();

      // Refrescar vistas que requieren permisos
      if (stateService.activeTab === 'history') {
        renderHistoryTable('tab-history');
      } else if (stateService.activeTab === 'retrain') {
        renderRetrainCenter('tab-retrain');
      }
    } catch (err) {
      if (errorMsg) {
        errorMsg.textContent = err.message || 'Credenciales inválidas. Verifique usuario y contraseña.';
        errorMsg.classList.remove('hidden');
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Iniciar Sesión';
      }
    }
  });
}

// ==========================================================================
// 3. ENRUTAMIENTO Y GESTIÓN DE VISTAS (TABS)
// ==========================================================================
function setupTabRouting() {
  const tabPanes = {
    predictor: document.getElementById('tab-predictor'),
    metrics: document.getElementById('tab-metrics'),
    history: document.getElementById('tab-history'),
    retrain: document.getElementById('tab-retrain'),
  };

  stateService.subscribe((state) => {
    Object.keys(tabPanes).forEach((tabKey) => {
      const pane = tabPanes[tabKey];
      if (!pane) return;
      if (tabKey === state.activeTab) {
        pane.classList.remove('hidden');
        pane.classList.add('active');
      } else {
        pane.classList.add('hidden');
        pane.classList.remove('active');
      }
    });

    // Refrescos condicionales al entrar a pestaña
    if (state.activeTab === 'history') {
      renderHistoryTable('tab-history');
    }
  });
}

// ==========================================================================
// 4. INICIALIZACIÓN GLOBAL DE LA APLICACIÓN
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  // Renderizar componentes en sus respectivos contenedores
  renderNavbar('navbar-root');
  renderPredictor('tab-predictor');
  renderMetricsDashboard('tab-metrics');
  renderHistoryTable('tab-history');
  renderRetrainCenter('tab-retrain');

  // Inicializar listeners y enrutador
  setupLoginModal();
  setupTabRouting();
  updateAuthBtnState();

  console.log('[SISTEMA] Aplicación Web de Precalificación Crediticia inicializada correctamente.');
});
