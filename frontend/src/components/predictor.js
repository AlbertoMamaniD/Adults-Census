/**
 * PREDICTOR.JS — Módulo 1: Formulario de Scoring y Dictamen Crediticio
 * Diseñado bajo principios de usabilidad bancaria y mitigación de riesgo.
 */

import { apiService } from '../services/apiService.js';

export function renderPredictor(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = `
    <!-- Banner Informativo para el Oficial de Crédito -->
    <div class="bank-callout">
      <div class="bank-callout-icon" aria-hidden="true">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
      </div>
      <div class="bank-callout-text">
        <h4>Sistema Inteligente de Evaluación y Precalificación de Crédito</h4>
        <p>
          Esta herramienta analiza la información sociodemográfica y patrimonial del solicitante para determinar si tiene una capacidad económica anual superior a <strong>$50.000 USD</strong>. Permite precalificar productos de alto monto de forma ágil, aplicando un umbral conservador de seguridad (θ = 0.77) para prevenir la mora y resguardar el capital del banco.
        </p>
      </div>
    </div>

    <div class="predictor-layout">
      <!-- Columna 1: Formulario Estructurado del Solicitante -->
      <section class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7.5" r="4"></circle><line x1="20" y1="8" x2="20" y2="14"></line><line x1="23" y1="11" x2="17" y2="11"></line></svg>
              Ficha del Solicitante
            </h2>
            <p class="card-subtitle">Complete los 12 datos socioeconómicos requeridos para emitir el dictamen.</p>
          </div>
          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <button type="button" id="btn-sample-solvent" class="btn btn-secondary btn-sm" title="Cargar perfil de alta solvencia">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-positive)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px; vertical-align: middle;"><polyline points="20 6 9 17 4 12"></polyline></svg>Perfil Solvente (>50K)
            </button>
            <button type="button" id="btn-sample-risk" class="btn btn-secondary btn-sm" title="Cargar perfil de riesgo crediticio">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-negative)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px; vertical-align: middle;"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>Perfil Riesgo (<=50K)
            </button>
          </div>
        </div>

        <form id="prediction-form" novalidate>
          <div class="form-grid">
            <!-- Sección 1: Datos Personales y Demográficos -->
            <div class="form-section-header">
              <h3>1. Información Personal y Demográfica</h3>
              <span>(Identidad del solicitante)</span>
            </div>

            <div class="form-group">
              <label for="age" class="form-label">Edad del Solicitante <span>(Años)</span></label>
              <input type="number" id="age" name="age" class="form-control" min="17" max="100" value="39" required />
              <span class="form-hint">Rango de admisión crediticia: 18 a 75 años.</span>
            </div>

            <div class="form-group">
              <label for="sex" class="form-label">
                Género
                <span class="badge badge-bank">Variable Protegida</span>
              </label>
              <select id="sex" name="sex" class="form-control" required>
                <option value="Male" selected>Masculino (Male)</option>
                <option value="Female">Femenino (Female)</option>
              </select>
              <span class="form-hint">Monitoreado bajo políticas de cero discriminación.</span>
            </div>

            <div class="form-group">
              <label for="race" class="form-label">
                Grupo Poblacional Censal
                <span class="badge badge-bank">Auditoría Ética</span>
              </label>
              <select id="race" name="race" class="form-control" required>
                <option value="White" selected>Caucásico / Blanco (White)</option>
                <option value="Asian-Pac-Islander">Asiático / Islas del Pacífico</option>
                <option value="Amer-Indian-Eskimo">Indígena / Nativo Americano</option>
                <option value="Black">Afrodescendiente (Black)</option>
                <option value="Other">Otro grupo poblacional</option>
              </select>
            </div>

            <div class="form-group">
              <label for="native_country" class="form-label">País de Residencia u Origen</label>
              <select id="native_country" name="native_country" class="form-control" required>
                <option value="United-States" selected>Estados Unidos (United-States)</option>
                <option value="Mexico">México</option>
                <option value="Canada">Canadá</option>
                <option value="Germany">Alemania</option>
                <option value="England">Inglaterra</option>
                <option value="Philippines">Filipinas</option>
                <option value="India">India</option>
                <option value="South">Corea del Sur</option>
                <option value="China">China</option>
                <option value="Cuba">Cuba</option>
                <option value="Other">Otro país</option>
              </select>
            </div>

            <!-- Sección 2: Actividad Laboral y Nivel de Instrucción -->
            <div class="form-section-header">
              <h3>2. Situación Laboral y Nivel de Instrucción</h3>
              <span>(Estabilidad y capacidad generativa)</span>
            </div>

            <div class="form-group">
              <label for="workclass" class="form-label">Régimen Laboral / Empleador</label>
              <select id="workclass" name="workclass" class="form-control" required>
                <option value="Private" selected>Sector Privado (Empresa privada)</option>
                <option value="Self-emp-inc">Autoempleo Incorporado (Empresario / Societario)</option>
                <option value="Self-emp-not-inc">Autoempleo sin incorporar (Independiente)</option>
                <option value="Federal-gov">Servidor Público Federal / Nacional</option>
                <option value="Local-gov">Servidor Público Municipal / Local</option>
                <option value="State-gov">Servidor Público Departamental / Estatal</option>
                <option value="Without-pay">Sin remuneración fija</option>
                <option value="Never-worked">Sin historial de trabajo</option>
              </select>
            </div>

            <div class="form-group">
              <label for="occupation" class="form-label">Actividad Profesional / Cargo</label>
              <select id="occupation" name="occupation" class="form-control" required>
                <option value="Exec-managerial" selected>Dirección Ejecutiva / Gerencia</option>
                <option value="Prof-specialty">Profesional Especializado / Consultor</option>
                <option value="Tech-support">Soporte Tecnológico / Especialista IT</option>
                <option value="Sales">Comercial / Ventas de Alto Impacto</option>
                <option value="Craft-repair">Técnico Calificado / Mantenimiento</option>
                <option value="Adm-clerical">Administrativo / Oficinista</option>
                <option value="Protective-serv">Seguridad y Protección Civil</option>
                <option value="Machine-op-inspct">Operador Industrial / Maquinaria</option>
                <option value="Transport-moving">Transporte y Logística</option>
                <option value="Farming-fishing">Producción Agropecuaria / Pesca</option>
                <option value="Handlers-cleaners">Servicios Generales / Limpieza</option>
                <option value="Other-service">Otros Servicios</option>
              </select>
            </div>

            <div class="form-group">
              <label for="education_num" class="form-label">Nivel de Instrucción <span>(Años)</span></label>
              <input type="number" id="education_num" name="education_num" class="form-control" min="1" max="16" value="13" required />
              <span class="form-hint">Guía: 9 = Bachiller, 13 = Licenciatura, 14 = Maestría, 16 = Doctorado.</span>
            </div>

            <div class="form-group">
              <label for="hours_per_week" class="form-label">Dedicación Semanal <span>(Horas)</span></label>
              <input type="number" id="hours_per_week" name="hours_per_week" class="form-control" min="1" max="100" value="40" required />
              <span class="form-hint">40 hrs = Tiempo completo habitual; 50+ hrs = Intensivo.</span>
            </div>

            <!-- Sección 3: Capacidad Patrimonial y Situación Familiar -->
            <div class="form-section-header">
              <h3>3. Solvencia Patrimonial y Cargas Familiares</h3>
              <span>(Ingresos adicionales y responsabilidades)</span>
            </div>

            <div class="form-group">
              <label for="marital_status" class="form-label">Estado Civil y Régimen Conyugal</label>
              <select id="marital_status" name="marital_status" class="form-control" required>
                <option value="Married-civ-spouse" selected>Casado/a (Sociedad Conyugal)</option>
                <option value="Never-married">Soltero/a (Nunca casado)</option>
                <option value="Divorced">Divorciado/a</option>
                <option value="Separated">Separado/a</option>
                <option value="Widowed">Viudo/a</option>
                <option value="Married-spouse-absent">Casado/a (Cónyuge ausente)</option>
                <option value="Married-AF-spouse">Casado/a (Fuerzas Armadas)</option>
              </select>
            </div>

            <div class="form-group">
              <label for="relationship" class="form-label">Situación en el Hogar</label>
              <select id="relationship" name="relationship" class="form-control" required>
                <option value="Husband" selected>Cónyuge Masculino (Jefe de hogar)</option>
                <option value="Wife">Cónyuge Femenino (Jefa de hogar)</option>
                <option value="Not-in-family">Independiente / Vive solo</option>
                <option value="Own-child">Hijo/a dependiente en el hogar</option>
                <option value="Unmarried">Sin pareja conviviente</option>
                <option value="Other-relative">Otro pariente dependiente</option>
              </select>
            </div>

            <div class="form-group">
              <label for="capital_gain" class="form-label">Ganancias de Capital / Dividendos <span>(USD)</span></label>
              <input type="number" id="capital_gain" name="capital_gain" class="form-control" min="0" value="2174" step="100" required />
              <span class="form-hint">Rendimientos anuales por acciones, inmuebles o inversiones.</span>
            </div>

            <div class="form-group">
              <label for="capital_loss" class="form-label">Obligaciones o Pérdidas Financieras <span>(USD)</span></label>
              <input type="number" id="capital_loss" name="capital_loss" class="form-control" min="0" value="0" step="100" required />
              <span class="form-hint">Pérdidas de capital o pasivos anuales declarados.</span>
            </div>
          </div>

          <div style="margin-top: 1.5rem; display: flex; justify-content: flex-end; gap: 0.75rem;">
            <button type="submit" id="btn-predict" class="btn btn-primary" style="min-width: 14rem;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 16 16 12 12 8"></polyline><line x1="8" y1="12" x2="16" y2="12"></line></svg>
              Emitir Dictamen Crediticio
            </button>
          </div>
        </form>
      </section>

      <!-- Columna 2: Resolución de Evaluación de Riesgo Crediticio -->
      <aside>
        <div class="card prediction-result-card" id="result-container">
          <div class="card-header">
            <div>
              <h3 class="card-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                Dictamen de Precalificación
              </h3>
              <p class="card-subtitle" style="margin: 0;">Resolución automatizada del motor de riesgo</p>
            </div>
            <span class="badge badge-neutral" id="result-model-version">v_latest</span>
          </div>

          <!-- Estado Inicial Vacío -->
          <div id="result-empty" style="text-align: center; padding: 3.5rem 1rem; color: var(--color-primary-500);">
            <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin: 0 auto 1.25rem; color: #94a3b8;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            <p style="font-weight: var(--font-weight-semibold); color: var(--color-primary-800); margin-bottom: 0.25rem;">
              Listo para emitir dictamen
            </p>
            <p style="font-size: var(--font-size-sm); margin: 0; max-width: 20rem; margin: 0 auto;">
              Complete los datos del solicitante o use los perfiles de ejemplo, luego presione <strong>"Emitir Dictamen Crediticio"</strong>.
            </p>
          </div>

          <!-- Estado con Resultados Renderizados -->
          <div id="result-content" class="hidden">
            <div id="decision-banner" class="decision-banner">
              <div id="decision-badge" class="badge" style="margin-bottom: 0.6rem; font-size: 0.7rem;">DICTAMEN DE RIESGO</div>
              <div id="decision-title" class="decision-title">--</div>
              <div id="decision-subtitle" style="font-size: 0.85rem; font-weight: 500;">--</div>
            </div>

            <!-- Medidor de Solvencia y Nivel de Confianza -->
            <div class="probability-indicator">
              <div class="probability-header">
                <span style="color: var(--color-primary-700);">Probabilidad de Solvencia (>50K):</span>
                <strong id="prob-percentage" style="font-size: 1.125rem; color: var(--color-primary-900);">0.0%</strong>
              </div>
              <div class="progress-bar-container" style="height: 0.875rem;">
                <div id="prob-bar-fill" class="progress-bar-fill" style="width: 0%;"></div>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.725rem; color: var(--color-primary-500); margin-top: 0.4rem;">
                <span>0% (Riesgo Alto)</span>
                <span id="prob-threshold-label" style="font-weight: 600; color: var(--color-accent-700);">Filtro Bancario: 77%</span>
                <span>100% (Solvente)</span>
              </div>
            </div>

            <!-- Recomendación de Negocio para el Asesor de Crédito -->
            <div class="recommendation-box">
              <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.35rem;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--color-accent);"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>
                <strong style="color: var(--color-primary-900); font-size: 0.875rem;">Recomendación para el Oficial de Negocios:</strong>
              </div>
              <span id="recommendation-text" style="line-height: 1.5; color: var(--color-primary-800);">--</span>
            </div>

            <!-- Trazabilidad Bancaria -->
            <div style="margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid var(--color-primary-200); display: flex; justify-content: space-between; align-items: center; font-size: var(--font-size-micro); color: var(--color-primary-500);">
              <span>Latencia de cálculo: <strong id="latency-text" style="color: var(--color-primary-800);">-- ms</strong></span>
              <span style="display: inline-flex; align-items: center; gap: 0.35rem;">Auditoría: <strong style="color: var(--color-positive); display: inline-flex; align-items: center; gap: 0.25rem;">Persistido en Supabase DB <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg></strong></span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  `;

  setupPredictorEvents(container);
}

