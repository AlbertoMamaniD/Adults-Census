/**
 * SETUP.JS — Mock de Entorno de Navegador para Pruebas Unitarias de Frontend
 * Simula Window, Document, LocalStorage y Fetch en Node.js sin dependencias externas.
 */

class MockClassList {
  constructor(el) {
    this.el = el;
    this.classes = new Set();
  }
  add(...cls) {
    cls.forEach(c => { if (c) this.classes.add(c); });
    this.el.className = Array.from(this.classes).join(' ');
  }
  remove(...cls) {
    cls.forEach(c => { if (c) this.classes.delete(c); });
    this.el.className = Array.from(this.classes).join(' ');
  }
  contains(c) {
    return this.classes.has(c);
  }
  toggle(c) {
    if (this.contains(c)) { this.remove(c); return false; }
    else { this.add(c); return true; }
  }
}

export class MockElement {
  constructor(tagName = 'div', id = '') {
    this.tagName = tagName.toUpperCase();
    this.id = id;
    this.className = '';
    this.classList = new MockClassList(this);
    this.attributes = {};
    if (id) this.attributes.id = id;
    this.children = [];
    this._innerHTML = '';
    this.textContent = '';
    this.value = '';
    this.disabled = false;
    this.style = {};
    this.eventListeners = {};
  }

  setAttribute(k, v) {
    this.attributes[k] = String(v);
    if (k === 'id') this.id = v;
    if (k === 'class') {
      this.className = v;
      v.split(/\s+/).filter(Boolean).forEach(c => this.classList.add(c));
    }
  }

  getAttribute(k) {
    return this.attributes[k] !== undefined ? this.attributes[k] : null;
  }

  removeAttribute(k) {
    delete this.attributes[k];
  }

  addEventListener(event, fn) {
    if (!this.eventListeners[event]) this.eventListeners[event] = [];
    this.eventListeners[event].push(fn);
  }

  dispatchEvent(event) {
    const eventType = typeof event === 'string' ? event : event.type;
    const handlers = this.eventListeners[eventType] || [];
    const evt = typeof event === 'string' ? { type: event, target: this } : { target: this, ...event };
    handlers.forEach(fn => fn(evt));
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  set innerHTML(html) {
    this._innerHTML = html;
    this._parseHTML(html);
  }

  get innerHTML() {
    return this._innerHTML;
  }

  _parseHTML(html) {
    // 1. Extraer elementos con ID explícito
    const idRegex = /<([a-zA-Z0-9-]+)[^>]*\bid=["']([^"']+)["'][^>]*>/g;
    let match;
    while ((match = idRegex.exec(html)) !== null) {
      const tag = match[1];
      const id = match[2];
      let existing = globalThis.document.getElementById(id);
      if (!existing) {
        existing = new MockElement(tag, id);
        globalThis.document._registerElement(existing);
      }
      this.children.push(existing);
    }

    // 2. Extraer botones de tabs de navegación
    const tabRegex = /<button[^>]*class=["']([^"']*)["'][^>]*data-tab=["']([^"']+)["'][^>]*>/g;
    while ((match = tabRegex.exec(html)) !== null) {
      const btn = new MockElement('button');
      btn.className = match[1];
      btn.setAttribute('data-tab', match[2]);
      btn.classList.add(...match[1].split(/\s+/).filter(Boolean));
      this.children.push(btn);
    }
  }

  querySelector(sel) {
    if (sel.startsWith('#')) {
      const targetId = sel.slice(1);
      if (this.id === targetId) return this;
      return this.children.find(c => c.id === targetId) || globalThis.document.getElementById(targetId);
    }
    if (sel.startsWith('.')) {
      const cls = sel.slice(1);
      if (this.classList.contains(cls)) return this;
      return this.children.find(c => c.classList.contains(cls)) || null;
    }
    return this.children.find(c => c.tagName.toLowerCase() === sel.toLowerCase()) || null;
  }

  querySelectorAll(sel) {
    const results = [];
    if (sel.startsWith('.')) {
      const cls = sel.slice(1);
      this.children.forEach(c => {
        if (c.classList.contains(cls)) results.push(c);
      });
    } else if (sel.includes('nav-tab-btn')) {
      this.children.forEach(c => {
        if (c.getAttribute('data-tab') || c.classList.contains('nav-tab-btn')) {
          results.push(c);
        }
      });
    }
    return results;
  }
}

class MockDocument {
  constructor() {
    this.elementsById = new Map();
    this.body = new MockElement('body');
  }

  _registerElement(el) {
    if (el.id) {
      this.elementsById.set(el.id, el);
    }
  }

  getElementById(id) {
    return this.elementsById.get(id) || null;
  }

  createElement(tag) {
    return new MockElement(tag);
  }

  querySelector(sel) {
    if (sel.startsWith('#')) return this.getElementById(sel.slice(1));
    return null;
  }

  reset() {
    this.elementsById.clear();
    this.body = new MockElement('body');
  }
}

class MockLocalStorage {
  constructor() {
    this.store = {};
  }
  getItem(k) {
    return this.store[k] || null;
  }
  setItem(k, v) {
    this.store[k] = String(v);
  }
  removeItem(k) {
    delete this.store[k];
  }
  clear() {
    this.store = {};
  }
}

// Configurar entorno global antes de que se importen servicios
export function setupBrowserEnvironment() {
  globalThis.window = {
    location: {
      origin: 'http://127.0.0.1:3000',
    },
    showToast: (msg, type) => {},
    openLoginModal: () => {},
  };

  globalThis.document = new MockDocument();
  globalThis.localStorage = new MockLocalStorage();
}

// Inicializar inmediatamente al importar setup.js
setupBrowserEnvironment();
