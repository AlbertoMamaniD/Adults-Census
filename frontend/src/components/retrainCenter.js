/**
 * RETRAINCENTER.JS — Módulo 4: Carga de CSV y Reentrenamiento MLOps con WebSocket
 */

import { apiService } from '../services/apiService.js';

export function renderRetrainCenter(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = `
    <div style="display: grid; grid-template-columns: 1fr; gap: 2rem;">
      <section class="card">
        <div class="card-header">
          <div>
            <h2>Centro de Reentrenamiento y Ciclo MLOps</h2>
            <p class="text-muted" style="font-size: var(--font-size-sm); margin: 0;">
              Ingesta de lotes censales validados, ajuste del pipeline HistGradientBoosting y promoción con Zero-Downtime.
            </p>
          </div>
        </div>

        <!-- Alerta de Autenticación si no hay token -->
        <div id="retrain-auth-alert" class="hidden" style="background-color: var(--color-warning-bg); border: 1px solid var(--color-warning-border); padding: 1rem; border-radius: var(--radius-md); margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.75rem; color: var(--color-warning-hover); font-size: var(--font-size-sm);">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            <span><strong>Modo Restringido:</strong> Se requiere autenticación JWT para subir nuevos datasets o disparar reentrenamientos.</span>
          </div>
          <button type="button" id="btn-login-retrain" class="btn btn-secondary btn-sm">Iniciar Sesión</button>
        </div>

        <div style="display: grid; grid-template-columns: 1fr; gap: 1.5rem;">
          <!-- 1. Zona Drag & Drop para Cargar CSV -->
          <div>
            <label class="form-label">1. Carga de Nuevo Lote de Entrenamiento (.CSV)</label>
            <div id="csv-dropzone" class="dropzone">
              <div class="dropzone-icon">📁</div>
              <p style="font-weight: var(--font-weight-semibold); margin-bottom: 0.25rem;">
                Arrastre y suelte su archivo CSV aquí, o <span style="color: var(--color-accent-600); text-decoration: underline;">examine sus archivos</span>
              </p>
              <p style="font-size: var(--font-size-micro); color: var(--color-primary-500); margin: 0;">
                Máximo 50 MB. Debe contener las 12 columnas censales y la columna objetivo 'income' (>50K / <=50K).
              </p>
              <input type="file" id="csv-file-input" accept=".csv" class="hidden" />
            </div>
            <div id="upload-status" style="margin-top: 0.75rem; font-size: var(--font-size-sm);" class="hidden"></div>
          </div>

          <!-- 2. Botón de Disparo de Re-entrenamiento -->
          <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 1rem; border-top: 1px solid var(--color-primary-200);">
            <div>
              <strong style="color: var(--color-primary-900); font-size: var(--font-size-sm);">Reentrenamiento del Modelo:</strong>
              <p style="font-size: var(--font-size-micro); color: var(--color-primary-500); margin: 0;">
                Ejecuta partición estratificada 80/20, calibración de umbral bajo costo 3:1 y switch atómico de versión.
              </p>
            </div>
            <button type="button" id="btn-start-retrain" class="btn btn-primary" style="min-width: 13rem;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              Iniciar Reentrenamiento
            </button>
          </div>
        </div>

        <!-- 3. Terminal de Streaming en Vivo (WebSocket) -->
        <div style="margin-top: 2rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <label class="form-label" style="margin: 0;">Consola de Ejecución en Vivo (WebSocket Stream)</label>
            <span class="badge badge-neutral" id="ws-status-badge">WebSocket Inactivo</span>
          </div>

          <div class="progress-bar-container" style="height: 0.5rem; margin-bottom: 0.75rem;">
            <div id="retrain-progress-bar" class="progress-bar-fill" style="width: 0%;"></div>
          </div>

          <div id="ws-terminal" class="log-stream-terminal">
            <div style="color: #64748b;">[SISTEMA] Esperando evento de inicio de reentrenamiento...</div>
          </div>
        </div>
      </section>
    </div>
  `;

  setupRetrainEvents(container);
}

