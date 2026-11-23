/**
 * RETRAINCENTER.JS — Módulo 4: Carga de Datos y Reentrenamiento Continuo MLOps
 * Permite adaptar el scoring a cambios macroeconómicos y nuevos lotes de clientes.
 */

import { apiService } from '../services/apiService.js';
import { stateService } from '../services/stateService.js';
import { loadMetricsData } from './metricsDashboard.js';
import { loadHistory } from './historyTable.js';

export function renderRetrainCenter(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = `
    <!-- Banner de Negocio MLOps -->
    <div class="bank-callout">
      <div class="bank-callout-icon" aria-hidden="true">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
        </svg>
      </div>
      <div class="bank-callout-text">
        <h4>Actualización Continua del Scoring Crediticio (Ciclo MLOps)</h4>
        <p>
          Las condiciones económicas y los perfiles de mora evolucionan con el tiempo (<em>Data Drift</em>). Esta consola permite al equipo de analistas ingresar nuevos lotes de solicitudes con datos de pago reales para recalibrar los pesos del clasificador y actualizar el umbral óptimo de corte, realizando una promoción atómica sin interrumpir las operaciones en ventanilla (<em>Zero-Downtime Deployment</em>).
        </p>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr; gap: 2rem;">
      <section class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
              Centro de Reentrenamiento y Gobernanza de Modelos
            </h2>
            <p class="card-subtitle" style="margin: 0;">Ingesta de nuevos datos censales, partición estratificada 80/20 y switch atómico de versión.</p>
          </div>
        </div>

        <!-- Alerta de Autenticación si no hay token -->
        <div id="retrain-auth-alert" class="hidden" style="background-color: var(--color-warning-bg); border: 1px solid var(--color-warning-border); padding: 1rem; border-radius: var(--radius-md); margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.75rem; color: var(--color-warning-hover); font-size: var(--font-size-sm);">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            <span><strong>Control de Seguridad Bancaria:</strong> Se requiere autorización de analista con token JWT para subir nuevos lotes o iniciar el reentrenamiento.</span>
          </div>
          <button type="button" id="btn-login-retrain" class="btn btn-secondary btn-sm">Iniciar Sesión</button>
        </div>

        <div style="display: grid; grid-template-columns: 1fr; gap: 1.5rem;">
          <!-- 1. Zona Drag & Drop para Cargar CSV -->
          <div>
            <label class="form-label">
              1. Carga de Nuevo Lote de Clientes (.CSV)
              <span class="badge badge-neutral">Máx 50 MB</span>
            </label>
            <div id="csv-dropzone" class="dropzone">
              <div class="dropzone-icon">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" style="color: var(--color-accent-600);">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="17 8 12 3 7 8"></polyline>
                  <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
              </div>
              <p style="font-weight: var(--font-weight-semibold); margin-bottom: 0.25rem; color: var(--color-primary-800);">
                Arrastre y suelte su archivo CSV aquí, o <span style="color: var(--color-accent-600); text-decoration: underline;">seleccione desde su equipo</span>
              </p>
              <p style="font-size: var(--font-size-micro); color: var(--color-primary-500); margin: 0; max-width: 30rem; margin: 0 auto;">
                El archivo debe contener las 12 columnas socioeconómicas y la columna objetivo 'income' (&gt;50K / &lt;=50K) para su validación de esquema bancario.
              </p>
              <input type="file" id="csv-file-input" accept=".csv" class="hidden" />
            </div>
            <div id="upload-status" style="margin-top: 0.75rem; font-size: var(--font-size-sm);" class="hidden"></div>
          </div>

          <!-- 2. Botón de Disparo de Re-entrenamiento -->
          <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 1.25rem; border-top: 1px solid var(--color-primary-200); flex-wrap: wrap; gap: 1rem;">
            <div>
              <strong style="color: var(--color-primary-900); font-size: var(--font-size-sm); display: block; margin-bottom: 0.2rem;">
                2. Ejecutar Pipeline de Reentrenamiento Automático:
              </strong>
              <p style="font-size: var(--font-size-micro); color: var(--color-primary-500); margin: 0; max-width: 32rem;">
                Ajusta el algoritmo HistGradientBoosting, calibra el nuevo umbral robusto contra la función de costo 3:1 y registra el nuevo modelo en Supabase.
              </p>
            </div>
            <button type="button" id="btn-start-retrain" class="btn btn-primary" style="min-width: 14rem;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              Iniciar Reentrenamiento
            </button>
          </div>
        </div>

        <!-- 3. Terminal de Streaming en Vivo (WebSocket) -->
        <div style="margin-top: 2rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <label class="form-label" style="margin: 0; font-weight: 600;">
              Consola de Trazabilidad en Vivo (WebSocket Event Stream)
            </label>
            <span class="badge badge-neutral" id="ws-status-badge">WebSocket Inactivo</span>
          </div>

          <div class="progress-bar-container" style="height: 0.5rem; margin-bottom: 0.75rem;">
            <div id="retrain-progress-bar" class="progress-bar-fill" style="width: 0%;"></div>
          </div>

          <div id="ws-terminal" class="log-stream-terminal">
            <div style="color: #64748b;">[SISTEMA BANCARIO] Esperando inicio del ciclo de reentrenamiento MLOps...</div>
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

  let currentUploadedDatasetId = null;

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
      handleFileUpload(e.dataTransfer.files[0], uploadStatus, (id) => { currentUploadedDatasetId = id; });
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFileUpload(e.target.files[0], uploadStatus, (id) => { currentUploadedDatasetId = id; });
    }
  });

  // Botón Reentrenar
  btnStartRetrain.addEventListener('click', async () => {
    if (!apiService.isAuthenticated()) {
      window.showToast?.('Se requiere autenticación para reentrenar el modelo.', 'error');
      window.openLoginModal?.();
      return;
    }

    btnStartRetrain.disabled = true;
    terminal.innerHTML = '';
    const initLine = document.createElement('div');
    initLine.style.color = '#38bdf8';
    initLine.textContent = '[INICIO] Estableciendo canal WebSocket seguro y preparando pipeline CRISP-ML(Q)...';
    terminal.appendChild(initLine);
    progressBar.style.width = '5%';
    wsBadge.textContent = 'Conectando...';
    wsBadge.className = 'badge badge-warning';

    // Abrir WebSocket para streaming en tiempo real
    apiService.connectWebSocket(
      (data) => {
        wsBadge.textContent = 'En Ejecución';
        wsBadge.className = 'badge badge-positive';

        const stage = data.stage || 'proceso';
        const msg = String(data.message || (typeof data === 'object' ? JSON.stringify(data) : data));
        const progress = data.progress !== undefined ? Number(data.progress) : (data.progress_pct !== undefined ? Number(data.progress_pct) : 0);

        if (!isNaN(progress) && progress > 0) {
          progressBar.style.width = `${Math.min(100, Math.max(0, progress))}%`;
        }

        const logLine = document.createElement('div');
        logLine.style.marginBottom = '0.25rem';

        if (stage === 'completed') {
          logLine.style.color = '#34d399';
          const strongTag = document.createElement('strong');
          strongTag.textContent = '[EXITO] ';
          logLine.appendChild(strongTag);
          logLine.appendChild(document.createTextNode(msg));

          progressBar.style.width = '100%';
          wsBadge.textContent = 'Completado';
          wsBadge.className = 'badge badge-positive';

          // Sincronizar en vivo el nuevo modelo y umbral con todos los módulos
          const payload = data.payload || {};
          const newModel = payload.new_model_version;
          const newThresh = payload.threshold;
          if (newModel) {
            stateService.setSystemStatus(true, newModel, newThresh);
          }

          // Refrescar métricas e historial en segundo plano
          const metricsPane = document.getElementById('tab-metrics');
          if (metricsPane) {
            loadMetricsData(metricsPane);
          }
          const histPane = document.getElementById('tab-history');
          if (histPane) {
            loadHistory(histPane, 15, 0, true);
          }

          window.showToast?.('Reentrenamiento completado con éxito. Modelo activado en vivo.', 'success');
        } else if (stage === 'error') {
          logLine.style.color = '#f87171';
          const strongTag = document.createElement('strong');
          strongTag.textContent = '[ERROR] ';
          logLine.appendChild(strongTag);
          logLine.appendChild(document.createTextNode(msg));

          wsBadge.textContent = 'Error';
          wsBadge.className = 'badge badge-negative';
          window.showToast?.(`Fallo en reentrenamiento: ${msg}`, 'error');
        } else {
          const stageSpan = document.createElement('span');
          stageSpan.style.color = '#94a3b8';
          stageSpan.textContent = `[${stage.toUpperCase()}] `;
          logLine.appendChild(stageSpan);
          logLine.appendChild(document.createTextNode(msg));
        }

        terminal.appendChild(logLine);
        terminal.scrollTop = terminal.scrollHeight;
      },
      (err) => {
        wsBadge.textContent = 'Error WS';
        wsBadge.className = 'badge badge-negative';
      },
      () => {
        if (wsBadge.textContent !== 'Completado' && wsBadge.textContent !== 'Error') {
          wsBadge.textContent = 'Canal Cerrado';
          wsBadge.className = 'badge badge-neutral';
        }
      }
    );

    // Disparar endpoint de reentrenamiento
    try {
      const retrainResp = await apiService.triggerRetrain(currentUploadedDatasetId);
      if (retrainResp && retrainResp.new_model_version) {
        stateService.setSystemStatus(true, retrainResp.new_model_version, retrainResp.threshold);
        const metricsPane = document.getElementById('tab-metrics');
        if (metricsPane) {
          loadMetricsData(metricsPane);
        }
      }
    } catch (err) {
      const errLine = document.createElement('div');
      errLine.style.color = '#f87171';
      errLine.textContent = `[ERROR DE DISPARO] ${err.message}`;
      terminal.appendChild(errLine);
    } finally {
      btnStartRetrain.disabled = false;
    }
  });
}

async function handleFileUpload(file, statusEl, onDatasetUploaded = null) {
  if (!file.name.endsWith('.csv')) {
    statusEl.innerHTML = `<div class="badge badge-negative">El archivo debe tener formato .csv</div>`;
    statusEl.classList.remove('hidden');
    return;
  }

  statusEl.innerHTML = `<div style="color: var(--color-primary-600);"><span class="spinner"></span> Validando e ingiriendo archivo (${(file.size / (1024 * 1024)).toFixed(2)} MB)...</div>`;
  statusEl.classList.remove('hidden');

  try {
    const res = await apiService.uploadDataset(file);
    if (onDatasetUploaded && res.dataset_id) {
      onDatasetUploaded(res.dataset_id);
    }
    statusEl.innerHTML = '';
    const successBox = document.createElement('div');
    successBox.style.cssText = 'background-color: var(--color-positive-bg); border: 1px solid var(--color-positive-border); color: var(--color-positive); padding: 0.75rem; border-radius: var(--radius-sm); display: flex; align-items: center; gap: 0.5rem;';
    successBox.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
    const textSpan = document.createElement('span');
    const strongPrefix = document.createElement('strong');
    strongPrefix.textContent = 'Lote Ingerido Exitosamente: ';
    textSpan.appendChild(strongPrefix);
    textSpan.appendChild(document.createTextNode(`Se validaron ${res.rows_ingested || 'todas las'} filas censales en Supabase (Dataset ID: #${res.dataset_id || 1}).`));
    successBox.appendChild(textSpan);
    statusEl.appendChild(successBox);
    window.showToast?.('Dataset validado e ingresado a training_datasets', 'success');
  } catch (err) {
    statusEl.innerHTML = '';
    const errBox = document.createElement('div');
    errBox.style.cssText = 'background-color: var(--color-negative-bg); border: 1px solid var(--color-negative-border); color: var(--color-negative); padding: 0.75rem; border-radius: var(--radius-sm); display: flex; align-items: center; gap: 0.5rem;';
    errBox.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
    const textSpan = document.createElement('span');
    const strongPrefix = document.createElement('strong');
    strongPrefix.textContent = 'Error en la Ingesta: ';
    textSpan.appendChild(strongPrefix);
    textSpan.appendChild(document.createTextNode(err.message || 'Error desconocido'));
    errBox.appendChild(textSpan);
    statusEl.appendChild(errBox);
    window.showToast?.(`Error al subir CSV: ${err.message}`, 'error');
  }
}
