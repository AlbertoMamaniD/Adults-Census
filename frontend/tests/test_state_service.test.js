/**
 * TEST_STATE_SERVICE.TEST.JS — Pruebas Unitarias del Gestor de Estado Reactivo
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { setupBrowserEnvironment } from './setup.js';

setupBrowserEnvironment();
import { stateService } from '../src/services/stateService.js';

describe('StateService — Gestor de Estado Reactivo', () => {
  beforeEach(() => {
    stateService.activeTab = 'predictor';
    stateService.systemOnline = false;
    stateService.activeModel = null;
    stateService.threshold = 0.77;
    stateService.listeners = [];
  });

  it('1. Debe inicializarse con la pestaña predictor y umbral 0.77', () => {
    assert.equal(stateService.activeTab, 'predictor');
    assert.equal(stateService.systemOnline, false);
    assert.equal(stateService.threshold, 0.77);
    assert.equal(stateService.activeModel, null);
  });

  it('2. Debe permitir cambiar de pestaña y notificar a los observadores', () => {
    let notified = false;
    let observedTab = null;

    const unsubscribe = stateService.subscribe((state) => {
      notified = true;
      observedTab = state.activeTab;
    });

    stateService.setActiveTab('metrics');

    assert.equal(notified, true);
    assert.equal(observedTab, 'metrics');
    assert.equal(stateService.activeTab, 'metrics');

    unsubscribe();
  });

  it('3. Debe desuscribir correctamente a un observador', () => {
    let callCount = 0;
    const unsubscribe = stateService.subscribe(() => {
      callCount++;
    });

    stateService.setActiveTab('history');
    assert.equal(callCount, 1);

    unsubscribe();
    stateService.setActiveTab('retrain');
    assert.equal(callCount, 1, 'No debe notificar tras desuscribirse');
  });

  it('4. Debe actualizar el estado de conectividad del sistema, modelo y umbral', () => {
    let reportedOnline = null;
    let reportedModel = null;

    stateService.subscribe((state) => {
      reportedOnline = state.systemOnline;
      reportedModel = state.activeModel;
    });

    stateService.setSystemStatus(true, 'v20261117002816', 0.77);

    assert.equal(stateService.systemOnline, true);
    assert.equal(stateService.activeModel, 'v20261117002816');
    assert.equal(stateService.threshold, 0.77);
    assert.equal(reportedOnline, true);
    assert.equal(reportedModel, 'v20261117002816');
  });
});
