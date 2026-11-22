/**
 * PREDICTOR.JS — Módulo 1: Formulario de Inferencia y Tarjeta de Decisión Crediticia
 */

import { apiService } from '../services/apiService.js';

export function renderPredictor(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = `
    <div class="predictor-layout">
      <!-- Columna 1: Formulario de Datos Censales -->
      <section class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7.5" r="4"></circle><line x1="20" y1="8" x2="20" y2="14"></line><line x1="23" y1="11" x2="17" y2="11"></line></svg>
              Datos del Solicitante
            </h2>
            <p class="card-subtitle">Ingrese las 12 características demográficas y laborales para precalificación.</p>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <button type="button" id="btn-sample-solvent" class="btn btn-secondary btn-sm" title="Cargar perfil de alta solvencia">
              Ejemplo Solvente (>50K)
            </button>
            <button type="button" id="btn-sample-risk" class="btn btn-secondary btn-sm" title="Cargar perfil de riesgo">
              Ejemplo Riesgo (<=50K)
            </button>
          </div>
        </div>

        <form id="prediction-form" novalidate>
          <div class="form-grid">
            <div class="form-group">
              <label for="age" class="form-label">Edad <span>(Años)</span></label>
              <input type="number" id="age" name="age" class="form-control" min="17" max="100" value="39" required />
            </div>

            <div class="form-group">
              <label for="workclass" class="form-label">Sector Laboral (Workclass)</label>
              <select id="workclass" name="workclass" class="form-control" required>
                <option value="Private" selected>Sector Privado (Private)</option>
                <option value="Self-emp-not-inc">Autoempleo sin incorporar</option>
                <option value="Self-emp-inc">Autoempleo incorporado (Empresario)</option>
                <option value="Federal-gov">Gobierno Federal</option>
                <option value="Local-gov">Gobierno Local</option>
                <option value="State-gov">Gobierno Estatal</option>
                <option value="Without-pay">Sin remuneración</option>
                <option value="Never-worked">Nunca ha trabajado</option>
              </select>
            </div>

            <div class="form-group">
              <label for="education_num" class="form-label">Años de Educación <span>(1 - 16)</span></label>
              <input type="number" id="education_num" name="education_num" class="form-control" min="1" max="16" value="13" required />
              <span class="form-hint">13 = Licenciatura (Bachelors), 14 = Maestría, 16 = Doctorado</span>
            </div>

            <div class="form-group">
              <label for="marital_status" class="form-label">Estado Civil</label>
              <select id="marital_status" name="marital_status" class="form-control" required>
                <option value="Married-civ-spouse" selected>Casado/a (Cónyuge civil)</option>
                <option value="Never-married">Soltero/a (Nunca casado)</option>
                <option value="Divorced">Divorciado/a</option>
                <option value="Separated">Separado/a</option>
                <option value="Widowed">Viudo/a</option>
                <option value="Married-spouse-absent">Casado/a (Cónyuge ausente)</option>
                <option value="Married-AF-spouse">Casado/a (Fuerzas Armadas)</option>
              </select>
            </div>

            <div class="form-group">
              <label for="occupation" class="form-label">Ocupación / Cargo</label>
              <select id="occupation" name="occupation" class="form-control" required>
                <option value="Exec-managerial" selected>Ejecutivo / Gerencial</option>
                <option value="Prof-specialty">Profesional Especializado</option>
                <option value="Tech-support">Soporte Técnico</option>
                <option value="Sales">Ventas Comerciales</option>
                <option value="Craft-repair">Artesanía / Reparación técnica</option>
                <option value="Adm-clerical">Administrativo / Oficinista</option>
                <option value="Farming-fishing">Agricultura / Pesca</option>
                <option value="Transport-moving">Transporte / Logística</option>
                <option value="Handlers-cleaners">Manipuladores / Limpieza</option>
                <option value="Machine-op-inspct">Operador de Maquinaria</option>
                <option value="Protective-serv">Servicios de Protección</option>
                <option value="Other-service">Otros Servicios</option>
              </select>
            </div>

            <div class="form-group">
              <label for="relationship" class="form-label">Rol Familiar (Relationship)</label>
              <select id="relationship" name="relationship" class="form-control" required>
                <option value="Husband" selected>Esposo (Husband)</option>
                <option value="Wife">Esposa (Wife)</option>
                <option value="Not-in-family">Independiente (Not-in-family)</option>
                <option value="Own-child">Hijo/a en el hogar (Own-child)</option>
                <option value="Unmarried">Sin pareja conviviente</option>
                <option value="Other-relative">Otro pariente</option>
              </select>
            </div>

            <div class="form-group">
              <label for="race" class="form-label">Grupo Poblacional (Race)</label>
              <select id="race" name="race" class="form-control" required>
                <option value="White" selected>White</option>
                <option value="Asian-Pac-Islander">Asian-Pac-Islander</option>
                <option value="Amer-Indian-Eskimo">Amer-Indian-Eskimo</option>
                <option value="Black">Black</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <div class="form-group">
              <label for="sex" class="form-label">Género</label>
              <select id="sex" name="sex" class="form-control" required>
                <option value="Male" selected>Masculino (Male)</option>
                <option value="Female">Femenino (Female)</option>
              </select>
            </div>

            <div class="form-group">
              <label for="capital_gain" class="form-label">Ganancia de Capital <span>(USD)</span></label>
              <input type="number" id="capital_gain" name="capital_gain" class="form-control" min="0" value="2174" step="100" required />
            </div>

            <div class="form-group">
              <label for="capital_loss" class="form-label">Pérdida de Capital <span>(USD)</span></label>
              <input type="number" id="capital_loss" name="capital_loss" class="form-control" min="0" value="0" step="100" required />
            </div>

            <div class="form-group">
              <label for="hours_per_week" class="form-label">Horas Semanales de Trabajo</label>
              <input type="number" id="hours_per_week" name="hours_per_week" class="form-control" min="1" max="100" value="40" required />
            </div>

            <div class="form-group">
              <label for="native_country" class="form-label">País de Origen</label>
              <select id="native_country" name="native_country" class="form-control" required>
                <option value="United-States" selected>United-States</option>
                <option value="Bolivia">Bolivia</option>
                <option value="Mexico">Mexico</option>
                <option value="Canada">Canada</option>
                <option value="Germany">Germany</option>
                <option value="England">England</option>
                <option value="Other">Otro País</option>
              </select>
            </div>
          </div>

          <div style="margin-top: 1.5rem; display: flex; justify-content: flex-end;">
            <button type="submit" id="btn-predict" class="btn btn-primary" style="min-width: 12rem;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 16 16 12 12 8"></polyline><line x1="8" y1="12" x2="16" y2="12"></line></svg>
              Evaluar Solicitud
            </button>
          </div>
        </form>
      </section>

      <!-- Columna 2: Resultado de la Evaluación en Tiempo Real -->
      <aside>
        <div class="card prediction-result-card" id="result-container">
          <div class="card-header">
            <h3 class="card-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
              Dictamen de Precalificación
            </h3>
            <span class="badge badge-neutral" id="result-model-version">v_latest</span>
          </div>

          <!-- Estado Inicial Vacío -->
          <div id="result-empty" style="text-align: center; padding: 3rem 1rem; color: var(--color-primary-500);">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin: 0 auto 1rem; color: #94a3b8;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            <p style="font-weight: var(--font-weight-medium);">Listo para evaluar solicitud</p>
            <p style="font-size: var(--font-size-sm); margin: 0;">Complete el formulario y presione "Evaluar Solicitud".</p>
          </div>

          <!-- Estado con Resultados Renderizados -->
          <div id="result-content" class="hidden">
            <div id="decision-banner" class="decision-banner">
              <div id="decision-badge" class="badge" style="margin-bottom: 0.5rem;">DICTAMEN DEL MODELO</div>
              <div id="decision-title" class="decision-title">--</div>
              <div id="decision-subtitle" style="font-size: var(--font-size-sm);">--</div>
            </div>

            <div class="probability-indicator">
              <div class="probability-header">
                <span>Probabilidad de Solvencia:</span>
                <strong id="prob-percentage">0.0%</strong>
              </div>
              <div class="progress-bar-container">
                <div id="prob-bar-fill" class="progress-bar-fill" style="width: 0%;"></div>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: var(--font-size-micro); color: var(--color-primary-500); margin-top: 0.35rem;">
                <span>0% (Insolvente)</span>
                <span id="prob-threshold-label">Umbral Calibrado: 0.77</span>
                <span>100% (Solvente)</span>
              </div>
            </div>

            <div class="recommendation-box">
              <strong style="display: block; margin-bottom: 0.25rem; color: var(--color-primary-900);">Recomendación Comercial:</strong>
              <span id="recommendation-text">--</span>
            </div>

            <div style="margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid var(--color-primary-200); display: flex; justify-content: space-between; font-size: var(--font-size-micro); color: var(--color-primary-500);">
              <span>Latencia de inferencia: <strong id="latency-text" style="color: var(--color-primary-800);">-- ms</strong></span>
              <span>Auditoría: <strong>Supabase DB ✅</strong></span>
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
  const resultEmpty = container.querySelector('#result-empty');
  const resultContent = container.querySelector('#result-content');

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
    window.showToast?.('Cargado perfil de prueba: Alta Solvencia', 'success');
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
    window.showToast?.('Cargado perfil de prueba: Riesgo Crediticio', 'success');
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
    btnPredict.innerHTML = `<span class="spinner" aria-hidden="true"></span> Procesando...`;

    try {
      const resp = await apiService.predict(payload);
      displayPredictionResult(resp, container);
      window.showToast?.(`Evaluación completada: ${resp.predicted_class}`, 'success');
    } catch (err) {
      window.showToast?.(`Error en inferencia: ${err.message}`, 'error');
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
  probThreshold.textContent = `Umbral Calibrado: ${(res.threshold_applied || 0.77).toFixed(2)}`;
  recommendation.textContent = res.recommendation;
  latency.textContent = `${res.latency_ms?.toFixed(1) || '12.0'} ms`;

  if (isSolvent) {
    banner.className = 'decision-banner positive';
    title.textContent = 'CALIFICA (>50K)';
    subtitle.textContent = 'Cliente Solvente Apto para Crédito de Alto Monto';
    probBar.className = 'progress-bar-fill positive';
  } else {
    banner.className = 'decision-banner negative';
    title.textContent = 'NO CALIFICA (<=50K)';
    subtitle.textContent = 'Riesgo Crediticio Elevado o Ingresos Insuficientes';
    probBar.className = 'progress-bar-fill negative';
  }
}
