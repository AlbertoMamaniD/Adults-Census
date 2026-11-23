/**
 * APISERVICE.JS — Cliente HTTP & WebSocket Desacoplado
 * Gestiona endpoints, cabeceras JWT, control de timeout y reconexión WebSocket.
 */

export function getApiBaseUrl() {
  if (typeof window !== 'undefined' && window.API_BASE_URL) {
    return window.API_BASE_URL;
  }
  if (typeof window !== 'undefined' && window.location && window.location.hostname) {
    const proto = window.location.protocol === 'https:' ? 'https:' : 'http:';
    const host = window.location.hostname;
    if (window.location.port === '8000') {
      return window.location.origin;
    }
    return `${proto}//${host}:8000`;
  }
  return 'http://127.0.0.1:8000';
}

export function getWsBaseUrl() {
  return getApiBaseUrl().replace(/^https:/, 'wss:').replace(/^http:/, 'ws:');
}

export const API_BASE_URL = getApiBaseUrl();
export const WS_BASE_URL = getWsBaseUrl();
const DEFAULT_TIMEOUT_MS = 15000;

class ApiService {
  constructor() {
    this.token = typeof localStorage !== 'undefined' ? localStorage.getItem('precal_auth_token') : null;
    this.ws = null;
  }

  setToken(token) {
    this.token = token;
    if (typeof localStorage !== 'undefined') {
      if (token) {
        localStorage.setItem('precal_auth_token', token);
      } else {
        localStorage.removeItem('precal_auth_token');
      }
    }
  }

  getToken() {
    return this.token;
  }

  isAuthenticated() {
    return Boolean(this.token);
  }

  async _request(endpoint, options = {}) {
    const baseUrl = getApiBaseUrl();
    const url = `${baseUrl}${endpoint}`;
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
      timeout: 180000, // 3 minutos para permitir pipeline completo de reentrenamiento
    });
  }

  // 8. Conexión WebSocket para Reentrenamiento (Autenticación en banda para proteger credenciales)
  connectWebSocket(onMessage, onError, onClose) {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      this.ws.close();
    }

    const wsUrl = `${getWsBaseUrl()}/ws/retrain`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      if (this.token) {
        try {
          this.ws.send(JSON.stringify({ type: 'auth', token: this.token }));
        } catch (e) {
          console.warn('[WS] Error enviando credenciales en banda:', e);
        }
      }
    };

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
