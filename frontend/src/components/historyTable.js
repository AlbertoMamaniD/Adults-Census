/**
 * HISTORYTABLE.JS — Módulo 3: Historial Paginado y Auditoría en Supabase
 * Diseñado para comités de cumplimiento y trazabilidad regulatoria bancaria.
 */

import { apiService } from '../services/apiService.js';

export function renderHistoryTable(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = `
    <!-- Banner de Cumplimiento Regulatorio -->
    <div class="bank-callout">
      <div class="bank-callout-icon" aria-hidden="true">🔒</div>
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

  btnRefresh.addEventListener('click', () => loadHistory(container, pageLimit, currentOffset));
  btnLoginHistory?.addEventListener('click', () => window.openLoginModal?.());

  btnPrev.addEventListener('click', () => {
    if (currentOffset >= pageLimit) {
      currentOffset -= pageLimit;
      loadHistory(container, pageLimit, currentOffset);
    }
  });

  btnNext.addEventListener('click', () => {
    currentOffset += pageLimit;
    loadHistory(container, pageLimit, currentOffset);
  });

  loadHistory(container, pageLimit, currentOffset);
}

export async function loadHistory(container, limit = 15, offset = 0) {
  const unauthBox = container.querySelector('#history-unauth');
  const tableWrapper = container.querySelector('#history-table-wrapper');
  const tbody = container.querySelector('#history-tbody');
  const countLabel = container.querySelector('#history-count-label');
  const btnPrev = container.querySelector('#btn-prev-page');
  const btnNext = container.querySelector('#btn-next-page');

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

  try {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem;">Cargando registros desde Supabase...</td></tr>`;
    const resp = await apiService.getHistory(limit, offset);
    const items = resp.items || [];
    const total = resp.total || 0;

    if (items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem; color: var(--color-primary-500);">No se encontraron solicitudes registradas en este rango.</td></tr>`;
      countLabel.textContent = `Total: ${total} registros`;
      btnPrev.disabled = offset === 0;
      btnNext.disabled = true;
      return;
    }

    tbody.innerHTML = items.map(row => {
      const isSolvent = row.predicted_class === '>50K';
      const badgeClass = isSolvent ? 'badge-positive' : 'badge-negative';
      const badgeText = isSolvent ? 'CALIFICA (>50K)' : 'NO CALIFICA (<=50K)';
      const probPct = (row.probability * 100).toFixed(1);
      const dateStr = new Date(row.created_at).toLocaleString();
      const inp = row.input_data || {};

      return `
        <tr>
          <td><strong style="color: var(--color-accent-600);">#${row.id}</strong></td>
          <td style="white-space: nowrap; font-size: 0.8125rem;">${dateStr}</td>
          <td><span class="badge badge-neutral" style="font-size: 0.7rem;">${row.model_version || 'v_latest'}</span></td>
          <td style="font-size: 0.8125rem;">
            <strong>${inp.age || '--'} años</strong> | ${inp.occupation || 'N/A'}<br/>
            <span style="color: var(--color-primary-500); font-size: 0.75rem;">${inp.workclass || 'N/A'} • ${inp.education_num || '--'} años de estudio</span>
          </td>
          <td>
            <div style="font-weight: 600; color: ${isSolvent ? 'var(--color-positive)' : 'var(--color-negative)'}; font-size: 0.875rem;">
              ${probPct}%
            </div>
          </td>
          <td><span class="badge ${badgeClass}">${badgeText}</span></td>
          <td style="font-size: 0.8125rem; color: var(--color-primary-600);">${row.latency_ms?.toFixed(1) || '--'} ms</td>
        </tr>
      `;
    }).join('');

    countLabel.textContent = `Registros ${offset + 1} a ${Math.min(offset + limit, total)} de ${total} en Supabase`;
    btnPrev.disabled = offset === 0;
    btnNext.disabled = (offset + limit) >= total;

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem; color: var(--color-negative);">Error al cargar auditoría: ${err.message}</td></tr>`;
    countLabel.textContent = 'Error de conexión';
  }
}