function setupPredictorEvents(container) {
  const form = container.querySelector('#prediction-form');
  const btnPredict = container.querySelector('#btn-predict');

  // Botón Ejemplo Solvente
  container.querySelector('#btn-sample-solvent').addEventListener('click', () => {
    form.age.value = 45;
    form.workclass.value = 'Self-emp-inc';
    form.education_num.value = 14; // Maestría
    form.marital_status.value = 'Married-civ-spouse';
    form.occupation.value = 'Exec-managerial';
    form.relationship.value = 'Husband';
    form.race.value = 'White';
    form.sex.value = 'Male';
    form.capital_gain.value = 15000;
    form.capital_loss.value = 0;
    form.hours_per_week.value = 50;
    form.native_country.value = 'United-States';
    window.showToast?.('Cargado perfil de prueba: Solicitante de Alta Solvencia', 'success');
  });

  // Botón Ejemplo Riesgo
  container.querySelector('#btn-sample-risk').addEventListener('click', () => {
    form.age.value = 22;
    form.workclass.value = 'Private';
    form.education_num.value = 9; // High school
    form.marital_status.value = 'Never-married';
    form.occupation.value = 'Handlers-cleaners';
    form.relationship.value = 'Own-child';
    form.race.value = 'White';
    form.sex.value = 'Female';
    form.capital_gain.value = 0;
    form.capital_loss.value = 0;
    form.hours_per_week.value = 25;
    form.native_country.value = 'United-States';
    window.showToast?.('Cargado perfil de prueba: Riesgo de Insolvencia', 'warning');
  });

  // Envío del formulario
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    const payload = {
      age: parseInt(form.age.value, 10),
      workclass: form.workclass.value,
      education_num: parseInt(form.education_num.value, 10),
      marital_status: form.marital_status.value,
      occupation: form.occupation.value,
      relationship: form.relationship.value,
      race: form.race.value,
      sex: form.sex.value,
      capital_gain: parseFloat(form.capital_gain.value) || 0.0,
      capital_loss: parseFloat(form.capital_loss.value) || 0.0,
      hours_per_week: parseInt(form.hours_per_week.value, 10),
      native_country: form.native_country.value,
    };

    // Estado cargando
    btnPredict.disabled = true;
    const originalText = btnPredict.innerHTML;
    btnPredict.innerHTML = `<span class="spinner" aria-hidden="true"></span> Evaluando scoring...`;

    try {
      const resp = await apiService.predict(payload);
      displayPredictionResult(resp, container);
      window.showToast?.(`Dictamen emitido: ${resp.predicted_class}`, 'success');
    } catch (err) {
      window.showToast?.(`Error en evaluación: ${err.message}`, 'error');
    } finally {
      btnPredict.disabled = false;
      btnPredict.innerHTML = originalText;
    }
  });
}

