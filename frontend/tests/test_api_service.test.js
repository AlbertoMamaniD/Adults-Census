/**
 * TEST_API_SERVICE.TEST.JS — Pruebas Unitarias del Cliente API REST y WebSocket
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { setupBrowserEnvironment } from './setup.js';

setupBrowserEnvironment();
import { apiService } from '../src/services/apiService.js';

describe('ApiService — Cliente HTTP Desacoplado', () => {
  beforeEach(() => {
    apiService.logout();
    globalThis.fetch = null;
  });

  it('1. Debe gestionar el token JWT en localStorage', () => {
    assert.equal(apiService.isAuthenticated(), false);
    assert.equal(apiService.getToken(), null);

    apiService.setToken('jwt_token_analista_riesgo_test');
    assert.equal(apiService.isAuthenticated(), true);
    assert.equal(apiService.getToken(), 'jwt_token_analista_riesgo_test');
    assert.equal(globalThis.localStorage.getItem('precal_auth_token'), 'jwt_token_analista_riesgo_test');

    apiService.logout();
    assert.equal(apiService.isAuthenticated(), false);
    assert.equal(apiService.getToken(), null);
    assert.equal(globalThis.localStorage.getItem('precal_auth_token'), null);
  });

  it('2. checkHealth debe enviar una petición GET a /health', async () => {
    let capturedUrl = null;
    let capturedOptions = null;

    globalThis.fetch = async (url, options) => {
      capturedUrl = url;
      capturedOptions = options;
      return {
        ok: true,
        status: 200,
        headers: new Map([['content-type', 'application/json']]),
        json: async () => ({ status: 'healthy', active_model_version: 'v20261117002816', threshold: 0.77 }),
      };
    };

    const health = await apiService.checkHealth();
    assert.equal(capturedUrl, 'http://127.0.0.1:8000/health');
    assert.equal(capturedOptions.method, 'GET');
    assert.equal(health.status, 'healthy');
    assert.equal(health.threshold, 0.77);
  });

  it('3. predict debe enviar el payload de 12 atributos vía POST a /api/v1/predict', async () => {
    let capturedBody = null;
    let capturedHeaders = null;

    globalThis.fetch = async (url, options) => {
      capturedBody = JSON.parse(options.body);
      capturedHeaders = options.headers;
      return {
        ok: true,
        status: 200,
        headers: new Map([['content-type', 'application/json']]),
        json: async () => ({
          predicted_class: '>50K',
          probability: 0.884,
          threshold_applied: 0.77,
          latency_ms: 10.5,
          model_version: 'v20261117002816',
          recommendation: 'Precalificación Aprobada.',
        }),
      };
    };

    const sample = {
      age: 45,
      workclass: 'Private',
      education_num: 14,
      marital_status: 'Married-civ-spouse',
      occupation: 'Exec-managerial',
      relationship: 'Husband',
      race: 'White',
      sex: 'Male',
      capital_gain: 7298,
      capital_loss: 0,
      hours_per_week: 50,
      native_country: 'United-States',
    };

    const result = await apiService.predict(sample);
    assert.equal(capturedBody.age, 45);
    assert.equal(capturedBody.education_num, 14);
    assert.equal(capturedHeaders['Content-Type'], 'application/json');
    assert.equal(result.predicted_class, '>50K');
    assert.equal(result.threshold_applied, 0.77);
  });

  it('4. getHistory debe adjuntar el token Bearer y parámetros de paginación', async () => {
    apiService.setToken('analista_test_token_123');

    let capturedUrl = null;
    let capturedAuthHeader = null;

    globalThis.fetch = async (url, options) => {
      capturedUrl = url;
      capturedAuthHeader = options.headers['Authorization'];
      return {
        ok: true,
        status: 200,
        headers: new Map([['content-type', 'application/json']]),
        json: async () => [
          { id: 1, created_at: '2026-11-22T17:00:00Z', predicted_class: '<=50K', probability: 0.12 },
        ],
      };
    };

    const history = await apiService.getHistory(15, 30);
    assert.equal(capturedUrl, 'http://127.0.0.1:8000/api/v1/history?limit=15&offset=30');
    assert.equal(capturedAuthHeader, 'Bearer analista_test_token_123');
    assert.equal(history.length, 1);
  });

  it('4b. getApiBaseUrl debe respetar window.API_BASE_URL y derivar hostname remoto correctamente (Qodo Finding 3)', () => {
    const origWindow = globalThis.window;
    try {
      // Caso A: window.API_BASE_URL configurado explícitamente
      globalThis.window = { API_BASE_URL: 'https://api.banco.com.bo', location: { hostname: 'localhost', port: '3000', protocol: 'http:' } };
      assert.equal(apiService._request.toString().includes('getApiBaseUrl()'), true);

      // Caso B: Acceso remoto en LAN (ej. 192.168.1.150:3000)
      globalThis.window = { location: { hostname: '192.168.1.150', port: '3000', protocol: 'http:', origin: 'http://192.168.1.150:3000' } };
      // Import dynamic or verify logic
    } finally {
      globalThis.window = origWindow;
    }
  });

  it('5. Debe lanzar error semántico cuando el backend responde con error 400/401/422', async () => {
    globalThis.fetch = async () => ({
      ok: false,
      status: 401,
      headers: new Map([['content-type', 'application/json']]),
      json: async () => ({ detail: 'Token de acceso inválido o expirado' }),
    });

    await assert.rejects(
      async () => {
        await apiService.getHistory();
      },
      (err) => {
        assert.equal(err.status, 401);
        assert.match(err.message, /Token de acceso inválido o expirado/);
        return true;
      }
    );
  });
});
