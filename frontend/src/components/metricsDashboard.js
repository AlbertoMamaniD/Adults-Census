/**
 * METRICSDASHBOARD.JS — Módulo 2: Visualización de KPIs y Matriz de Confusión
 */

import { apiService } from '../services/apiService.js';

export function renderMetricsDashboard(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = `
    <div>
      <div class="card-header" style="margin-bottom: 1.5rem; padding-bottom: 0.75rem;">
        <div>
          <h2>Métricas del Modelo de IA (CRISP-ML(Q))</h2>
          <p class="text-muted" style="font-size: var(--font-size-sm); margin: 0;">
            Monitoreo de calidad, umbral de decisión calibrado y función de costo asimétrica bancaria.
          </p>
        </div>
        <button type="button" id="btn-refresh-metrics" class="btn btn-secondary btn-sm">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
          Actualizar Métricas
        </button>
      </div>

      <!-- Grid de KPIs Clave -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Matthews Correlation (MCC)</div>
          <div class="kpi-value" id="kpi-mcc">--</div>
          <div class="kpi-goal">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
            Meta: MCC ≥ 0.55
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">ROC-AUC Score</div>
          <div class="kpi-value" id="kpi-roc-auc">--</div>
          <div class="kpi-goal">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
            Meta: ROC-AUC > 0.85 (Excelente)
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Precisión Solvente (>50K)</div>
          <div class="kpi-value" id="kpi-precision">--</div>
          <div class="kpi-goal">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
            Meta: Precisión ≥ 0.75
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Recall / Sensibilidad</div>
          <div class="kpi-value" id="kpi-recall">--</div>
          <div class="kpi-goal">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
            Meta: Recall ≥ 0.60
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Umbral Calibrado (θ)</div>
          <div class="kpi-value" id="kpi-threshold" style="color: var(--color-accent-600);">--</div>
          <div style="font-size: var(--font-size-micro); color: var(--color-primary-500);">
            Optimizado contra 3×FP + 1×FN
          </div>
        </div>
      </div>

      <!-- Detalle de Matriz de Confusión y Función de Costo -->
      <div class="confusion-matrix-wrapper">
        <section class="card">
          <div class="card-header">
            <h3 class="card-title">Matriz de Confusión (Test Set: 6.508 Solicitudes)</h3>
            <span class="badge badge-neutral" id="cm-model-tag">v_latest</span>
          </div>
          <p style="font-size: var(--font-size-sm); color: var(--color-primary-600);">
            Evaluación simétrica sobre el 20% de validación independiente no visto en entrenamiento.
          </p>

          <div class="cm-grid">
            <div class="cm-cell tn">
              <div class="cm-value text-muted" id="cm-tn">--</div>
              <div class="cm-title">Verdaderos Negativos (TN)</div>
              <span style="font-size: 0.75rem; color: var(--color-primary-500);">Rechazo acertado de insolvente</span>
            </div>

            <div class="cm-cell fp">
              <div class="cm-value text-negative" id="cm-fp">--</div>
              <div class="cm-title text-negative">Falsos Positivos (FP)</div>
              <span style="font-size: 0.75rem; color: var(--color-negative);">Riesgo Crítico de Mora (Costo 3x)</span>
            </div>

            <div class="cm-cell fn">
              <div class="cm-value text-warning" id="cm-fn">--</div>
              <div class="cm-title text-warning">Falsos Negativos (FN)</div>
              <span style="font-size: 0.75rem; color: var(--color-warning);">Costo Oportunidad Comercial (1x)</span>
            </div>

            <div class="cm-cell tp">
              <div class="cm-value text-positive" id="cm-tp">--</div>
              <div class="cm-title text-positive">Verdaderos Positivos (TP)</div>
              <span style="font-size: 0.75rem; color: var(--color-positive);">Aprobación acertada de solvente</span>
            </div>
          </div>
        </section>

        <section class="card">
          <div class="card-header">
            <h3 class="card-title">Justificación Matemática y Negocio</h3>
          </div>
          <div style="font-size: var(--font-size-sm); color: var(--color-primary-700); line-height: 1.6;">
            <p><strong>Función de Costo Asimétrica del Banco:</strong></p>
            <div style="background-color: var(--color-primary-50); padding: 0.75rem; border-radius: var(--radius-sm); font-family: monospace; margin-bottom: 0.75rem;">
              C = 3 × FP + 1 × FN = <span id="cm-cost-val" style="font-weight: bold; color: var(--color-primary-900);">--</span>
            </div>
            <p>
              • <strong>Falso Positivo (FP = 3x):</strong> Prestar a un insolvente genera pérdida directa del capital del banco y gastos legales de recuperación.
            </p>
            <p>
              • <strong>Falso Negativo (FN = 1x):</strong> Dejar pasar a un solvente solo pierde el interés potencial, pero el capital bancario queda protegido.
            </p>
            <p style="margin-bottom: 0;">
              • <strong>Umbral θ = 0.77:</strong> En lugar del estándar 0.50 (que genera altos FPs), se exige un 77% de certidumbre para minimizar matemáticamente las pérdidas financieras.
            </p>
          </div>
        </section>
      </div>
    </div>
  `;

  const btnRefresh = container.querySelector('#btn-refresh-metrics');
  btnRefresh.addEventListener('click', () => loadMetricsData(container));

  loadMetricsData(container);
}

export async function loadMetricsData(container) {
  try {
    const data = await apiService.getMetrics();
    const m = data.metrics || {};
    const cm = m.confusion_matrix || {};

    container.querySelector('#kpi-mcc').textContent = m.mcc ? m.mcc.toFixed(4) : '--';
    container.querySelector('#kpi-roc-auc').textContent = m.roc_auc ? m.roc_auc.toFixed(4) : '--';
    container.querySelector('#kpi-precision').textContent = m.precision ? `${(m.precision * 100).toFixed(1)}%` : '--';
    container.querySelector('#kpi-recall').textContent = m.recall ? `${(m.recall * 100).toFixed(1)}%` : '--';
    container.querySelector('#kpi-threshold').textContent = data.threshold ? data.threshold.toFixed(2) : '0.77';

    container.querySelector('#cm-model-tag').textContent = data.model_version || 'v_latest';
    container.querySelector('#cm-tn').textContent = cm.tn?.toLocaleString() ?? '--';
    container.querySelector('#cm-fp').textContent = cm.fp?.toLocaleString() ?? '--';
    container.querySelector('#cm-fn').textContent = cm.fn?.toLocaleString() ?? '--';
    container.querySelector('#cm-tp').textContent = cm.tp?.toLocaleString() ?? '--';

    if (cm.fp !== undefined && cm.fn !== undefined) {
      const cost = 3.0 * cm.fp + 1.0 * cm.fn;
      container.querySelector('#cm-cost-val').textContent = `${cost.toLocaleString()} unidades de costo`;
    }
  } catch (err) {
    window.showToast?.(`No se pudieron cargar métricas: ${err.message}`, 'error');
  }
}
