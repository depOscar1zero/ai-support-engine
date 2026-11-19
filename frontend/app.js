// AI Support Engine - lógica de la demo.
//
// - Sin dependencias ni build. Sin claves: el navegador solo llama a la API.
// - Todo texto del usuario o del modelo se inserta con textContent, nunca
//   como HTML.
// - No genera estilos: solo cambia atributos (hidden, disabled, data-*) y
//   styles.css decide cómo se ve cada estado.
"use strict";

(function () {
  var API_URL = "/api/analyze";
  var MAX_MESSAGE_LENGTH = 2000;
  var WARNING_THRESHOLD = 1900;
  var REQUEST_TIMEOUT_MS = 90000;

  var CATEGORY_LABELS = {
    ACCESS: "Acceso",
    BUG: "Error",
    FEATURE: "Sugerencia",
    SECURITY: "Seguridad"
  };
  var PRIORITY_LABELS = {
    LOW: "Baja",
    MEDIUM: "Media",
    HIGH: "Alta",
    CRITICAL: "Crítica"
  };
  var MODE_LABELS = {
    traditional: "Tradicional (reglas)",
    generative: "Generativo (Gemini)",
    ml: "Machine Learning"
  };

  var MESSAGES = {
    empty: "Escribe un mensaje antes de analizar.",
    invalid: "El mensaje no es válido: debe tener entre 1 y 2000 caracteres y no puede estar vacío.",
    unavailable: "El servicio de análisis no está disponible. Intenta de nuevo más tarde.",
    network: "No se pudo conectar con el servidor. Verifica que esté en marcha e inténtalo de nuevo.",
    timeout: "El análisis tardó demasiado y se canceló. Inténtalo de nuevo.",
    unexpected: "La respuesta del servidor no tiene el formato esperado.",
    loading: "Analizando…",
    loadingSlow: "Analizando… el motor generativo puede tardar más de 10 segundos."
  };

  var elements = {
    loginSection: document.getElementById("login-section"),
    loginForm: document.getElementById("login-form"),
    loginUser: document.getElementById("login-user"),
    loginPassword: document.getElementById("login-password"),
    logoutButton: document.getElementById("logout-button"),
    appSection: document.getElementById("app-section"),
    analyzeForm: document.getElementById("analyze-form"),
    messageInput: document.getElementById("message-input"),
    charCounter: document.getElementById("char-counter"),
    modeSelect: document.getElementById("mode-select"),
    submitButton: document.getElementById("submit-button"),
    loadingIndicator: document.getElementById("loading-indicator"),
    loadingText: document.getElementById("loading-text"),
    errorMessage: document.getElementById("error-message"),
    resultSection: document.getElementById("result-section"),
    resultCategory: document.getElementById("result-category"),
    resultPriority: document.getElementById("result-priority"),
    resultResponse: document.getElementById("result-response"),
    resultMode: document.getElementById("result-mode"),
    reviewWarning: document.getElementById("review-warning"),
    historyList: document.getElementById("history-list"),
    historyEmpty: document.getElementById("history-empty")
  };

  // Historial de la sesión: solo en memoria, se pierde al recargar.
  var history = [];
  var requestInProgress = false;

  function label(labels, value) {
    return Object.prototype.hasOwnProperty.call(labels, value) ? labels[value] : String(value);
  }

  function describe(labels, value) {
    return label(labels, value) + " (" + value + ")";
  }

  // ---------- Login (solo visual, decisión D9) ----------

  function showApp() {
    elements.loginSection.hidden = true;
    elements.appSection.hidden = false;
    elements.messageInput.focus();
  }

  function showLogin() {
    history = [];
    renderHistory();
    hideResult();
    hideError();
    elements.messageInput.value = "";
    updateCounter();
    elements.appSection.hidden = true;
    elements.loginSection.hidden = false;
    elements.loginUser.focus();
  }

  elements.loginForm.addEventListener("submit", function (event) {
    event.preventDefault();
    // Se acepta cualquier valor y no se guarda nada.
    elements.loginUser.value = "";
    elements.loginPassword.value = "";
    showApp();
  });

  elements.logoutButton.addEventListener("click", showLogin);

  // ---------- Formulario ----------

  function updateCounter() {
    var length = elements.messageInput.value.length;
    elements.charCounter.textContent = length + " / " + MAX_MESSAGE_LENGTH;
    if (length >= MAX_MESSAGE_LENGTH) {
      elements.charCounter.dataset.state = "limit";
    } else if (length >= WARNING_THRESHOLD) {
      elements.charCounter.dataset.state = "warning";
    } else {
      elements.charCounter.dataset.state = "normal";
    }
  }

  elements.messageInput.addEventListener("input", updateCounter);

  Array.prototype.forEach.call(
    document.querySelectorAll("[data-example-message]"),
    function (button) {
      button.addEventListener("click", function () {
        elements.messageInput.value = button.dataset.exampleMessage;
        updateCounter();
        hideError();
        elements.messageInput.focus();
      });
    }
  );

  // ---------- Estados ----------

  function showError(text) {
    elements.errorMessage.textContent = text;
    elements.errorMessage.hidden = false;
  }

  function hideError() {
    elements.errorMessage.textContent = "";
    elements.errorMessage.hidden = true;
  }

  function hideResult() {
    elements.resultSection.hidden = true;
  }

  var loadingTimer = null;

  function setLoading(isLoading) {
    requestInProgress = isLoading;
    elements.submitButton.disabled = isLoading;
    elements.loadingIndicator.hidden = !isLoading;
    elements.analyzeForm.setAttribute("aria-busy", isLoading ? "true" : "false");

    if (loadingTimer !== null) {
      window.clearInterval(loadingTimer);
      loadingTimer = null;
    }
    if (isLoading) {
      var startedAt = Date.now();
      elements.loadingText.textContent = MESSAGES.loading;
      loadingTimer = window.setInterval(function () {
        var seconds = Math.floor((Date.now() - startedAt) / 1000);
        var base = seconds >= 5 ? MESSAGES.loadingSlow : MESSAGES.loading;
        elements.loadingText.textContent = base + " (" + seconds + " s)";
      }, 1000);
    }
  }

  // ---------- Resultado e historial ----------

  function isValidResponse(data) {
    return (
      data !== null &&
      typeof data === "object" &&
      typeof data.category === "string" &&
      typeof data.priority === "string" &&
      typeof data.response === "string" &&
      typeof data.requiresHumanReview === "boolean" &&
      typeof data.mode === "string"
    );
  }

  function renderResult(data) {
    elements.resultCategory.textContent = describe(CATEGORY_LABELS, data.category);
    elements.resultCategory.dataset.category = data.category;
    elements.resultPriority.textContent = describe(PRIORITY_LABELS, data.priority);
    elements.resultPriority.dataset.priority = data.priority;
    elements.resultResponse.textContent = data.response;
    elements.resultMode.textContent = label(MODE_LABELS, data.mode);
    elements.reviewWarning.hidden = !data.requiresHumanReview;
    elements.resultSection.hidden = false;
    elements.resultSection.focus();
  }

  function createElement(tag, className, text) {
    var element = document.createElement(tag);
    element.className = className;
    if (text !== undefined) {
      element.textContent = text;
    }
    return element;
  }

  function renderHistory() {
    var items = history.map(function (entry) {
      var item = createElement("li", "history-item");
      item.appendChild(createElement("p", "history-message", entry.message));

      var meta = createElement("div", "history-meta");
      meta.appendChild(createElement("span", "history-mode", label(MODE_LABELS, entry.mode)));

      var category = createElement("span", "badge badge--category", describe(CATEGORY_LABELS, entry.category));
      category.dataset.category = entry.category;
      meta.appendChild(category);

      var priority = createElement("span", "badge badge--priority", describe(PRIORITY_LABELS, entry.priority));
      priority.dataset.priority = entry.priority;
      meta.appendChild(priority);

      var review = createElement(
        "span",
        "history-review",
        entry.requiresHumanReview ? "Revisión humana: sí" : "Revisión humana: no"
      );
      review.dataset.review = entry.requiresHumanReview ? "true" : "false";
      meta.appendChild(review);

      item.appendChild(meta);
      return item;
    });

    // El análisis más reciente aparece primero.
    items.reverse();
    elements.historyList.replaceChildren.apply(elements.historyList, items);
    elements.historyList.hidden = history.length === 0;
    elements.historyEmpty.hidden = history.length !== 0;
  }

  // ---------- Petición ----------

  function messageForStatus(status) {
    if (status === 422) {
      return MESSAGES.invalid;
    }
    if (status === 502) {
      return MESSAGES.unavailable;
    }
    return MESSAGES.network;
  }

  function analyze(message, mode) {
    var controller = new AbortController();
    var timeout = window.setTimeout(function () {
      controller.abort();
    }, REQUEST_TIMEOUT_MS);

    return fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message, mode: mode }),
      signal: controller.signal
    })
      .then(function (response) {
        if (!response.ok) {
          var error = new Error("http");
          error.kind = "status";
          error.status = response.status;
          throw error;
        }
        return response.json();
      })
      .finally(function () {
        window.clearTimeout(timeout);
      });
  }

  elements.analyzeForm.addEventListener("submit", function (event) {
    event.preventDefault();
    if (requestInProgress) {
      return;
    }

    var message = elements.messageInput.value.trim();
    var mode = elements.modeSelect.value;
    hideError();

    if (message === "") {
      showError(MESSAGES.empty);
      elements.messageInput.focus();
      return;
    }

    hideResult();
    setLoading(true);

    analyze(message, mode)
      .then(function (data) {
        if (!isValidResponse(data)) {
          showError(MESSAGES.unexpected);
          return;
        }
        history.push({
          message: message,
          mode: data.mode,
          category: data.category,
          priority: data.priority,
          requiresHumanReview: data.requiresHumanReview
        });
        renderResult(data);
        renderHistory();
      })
      .catch(function (error) {
        if (error && error.kind === "status") {
          showError(messageForStatus(error.status));
        } else if (error && error.name === "AbortError") {
          showError(MESSAGES.timeout);
        } else {
          showError(MESSAGES.network);
        }
      })
      .finally(function () {
        setLoading(false);
      });
  });

  updateCounter();
  renderHistory();
})();
