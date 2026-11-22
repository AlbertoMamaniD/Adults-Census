/**
 * HISTORYTABLE.JS — Módulo 3: Historial Paginado y Auditoría en Supabase
 */

import { apiService } from '../services/apiService.js';

export function renderHistoryTable(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div>
          <h2>Auditoría de Inferencias (Supabase PostgreSQL)</h2>
          <p class="text-muted" style="font-size: var(--font-size-sm); margin: 0;">
            Historial inmutable de solicitudes evaluadas por la API para trazabilidad regulatoria bancaria.
          </p>
        </div>
        <div style="display: flex; gap: 0.5rem; align-items: center;">
          <button type="button" id="btn-refresh-history" class="btn btn-secondary btn-sm">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
            Refrescar
          </button>
        </div>
      </div>

      <!-- Estado No Autenticado -->
      <div id="history-unauth" class="hidden" style="text-align: center; padding: 3rem 1.5rem; background-color: var(--color-primary-50); border-radius: var(--radius-md);">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin: 0 auto 1rem; color: var(--color-warning);"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
        <h3 style="margin-bottom: 0.5rem;">Autenticación Requerida</h3>
        <p style="font-size: var(--font-size-sm); color: var(--color-primary-600); max-width: 28rem; margin: 0 auto 1.25rem;">
          Por directivas de seguridad bancaria, la consulta del historial de clientes requiere inicio de sesión de analista con token JWT.
        </p>
        <button type="button" id="btn-login-history" class="btn btn-primary btn-sm">
          Iniciar Sesión como Analista
        </button>
      </div>

      <!-- Tabla de Datos -->
      <div id="history-table-wrapper" class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Fecha / Hora (UTC)</th>
              <th>Versión IA</th>
              <th>Datos Demográficos Clave</th>
              <th>Probabilidad</th>
              <th>Resultado</th>
              <th>Latencia</th>
            </tr>
          </thead>
          <tbody id="history-tbody">
            <tr>
              <td colspan="7" style="text-align: center; padding: 2rem; color: var(--color-primary-500);">
                Cargando registros auditados...
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Paginación -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1.25rem; font-size: var(--font-size-sm);">
        <span id="history-count-label" class="text-muted">Mostrando 0 registros</span>
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
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem;">Cargando...</td></tr>`;
    const resp = await apiService.getHistory(limit, offset);
    const items = resp.items || [];
    const total = resp.total || 0;

    if (items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem; color: var(--color-primary-500);">No se encontraron predicciones en este rango.</td></tr>`;
      countLabel.textContent = `Total: ${total} registros`;
      btnPrev.disabled = offset === 0;
      btnNext.disabled = true;
      return;
    }

    tbody.innerHTML = items.map(row => {
      const isSolvent = row.predicted_class === '>50K';
      const badgeClass = isSolvent ? 'badge-positive' : 'badge-negative';
      const probPct = (row.probability * 100).toFixed(1);
      const dateStr = new Date(row.created_at).toLocaleString();
      const inp = row.input_data || {};
      const summary = `Edad: ${inp.age || '--'}, Edu: ${inp.education_num || '--'}, Horas: ${inp.hours_per_week || '--'}`;

      return `
        <tr>
          <td><strong>#${row.id}</strong></td>
          <td style="white-space: nowrap;">${dateStr}</td>
          <td><span class="badge badge-neutral">${row.model_version}</span></td>
          <td style="font-size: 0.8125rem;">${summary}</td>
          <td><strong>${probPct}%</strong></td>
          <td><span class="badge ${badgeClass}">${row.predicted_class}</span></td>
          <td style="color: var(--color-primary-500);">${row.latency_ms?.toFixed(1) || '--'} ms</td>
        </tr>
      `;
    }).join('');

    countLabel.textContent = `Mostrando ${offset + 1} - ${offset + items.length} de ${total} registros`;
    btnPrev.disabled = offset === 0;
    btnNext.disabled = (offset + items.length) >= total;
  } catch (err) {
    if (err.status === 401) {
      unauthBox.classList.remove('hidden');
      tableWrapper.classList.add('hidden');
      countLabel.textContent = 'Token expirado o inválido';
    } else {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--color-negative); padding: 2rem;">Error: ${err.message}</td></tr>`;
    }
  }
}
