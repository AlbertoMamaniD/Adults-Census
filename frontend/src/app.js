/**
 * APP.JS — Punto de Entrada Principal de la Aplicación Web
 * Inicializa componentes, enrutamiento por pestañas, modales y notificaciones.
 */

import { renderNavbar, updateAuthBtnState } from './components/navbar.js';
import { renderPredictor } from './components/predictor.js';
import { renderMetricsDashboard } from './components/metricsDashboard.js';
import { renderHistoryTable, loadHistory } from './components/historyTable.js';
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
  
  const iconSvg = type === 'success' 
    ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>` 
    : type === 'error' 
      ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>` 
      : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;

  toast.innerHTML = `
    <span style="display: inline-flex; align-items: center; margin-right: 0.5rem;">${iconSvg}</span>
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

  let currentActiveTab = 'predictor';

  stateService.subscribe((state) => {
    // Si la pestaña activa no ha cambiado (ej. polling periódico de salud de fondo), ignorar para evitar parpadeos
    if (state.activeTab === currentActiveTab) {
      return;
    }
    currentActiveTab = state.activeTab;

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

    // Refrescos silenciosos de datos en segundo plano al entrar a la pestaña sin parpadeo de interfaz
    if (state.activeTab === 'history') {
      const histContainer = document.getElementById('tab-history');
      if (histContainer) {
        loadHistory(histContainer, 15, 0, true);
      }
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