function setupRetrainEvents(container) {
  const dropzone = container.querySelector('#csv-dropzone');
  const fileInput = container.querySelector('#csv-file-input');
  const uploadStatus = container.querySelector('#upload-status');
  const btnStartRetrain = container.querySelector('#btn-start-retrain');
  const terminal = container.querySelector('#ws-terminal');
  const progressBar = container.querySelector('#retrain-progress-bar');
  const wsBadge = container.querySelector('#ws-status-badge');
  const authAlert = container.querySelector('#retrain-auth-alert');
  const btnLoginRetrain = container.querySelector('#btn-login-retrain');

  btnLoginRetrain?.addEventListener('click', () => window.openLoginModal?.());

  // Verificar estado de autenticación
  if (!apiService.isAuthenticated()) {
    authAlert.classList.remove('hidden');
  }

  // Eventos de Dropzone
  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0], uploadStatus);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFileUpload(e.target.files[0], uploadStatus);
    }
  });

  // Botón Reentrenar
  btnStartRetrain.addEventListener('click', async () => {
    if (!apiService.isAuthenticated()) {
      window.showToast?.('Debe iniciar sesión para reentrenar el modelo.', 'error');
      window.openLoginModal?.();
      return;
    }

    btnStartRetrain.disabled = true;
    terminal.innerHTML = `<div style="color: #38bdf8;">[INICIO] Conectando canal WebSocket y preparando reentrenamiento...</div>`;
    progressBar.style.width = '5%';
    wsBadge.textContent = 'Conectando...';
    wsBadge.className = 'badge badge-warning';

    // Abrir WebSocket
    apiService.connectWebSocket(
      (data) => {
        // Al recibir mensaje
        const logLine = document.createElement('div');
        const timestamp = new Date().toLocaleTimeString();
        logLine.innerHTML = `<span style="color: #64748b;">[${timestamp}]</span> <strong style="color: #38bdf8;">[${(data.stage || 'STAGE').toUpperCase()}]:</strong> ${data.message || ''}`;
        terminal.appendChild(logLine);
        terminal.scrollTop = terminal.scrollHeight;

        if (data.progress !== undefined) {
          progressBar.style.width = `${data.progress}%`;
        }

        if (data.stage === 'connected') {
          wsBadge.textContent = 'WS Conectado';
          wsBadge.className = 'badge badge-positive';
        } else if (data.stage === 'completed') {
          progressBar.style.width = '100%';
          wsBadge.textContent = 'Completado 100%';
          wsBadge.className = 'badge badge-positive';
          btnStartRetrain.disabled = false;
          window.showToast?.('¡Reentrenamiento completado con éxito! Modelo en producción.', 'success');
        } else if (data.stage === 'error') {
          wsBadge.textContent = 'Error';
          wsBadge.className = 'badge badge-negative';
          btnStartRetrain.disabled = false;
        }
      },
      (err) => {
        wsBadge.textContent = 'Error WS';
        wsBadge.className = 'badge badge-negative';
        btnStartRetrain.disabled = false;
      },
      () => {
        // Al cerrar
        if (progressBar.style.width !== '100%') {
          wsBadge.textContent = 'Desconectado';
        }
      }
    );

    // Disparar endpoint de reentrenamiento
    try {
      await apiService.triggerRetrain();
    } catch (err) {
      terminal.innerHTML += `<div style="color: #f87171;">[ERROR]: ${err.message}</div>`;
      btnStartRetrain.disabled = false;
      window.showToast?.(`Error al disparar reentrenamiento: ${err.message}`, 'error');
    }
  });
}

async function handleFileUpload(file, statusEl) {
  if (!file.name.endsWith('.csv')) {
    window.showToast?.('Solo se admiten archivos en formato .CSV', 'error');
    return;
  }

  statusEl.classList.remove('hidden');
  statusEl.innerHTML = `<span class="spinner" aria-hidden="true"></span> Subiendo y validando ${file.name}...`;

  try {
    const res = await apiService.uploadDataset(file);
    statusEl.innerHTML = `
      <span style="color: var(--color-positive);">
        ✅ <strong>${res.filename}</strong> cargado con éxito (${res.rows_ingested?.toLocaleString() || 0} filas validadas). ID: ${res.dataset_id}
      </span>
    `;
    window.showToast?.(`Dataset ${file.name} listo para reentrenamiento.`, 'success');
  } catch (err) {
    statusEl.innerHTML = `<span style="color: var(--color-negative);">❌ Error: ${err.message}</span>`;
    window.showToast?.(`Fallo de subida: ${err.message}`, 'error');
  }
}