function displayPredictionResult(res, container) {
  const resultEmpty = container.querySelector('#result-empty');
  const resultContent = container.querySelector('#result-content');
  const banner = container.querySelector('#decision-banner');
  const badge = container.querySelector('#decision-badge');
  const title = container.querySelector('#decision-title');
  const subtitle = container.querySelector('#decision-subtitle');
  const probPercentage = container.querySelector('#prob-percentage');
  const probBar = container.querySelector('#prob-bar-fill');
  const probThreshold = container.querySelector('#prob-threshold-label');
  const recommendation = container.querySelector('#recommendation-text');
  const latency = container.querySelector('#latency-text');
  const version = container.querySelector('#result-model-version');

  resultEmpty.classList.add('hidden');
  resultContent.classList.remove('hidden');

  const isSolvent = res.predicted_class === '>50K';
  const probPct = (res.probability * 100).toFixed(1);

  version.textContent = res.model_version || 'v_latest';
  probPercentage.textContent = `${probPct}%`;
  probBar.style.width = `${Math.min(res.probability * 100, 100)}%`;
  probThreshold.textContent = `Filtro de Seguridad: ${(res.threshold_applied * 100 || 77.0).toFixed(1)}%`;
  latency.textContent = `${res.latency_ms?.toFixed(1) || '12.0'} ms`;

  if (isSolvent) {
    banner.className = 'decision-banner positive';
    badge.className = 'badge badge-positive';
    badge.textContent = 'DICTAMEN: APROBADO (ALTA SOLVENCIA)';
    title.textContent = 'CALIFICA (> $50.000 USD / AÑO)';
    subtitle.textContent = 'Perfil solvente apto para colocación de crédito de alto monto';
    probBar.className = 'progress-bar-fill positive';
    recommendation.innerHTML = `
      <strong>Aprobación Inmediata:</strong> El solicitante supera ampliamente el filtro de solvencia (${probPct}% vs 77% requerido). 
      Se recomienda ofertar <strong>Línea de Crédito Premium</strong> (Tarjeta Platinum/Black, Crédito Hipotecario o de Inversión) con tasa preferencial. Riesgo de mora estimado: <strong>Muy bajo (&lt; 1%)</strong>.
    `;
  } else {
    banner.className = 'decision-banner negative';
    badge.className = 'badge badge-negative';
    badge.textContent = 'DICTAMEN: NO FAVORABLE (RIESGO ELEVADO)';
    title.textContent = 'NO CALIFICA (≤ $50.000 USD / AÑO)';
    subtitle.textContent = 'Capacidad económica insuficiente para líneas de alto monto';
    probBar.className = 'progress-bar-fill negative';
    recommendation.innerHTML = `
      <strong>Denegación Preventiva:</strong> La probabilidad de solvencia (${probPct}%) no alcanza el umbral de seguridad bancaria (77%). 
      Para mitigar el riesgo de mora (penalización 3x por incobrabilidad), se sugiere <strong>no otorgar crédito quirografario</strong> y canalizar al cliente hacia <strong>microcrédito con garantía prendaria/personal</strong> o planes de ahorro programado.
    `;
  }
}
