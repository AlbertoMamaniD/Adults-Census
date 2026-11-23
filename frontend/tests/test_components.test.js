/**
 * TEST_COMPONENTS.TEST.JS — Pruebas Unitarias de Renderizado de Componentes
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { setupBrowserEnvironment, MockElement } from './setup.js';

setupBrowserEnvironment();
import { renderNavbar } from '../src/components/navbar.js';
import { renderPredictor } from '../src/components/predictor.js';
import { renderMetricsDashboard, loadMetricsData } from '../src/components/metricsDashboard.js';
import { apiService } from '../src/services/apiService.js';
import { renderHistoryTable } from '../src/components/historyTable.js';
import { renderRetrainCenter } from '../src/components/retrainCenter.js';

describe('Componentes del Frontend — Pruebas de Renderizado e Inyección DOM', () => {
  beforeEach(() => {
    globalThis.document.reset();
  });

  it('1. renderNavbar debe renderizar el encabezado y las 4 pestañas de navegación', () => {
    const root = new MockElement('header', 'navbar-root');
    globalThis.document._registerElement(root);

    renderNavbar('navbar-root');

    assert.ok(root.innerHTML.includes('Precalificación Crediticia'));
    assert.ok(root.innerHTML.includes('CRISP-ML(Q)'));
    assert.ok(globalThis.document.getElementById('system-status-pill') !== null);
    assert.ok(globalThis.document.getElementById('auth-btn') !== null);

    const tabs = root.querySelectorAll('nav-tab-btn');
    assert.equal(tabs.length, 4, 'Debe haber exactamente 4 pestañas de navegación');
  });

  it('2. renderPredictor debe renderizar los 12 campos censales y botones de ejemplo', () => {
    const root = new MockElement('section', 'tab-predictor');
    globalThis.document._registerElement(root);

    renderPredictor('tab-predictor');

    assert.ok(globalThis.document.getElementById('prediction-form') !== null);
    assert.ok(globalThis.document.getElementById('btn-sample-solvent') !== null);
    assert.ok(globalThis.document.getElementById('btn-sample-risk') !== null);
    assert.ok(globalThis.document.getElementById('btn-predict') !== null);

    // Verificar las 12 características requeridas
    const requiredFields = [
      'age', 'workclass', 'education_num', 'marital_status',
      'occupation', 'relationship', 'race', 'sex',
      'capital_gain', 'capital_loss', 'hours_per_week', 'native_country'
    ];

    requiredFields.forEach(field => {
      assert.ok(globalThis.document.getElementById(field) !== null, `Debe existir el input para '${field}'`);
    });
  });

  it('3. renderMetricsDashboard debe renderizar las tarjetas KPI y la matriz de confusión', () => {
    const root = new MockElement('section', 'tab-metrics');
    globalThis.document._registerElement(root);

    renderMetricsDashboard('tab-metrics');

    assert.ok(globalThis.document.getElementById('kpi-mcc') !== null);
    assert.ok(globalThis.document.getElementById('kpi-roc-auc') !== null);
    assert.ok(globalThis.document.getElementById('kpi-precision') !== null);
    assert.ok(globalThis.document.getElementById('kpi-recall') !== null);
    assert.ok(globalThis.document.getElementById('kpi-threshold') !== null);

    // Celdas de la matriz de confusión
    assert.ok(globalThis.document.getElementById('cm-tn') !== null);
    assert.ok(globalThis.document.getElementById('cm-fp') !== null);
    assert.ok(globalThis.document.getElementById('cm-fn') !== null);
    assert.ok(globalThis.document.getElementById('cm-tp') !== null);
  });

  it('4. renderHistoryTable debe renderizar la tabla, estado no autenticado y paginación', () => {
    const root = new MockElement('section', 'tab-history');
    globalThis.document._registerElement(root);

    renderHistoryTable('tab-history');

    assert.ok(globalThis.document.getElementById('history-tbody') !== null);
    assert.ok(globalThis.document.getElementById('history-unauth') !== null);
    assert.ok(globalThis.document.getElementById('btn-refresh-history') !== null);
    assert.ok(globalThis.document.getElementById('btn-prev-page') !== null);
    assert.ok(globalThis.document.getElementById('btn-next-page') !== null);
  });

  it('5. renderRetrainCenter debe renderizar el uploader drag & drop, consola WS y botón de acción', () => {
    const root = new MockElement('section', 'tab-retrain');
    globalThis.document._registerElement(root);

    renderRetrainCenter('tab-retrain');

    assert.ok(globalThis.document.getElementById('csv-dropzone') !== null);
    assert.ok(globalThis.document.getElementById('csv-file-input') !== null);
    assert.ok(globalThis.document.getElementById('btn-start-retrain') !== null);
    assert.ok(globalThis.document.getElementById('ws-terminal') !== null);
    assert.ok(globalThis.document.getElementById('retrain-progress-bar') !== null);
    assert.ok(globalThis.document.getElementById('ws-status-badge') !== null);
  });

  it('6. loadMetricsData debe mostrar 0.0% en métricas legítimas de valor cero (Qodo Finding 2)', async () => {
    const root = new MockElement('section', 'tab-metrics');
    globalThis.document._registerElement(root);
    renderMetricsDashboard('tab-metrics');

    // Simular respuesta del backend con métricas válidas en cero
    const originalGetMetrics = apiService.getMetrics;
    apiService.getMetrics = async () => ({
      model_version: 'v_zero_test',
      threshold: 0.50,
      metrics: {
        mcc: 0.0,
        roc_auc: 0.50,
        precision: 0.0,
        recall: 0.0,
        confusion_matrix: { tn: 100, fp: 0, fn: 50, tp: 0 }
      }
    });

    try {
      await loadMetricsData(root);

      const elPrec = root.querySelector('#kpi-precision');
      const elMcc = root.querySelector('#kpi-mcc');
      const elRecall = root.querySelector('#kpi-recall');

      assert.strictEqual(elPrec.textContent, '0.0%');
      assert.strictEqual(elMcc.textContent, '0.0000');
      assert.strictEqual(elRecall.textContent, '0.0%');
    } finally {
      apiService.getMetrics = originalGetMetrics;
    }
  });

  it('7. loadMetricsData debe calcular evaluaciones dinámicas en la matriz de confusión (Qodo Finding 9)', async () => {
    const root = new MockElement('section', 'tab-metrics');
    globalThis.document._registerElement(root);
    renderMetricsDashboard('tab-metrics');

    const originalGetMetrics = apiService.getMetrics;
    apiService.getMetrics = async () => ({
      model_version: 'v_eval_test',
      threshold: 0.65,
      metrics: {
        mcc: 0.60,
        roc_auc: 0.91,
        precision: 0.75,
        recall: 0.60,
        confusion_matrix: { tn: 1500, fp: 100, fn: 200, tp: 700 }
      }
    });

    try {
      await loadMetricsData(root);

      const elTitle = root.querySelector('#cm-eval-title');
      assert.strictEqual(elTitle.textContent, `Matriz de Rendimiento Crediticio (${(2500).toLocaleString()} Clientes Evaluados)`);
      assert.match(elTitle.textContent, /Matriz de Rendimiento Crediticio \(2[.,\s]?500 Clientes Evaluados\)/);
    } finally {
      apiService.getMetrics = originalGetMetrics;
    }
  });
});
