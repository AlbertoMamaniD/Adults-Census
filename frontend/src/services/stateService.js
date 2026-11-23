/**
 * STATESERVICE.JS — Gestor de Estado Reactivo Simple
 * Controla pestaña activa, estado de autenticación y notificaciones toast.
 */

class StateService {
  constructor() {
    this.activeTab = 'predictor';
    this.systemOnline = false;
    this.activeModel = null;
    this.threshold = 0.77;
    this.listeners = [];
  }

  subscribe(listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  notify() {
    this.listeners.forEach(fn => fn(this));
  }

  setActiveTab(tabName) {
    this.activeTab = tabName;
    this.notify();
  }

  setSystemStatus(online, modelVersion = null, threshold = 0.77) {
    this.systemOnline = online;
    if (modelVersion) this.activeModel = modelVersion;
    if (threshold !== undefined && threshold !== null) this.threshold = threshold;
    this.notify();
  }
}

export const stateService = new StateService();
