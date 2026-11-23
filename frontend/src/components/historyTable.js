/**
 * HISTORYTABLE.JS — Módulo 3: Historial Paginado y Auditoría en Supabase
 * Diseñado para comités de cumplimiento y trazabilidad regulatoria bancaria.
 */

import { apiService } from '../services/apiService.js';

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export function renderHistoryTable(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!container.dataset) {
    container.dataset = {};
  }
  container.dataset.offset = '0';

  container.innerHTML = `
    <!-- Banner de Cumplimiento Regulatorio -->
    <div class="bank-callout">
      <div class="bank-callout-icon" aria-hidden="true">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
        </svg>
      </div>
      <div class="bank-callout-text">
        <h4>Libro de Auditoría y Trazabilidad Transaccional (Supabase PostgreSQL)</h4>
        <p>
          En estricto apego a las directivas de gobernanza y Basilea III, todas las solicitudes procesadas por la API quedan registradas de manera inmutable con sus 12 parámetros de entrada, el veredicto del modelo, la probabilidad y la latencia del cálculo.
        </p>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div>
          <h2 class="card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>
            Auditoría de Evaluaciones Crediticias
          </h2>
          <p class="card-subtitle" style="margin: 0;">Registro histórico en tiempo real conectado a base de datos relacional en la nube.</p>
        </div>
        <div style="display: flex; gap: 0.5rem; align-items: center;">
          <button type="button" id="btn-refresh-history" class="btn btn-secondary btn-sm">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
            Refrescar Historial
          </button>
        </div>
      </div>

      <!-- Estado No Autenticado -->
      <div id="history-unauth" class="hidden" style="text-align: center; padding: 3.5rem 1.5rem; background: linear-gradient(180deg, var(--color-primary-50) 0%, #ffffff 100%); border: 1px dashed var(--color-primary-200); border-radius: var(--radius-lg); margin: 1rem 0;">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin: 0 auto 1rem; color: var(--color-warning);"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
        <h3 style="margin-bottom: 0.5rem; color: var(--color-primary-900);">Módulo Restringido — Autenticación Requerida</h3>
        <p style="font-size: var(--font-size-sm); color: var(--color-primary-600); max-width: 32rem; margin: 0 auto 1.25rem; line-height: 1.5;">
          Por directivas de secreto bancario y protección de datos financieros, la consulta del historial de clientes requiere inicio de sesión de analista con token criptográfico JWT Bearer.
        </p>
        <button type="button" id="btn-login-history" class="btn btn-primary btn-sm">
          Iniciar Sesión como Analista Financiero
        </button>
      </div>

      <!-- Tabla de Datos Bancaria -->
      <div id="history-table-wrapper" class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 5rem;">Nº Solicitud</th>
              <th>Fecha y Hora (UTC)</th>
              <th>Versión IA</th>
              <th>Perfil Evaluado (Edad / Cargo / Estudios)</th>
              <th>Probabilidad</th>
              <th>Dictamen de Riesgo</th>
              <th>Latencia</th>
            </tr>
          </thead>
          <tbody id="history-tbody">
            <tr>
              <td colspan="7" style="text-align: center; padding: 2.5rem; color: var(--color-primary-500);">
                Cargando registros auditados...
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Controles de Paginación -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1.25rem; font-size: var(--font-size-sm); padding-top: 0.75rem; border-top: 1px solid var(--color-primary-100);">
        <span id="history-count-label" class="text-muted">Cargando registros...</span>
        <div style="display: flex; gap: 0.5rem;">
          <button type="button" id="btn-prev-page" class="btn btn-secondary btn-sm" disabled>Anterior</button>
          <button type="button" id="btn-next-page" class="btn btn-secondary btn-sm" disabled>Siguiente</button>
        </div>
      </div>
    </div>
  `;

  let currentOffset = 0;
  const pageLimit = 15;

  const btnRefresh = container.querySelector('#btn-refresh-history');
  const btnPrev = container.querySelector('#btn-prev-page');
  const btnNext = container.querySelector('#btn-next-page');
  const btnLoginHistory = container.querySelector('#btn-login-history');

  btnRefresh.addEventListener('click', () => {
    const curOff = parseInt(container.dataset.offset || '0', 10);
    loadHistory(container, pageLimit, curOff);
  });
  btnLoginHistory?.addEventListener('click', () => window.openLoginModal?.());

  btnPrev.addEventListener('click', () => {
    let curOff = parseInt(container.dataset.offset || '0', 10);
    if (curOff >= pageLimit) {
      curOff -= pageLimit;
      container.dataset.offset = String(curOff);
      loadHistory(container, pageLimit, curOff);
    }
  });

  btnNext.addEventListener('click', () => {
    let curOff = parseInt(container.dataset.offset || '0', 10);
    curOff += pageLimit;
    container.dataset.offset = String(curOff);
    loadHistory(container, pageLimit, curOff);
  });

  loadHistory(container, pageLimit, 0);
}

