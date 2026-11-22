/**
 * APISERVICE.JS — Cliente HTTP & WebSocket Desacoplado
 * Gestiona endpoints, cabeceras JWT, control de timeout y reconexión WebSocket.
 */

const API_BASE_URL = window.location.origin.includes(':3000') || window.location.origin.includes(':5500')
  ? 'http://127.0.0.1:8000'
  : (window.API_BASE_URL || 'http://127.0.0.1:8000');

const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');
const DEFAULT_TIMEOUT_MS = 15000;

class ApiService {
  constructor() {
    this.token = localStorage.getItem('precal_auth_token') || null;
    this.ws = null;
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('precal_auth_token', token);
    } else {
      localStorage.removeItem('precal_auth_token');
    }
  }

  getToken() {
    return this.token;
  }

  isAuthenticated() {
    return Boolean(this.token);
  }

  async _request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
      'Accept': 'application/json',
      ...(options.headers || {}),
    };

    if (this.token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    if (options.body && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(options.body);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || DEFAULT_TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      const contentType = response.headers.get('content-type') || '';
      let data = null;
      if (contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        const errorMsg = data?.detail || `Error HTTP ${response.status}: ${response.statusText}`;
        const error = new Error(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
        error.status = response.status;
        error.data = data;
        throw error;
      }

      return data;
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        throw new Error('Tiempo de espera agotado. Verifique que el servidor backend esté en ejecución.');
      }
      throw err;
    }
  }

  // 1. Verificación de Salud
  async checkHealth() {
    return this._request('/health', { method: 'GET' });
  }

  // 2. Autenticación JWT
  async login(username, password) {
    const data = await this._request('/api/v1/auth/login', {
      method: 'POST',
      body: { username, password },
    });
    if (data && data.access_token) {
      this.setToken(data.access_token);
    }
    return data;
  }

  logout() {
    this.setToken(null);
  }

  // 3. Inferencia Predictiva
  async predict(candidateData) {
    return this._request('/api/v1/predict', {
      method: 'POST',
      body: candidateData,
    });
  }

  // 4. Métricas del Modelo Activo
  async getMetrics() {
    return this._request('/api/v1/metrics', { method: 'GET' });
  }

  // 5. Historial de Predicciones
  async getHistory(limit = 20, offset = 0, modelVersion = null) {
    let query = `?limit=${limit}&offset=${offset}`;
    if (modelVersion) {
      query += `&model_version=${encodeURIComponent(modelVersion)}`;
    }
    return this._request(`/api/v1/history${query}`, { method: 'GET' });
  }

  // 6. Subida de Dataset CSV
  async uploadDataset(file) {
    const formData = new FormData();
    formData.append('file', file);
    return this._request('/api/v1/train/upload', {
      method: 'POST',
      body: formData,
      timeout: 60000, // 60 segundos para subidas de archivos
    });
  }

  // 7. Disparo de Re-entrenamiento
  async triggerRetrain(datasetId = null) {
    const body = datasetId ? { dataset_id: datasetId } : {};
    return this._request('/api/v1/retrain', {
      method: 'POST',
      body,
    });
  }

  // 8. Conexión WebSocket para Reentrenamiento
  connectWebSocket(onMessage, onError, onClose) {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      this.ws.close();
    }

    let wsUrl = `${WS_BASE_URL}/ws/retrain`;
    if (this.token) {
      wsUrl += `?token=${encodeURIComponent(this.token)}`;
    }

    this.ws = new WebSocket(wsUrl);

    this.ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (onMessage) onMessage(payload);
      } catch (err) {
        if (onMessage) onMessage({ stage: 'raw', message: event.data });
      }
    };

    this.ws.onerror = (err) => {
      console.warn('[WS] Error en la conexión:', err);
      if (onError) onError(err);
    };

    this.ws.onclose = (event) => {
      if (onClose) onClose(event);
    };

    return this.ws;
  }

  closeWebSocket() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const apiService = new ApiService();