export async function loadHistory(container, limit = 15, offset = null, isSilent = false) {
  const unauthBox = container.querySelector('#history-unauth');
  const tableWrapper = container.querySelector('#history-table-wrapper');
  const tbody = container.querySelector('#history-tbody');
  const countLabel = container.querySelector('#history-count-label');
  const btnPrev = container.querySelector('#btn-prev-page');
  const btnNext = container.querySelector('#btn-next-page');
  const btnRefresh = container.querySelector('#btn-refresh-history');

  // Si no se suministra un offset específico, conservar la página actual del usuario
  const storedOffset = parseInt(container?.dataset?.offset || '0', 10);
  const effectiveOffset = (offset !== null && offset !== undefined) ? offset : storedOffset;
  if (container?.dataset) {
    container.dataset.offset = String(effectiveOffset);
  }

  if (!apiService.isAuthenticated()) {
    unauthBox.classList.remove('hidden');
    tableWrapper.classList.add('hidden');
    countLabel.textContent = 'Acceso protegido por token JWT';
    btnPrev.disabled = true;
    btnNext.disabled = true;
    return;
  }

  unauthBox.classList.add('hidden');
  tableWrapper.classList.remove('hidden');

  // Si ya hay filas reales renderizadas, realizar la recarga silenciosa en segundo plano
  const hasExistingRows = tbody && tbody.querySelectorAll('tr[data-id]').length > 0;
  const shouldBeSilent = isSilent || hasExistingRows;

  if (btnRefresh) {
    btnRefresh.classList.add('btn-refreshing');
  }

  try {
    if (!shouldBeSilent) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem;">Cargando registros desde Supabase...</td></tr>`;
    }

    const resp = await apiService.getHistory(limit, effectiveOffset);
    const items = Array.isArray(resp) ? resp : (resp.items || []);
    const count = items.length;

    if (items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2.5rem; color: var(--color-primary-600); font-size: var(--font-size-body);">No se encontraron solicitudes registradas en este rango.</td></tr>`;
      countLabel.textContent = effectiveOffset === 0 ? 'Sin registros históricos registrados' : `Página vacía (desplazamiento: ${effectiveOffset})`;
      btnPrev.disabled = effectiveOffset === 0;
      btnNext.disabled = true;
      return;
    }

    // Verificar si los IDs actuales son idénticos para evitar re-render innecesario
    const currentIds = Array.from(tbody.querySelectorAll('tr[data-id]')).map(el => el.getAttribute('data-id')).join(',');
    const newIds = items.map(r => String(r.id)).join(',');

    if (currentIds !== newIds) {
      tbody.innerHTML = items.map(row => {
        const isSolvent = row.predicted_class === '>50K';
        const badgeClass = isSolvent ? 'badge-positive' : 'badge-negative';
        const badgeText = isSolvent ? 'CALIFICA (>50K)' : 'NO CALIFICA (<=50K)';
        const probPct = (row.probability * 100).toFixed(1);
        const dateStr = new Date(row.created_at).toLocaleString();
        const inp = row.input_data || {};

        return `
          <tr data-id="${escapeHtml(row.id)}">
            <td><strong style="color: var(--color-accent-600); font-weight: 700;">#${escapeHtml(row.id)}</strong></td>
            <td style="white-space: nowrap; font-size: 0.875rem;">${escapeHtml(dateStr)}</td>
            <td><span class="badge badge-neutral" style="font-size: 0.75rem;">${escapeHtml(row.model_version || 'v_latest')}</span></td>
            <td style="font-size: 0.875rem;">
              <strong style="color: var(--color-primary-900);">${escapeHtml(inp.age || '--')} años</strong> | ${escapeHtml(inp.occupation || 'N/A')}<br/>
              <span style="color: var(--color-primary-600); font-size: 0.8125rem;">${escapeHtml(inp.workclass || 'N/A')} • ${escapeHtml(inp.education_num || '--')} años estudio</span>
            </td>
            <td>
              <div style="font-weight: 700; color: ${isSolvent ? 'var(--color-positive)' : 'var(--color-negative)'}; font-size: 0.9375rem;">
                ${escapeHtml(probPct)}%
              </div>
            </td>
            <td><span class="badge ${badgeClass}">${badgeText}</span></td>
            <td style="font-size: 0.875rem; color: var(--color-primary-700); font-weight: 500;">${escapeHtml(row.latency_ms?.toFixed(1) || '--')} ms</td>
          </tr>
        `;
      }).join('');
    }

    countLabel.textContent = `Mostrando ${effectiveOffset + 1} a ${effectiveOffset + count} registros en Supabase`;
    btnPrev.disabled = effectiveOffset === 0;
    btnNext.disabled = count < limit;

  } catch (err) {
    if (!shouldBeSilent) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem; color: var(--color-negative);" id="history-err-cell"></td></tr>`;
      const errCell = tbody.querySelector('#history-err-cell');
      if (errCell) {
        errCell.textContent = `Error al cargar auditoría: ${err.message || 'Error de conexión'}`;
      }
      countLabel.textContent = 'Error de conexión';
    }
  } finally {
    if (btnRefresh) {
      btnRefresh.classList.remove('btn-refreshing');
    }
  }
}
