/**
 * Aplicación Frontend: Sistema de Vigilancia y Seguimiento Nutricional
 * IPSI Kottushi Sao Ana>a
 */

const API_BASE = "";

// Estado global de la aplicación
const AppState = {
  casos: [],
  notificados: [],
  catalogos: {
    municipios: [],
    eapb: [],
    sedes: [],
    novedades: []
  },
  casoActual: null,
  pestanaPreviaExpediente: "tab-notificados",
  alertasRescate: null,
  pestañaAlertaActiva: "perdida_peso",
  busquedaResultados: [],
  indiceBusquedaActivo: -1,
  filtros: {
    estado_caso: "En seguimiento",
    municipio: "",
    eapb: "",
    clasificacion: "",
    citas_vencidas: false,
    busqueda: "",
    page: 1,
    limit: 50
  },
  filtrosNotificados: {
    evento: "",
    primera_atencion: "",
    municipio: "",
    eapb: "",
    estado_caso: "",
    busqueda: "",
    page: 1,
    limit: 50
  },
  totalCasos: 0,
  totalNotificados: 0,
  charts: {}
};

// =============================================================================
// INICIALIZACIÓN
// =============================================================================
document.addEventListener("DOMContentLoaded", () => {
  inicializarNavegacion();
  cargarCatalogos();
  cargarDashboard();
  cargarCasos();
  cargarKpisNotificados();
  cargarNotificados();
  configurarEventosFiltros();
  configurarEventosFiltrosNotificados();
  configurarFormularios();
  inicializarModuloImportacion();
  inicializarBusquedaGlobal();
  cargarAlertasRescate();
  inicializarSincronizacionScroll();
});

// Navegación por pestañas
function inicializarNavegacion() {
  const tabs = document.querySelectorAll("[data-tab-target]");
  tabs.forEach(tab => {
    tab.addEventListener("click", (e) => {
      e.preventDefault();
      const targetId = tab.getAttribute("data-tab-target");
      activarPestana(targetId);
    });
  });
}

function activarPestana(targetId) {
  // Recordar pestaña anterior si no es expediente ni importación
  if (targetId !== "tab-expediente" && targetId !== "tab-importacion") {
    AppState.pestanaPreviaExpediente = targetId;
  }

  document.querySelectorAll("[data-tab-target]").forEach(t => {
    t.classList.remove("text-sky-400", "border-sky-400", "font-bold");
    t.classList.add("text-slate-300", "border-transparent");
  });
  const activeTab = document.querySelector(`[data-tab-target="${targetId}"]`);
  if (activeTab) {
    activeTab.classList.add("text-sky-400", "border-sky-400", "font-bold");
    activeTab.classList.remove("text-slate-300", "border-transparent");
  }

  document.querySelectorAll(".tab-content").forEach(content => {
    content.classList.remove("active");
  });
  const targetContent = document.getElementById(targetId);
  if (targetContent) {
    targetContent.classList.add("active");
  }

  // Control del botón flotante y texto de volver en expediente
  const btnFlotante = document.getElementById("exp-boton-flotante-volver");
  if (targetId === "tab-expediente") {
    if (btnFlotante) btnFlotante.classList.remove("hidden");
    actualizarTextoBotonVolver();
  } else {
    if (btnFlotante) btnFlotante.classList.add("hidden");
  }

  // Refrescar según pestaña
  if (targetId === "tab-dashboard") cargarDashboard();
  if (targetId === "tab-notificados") {
    cargarKpisNotificados();
    cargarNotificados();
  }
  if (targetId === "tab-casos") cargarCasos();
  if (targetId === "tab-indicadores") cargarIndicadores();
  if (targetId === "tab-reportes-oficiales") poblarSelectoresReportesOficiales();
}

function actualizarTextoBotonVolver() {
  const origen = AppState.pestanaPreviaExpediente || "tab-notificados";
  let texto = "← Volver a la Lista";
  if (origen === "tab-notificados") texto = "← Volver a Notificados (FT-003)";
  else if (origen === "tab-casos") texto = "← Volver a Casos en Seguimiento";
  else if (origen === "tab-dashboard") texto = "← Volver al Tablero General";

  const btnVolver = document.getElementById("exp-btn-volver-texto");
  if (btnVolver) btnVolver.innerText = texto;
  const btnFlotante = document.getElementById("exp-btn-flotante-texto");
  if (btnFlotante) btnFlotante.innerText = texto;
}

function volverDeExpediente() {
  const destino = AppState.pestanaPreviaExpediente || "tab-notificados";
  activarPestana(destino);
}

// =============================================================================
// CARGA DE CATÁLOGOS
// =============================================================================
async function cargarCatalogos() {
  try {
    const [munRes, eapbRes, sedesRes, novRes] = await Promise.all([
      fetch(`${API_BASE}/api/catalogos/municipios`),
      fetch(`${API_BASE}/api/catalogos/eapb`),
      fetch(`${API_BASE}/api/catalogos/sedes`),
      fetch(`${API_BASE}/api/catalogos/novedades`)
    ]);

    AppState.catalogos.municipios = await munRes.json();
    AppState.catalogos.eapb = await eapbRes.json();
    AppState.catalogos.sedes = await sedesRes.json();
    AppState.catalogos.novedades = await novRes.json();

    poblarSelectoresCatalogos();
  } catch (err) {
    console.error("Error al cargar catálogos maestros:", err);
  }
}

function poblarSelectoresCatalogos() {
  // Filtros de Casos
  const selMun = document.getElementById("filtro-municipio");
  const selEAPB = document.getElementById("filtro-eapb");
  if (selMun) {
    selMun.innerHTML = '<option value="">Todos los Municipios</option>';
    AppState.catalogos.municipios.forEach(m => {
      selMun.innerHTML += `<option value="${m.nombre}">${m.nombre}</option>`;
    });
  }
  if (selEAPB) {
    selEAPB.innerHTML = '<option value="">Todas las EAPB (EPS)</option>';
    AppState.catalogos.eapb.forEach(e => {
      selEAPB.innerHTML += `<option value="${e.nombre}">${e.nombre}</option>`;
    });
  }

  // Filtros de Notificados (FT-003)
  const selNotifMun = document.getElementById("filtro-notif-municipio");
  const selNotifEAPB = document.getElementById("filtro-notif-eapb");
  if (selNotifMun) {
    selNotifMun.innerHTML = '<option value="">Todos los Municipios</option>';
    AppState.catalogos.municipios.forEach(m => {
      selNotifMun.innerHTML += `<option value="${m.nombre}">${m.nombre}</option>`;
    });
  }
  if (selNotifEAPB) {
    selNotifEAPB.innerHTML = '<option value="">Todas las EAPB (EPS)</option>';
    AppState.catalogos.eapb.forEach(e => {
      selNotifEAPB.innerHTML += `<option value="${e.nombre}">${e.nombre}</option>`;
    });
  }

  // Selectores de Nuevo Caso
  const fMun = document.getElementById("nuevo-municipio");
  const fEAPB = document.getElementById("nuevo-eapb");
  const fSede = document.getElementById("nuevo-sede");
  if (fMun) {
    fMun.innerHTML = '<option value="">Seleccione Municipio</option>';
    AppState.catalogos.municipios.forEach(m => {
      fMun.innerHTML += `<option value="${m.id}">${m.nombre}</option>`;
    });
  }
  if (fEAPB) {
    fEAPB.innerHTML = '<option value="">Seleccione EAPB</option>';
    AppState.catalogos.eapb.forEach(e => {
      fEAPB.innerHTML += `<option value="${e.id}">${e.nombre}</option>`;
    });
  }
  if (fSede) {
    fSede.innerHTML = '<option value="">Seleccione Sede IPSI</option>';
    AppState.catalogos.sedes.forEach(s => {
      fSede.innerHTML += `<option value="${s.id}">${s.nombre}</option>`;
    });
  }

  // Selector Novedades en Nuevo Control
  const fNov = document.getElementById("control-novedad");
  if (fNov) {
    fNov.innerHTML = '<option value="">Sin Novedad Especial</option>';
    AppState.catalogos.novedades.forEach(n => {
      fNov.innerHTML += `<option value="${n.novedad_id}">${n.descripcion}</option>`;
    });
  }
}

// =============================================================================
// MÓDULO 1: DASHBOARD DE CONTROL
// =============================================================================
async function cargarDashboard() {
  try {
    const res = await fetch(`${API_BASE}/api/reportes/dashboard`);
    if (!res.ok) return;
    const data = await res.json();

    // Actualizar KPIs numéricos
    document.getElementById("kpi-notificados").innerText = data.total_notificados.toLocaleString();
    document.getElementById("kpi-seguimiento").innerText = data.total_en_seguimiento.toLocaleString();
    document.getElementById("kpi-cerrados").innerText = data.total_cerrados.toLocaleString();
    document.getElementById("kpi-citas-vencidas").innerText = data.citas_vencidas_hoy.toLocaleString();
    document.getElementById("kpi-alertas-edad").innerText = data.alertas_egreso_edad.toLocaleString();

    renderizarGraficasDashboard(data);
  } catch (err) {
    console.error("Error al cargar datos del Dashboard:", err);
  }
}

function renderizarGraficasDashboard(data) {
  // 1. Gráfica de Distribución Diagnóstica (Donut)
  const ctxDx = document.getElementById("chart-diagnostico");
  if (ctxDx) {
    const labels = Object.keys(data.distribucion_diagnostico);
    const valores = Object.values(data.distribucion_diagnostico);
    const colores = labels.map(l => {
      if (l.includes("severa")) return "#ef4444";
      if (l.includes("moderada")) return "#f97316";
      if (l.includes("Riesgo")) return "#f59e0b";
      if (l.includes("adecuado")) return "#10b981";
      if (l.includes("Sobrepeso")) return "#8b5cf6";
      return "#94a3b8";
    });

    if (AppState.charts.dx) AppState.charts.dx.destroy();
    AppState.charts.dx = new Chart(ctxDx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: valores,
          backgroundColor: colores,
          borderWidth: 2,
          borderColor: "#ffffff"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 10 } } }
        }
      }
    });
  }

  // 2. Gráfica de Municipios (Barras horizontales)
  const ctxMun = document.getElementById("chart-municipios");
  if (ctxMun) {
    const munEntries = Object.entries(data.distribucion_municipio).slice(0, 8);
    if (AppState.charts.mun) AppState.charts.mun.destroy();
    AppState.charts.mun = new Chart(ctxMun, {
      type: "bar",
      data: {
        labels: munEntries.map(e => e[0]),
        datasets: [{
          label: "Casos Notificados",
          data: munEntries.map(e => e[1]),
          backgroundColor: "#0284c7",
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true } }
      }
    });
  }

  // 3. Gráfica de EAPB (Barras)
  const ctxEapb = document.getElementById("chart-eapb");
  if (ctxEapb) {
    const eapbEntries = Object.entries(data.distribucion_eapb).slice(0, 6);
    if (AppState.charts.eapb) AppState.charts.eapb.destroy();
    AppState.charts.eapb = new Chart(ctxEapb, {
      type: "bar",
      data: {
        labels: eapbEntries.map(e => e[0]),
        datasets: [{
          label: "Casos por EAPB",
          data: eapbEntries.map(e => e[1]),
          backgroundColor: "#38bdf8",
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } }
      }
    });
  }
}

// =============================================================================
// MÓDULO 2: TABLA DE CASOS Y SEGUIMIENTO ACTIVO
// =============================================================================
async function cargarCasos() {
  const tbody = document.getElementById("tabla-casos-body");
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="10" class="text-center py-8 text-slate-500">Cargando información clínica en vivo...</td></tr>';

  try {
    const params = new URLSearchParams();
    if (AppState.filtros.estado_caso) params.append("estado_caso", AppState.filtros.estado_caso);
    if (AppState.filtros.municipio) params.append("municipio", AppState.filtros.municipio);
    if (AppState.filtros.eapb) params.append("eapb", AppState.filtros.eapb);
    if (AppState.filtros.clasificacion) params.append("clasificacion", AppState.filtros.clasificacion);
    if (AppState.filtros.citas_vencidas) params.append("citas_vencidas", "true");
    if (AppState.filtros.busqueda) params.append("busqueda", AppState.filtros.busqueda);

    const limit = AppState.filtros.limit || 50;
    const page = AppState.filtros.page || 1;
    const offset = (page - 1) * limit;

    params.append("limit", limit.toString());
    params.append("offset", offset.toString());

    const res = await fetch(`${API_BASE}/api/casos?${params.toString()}`);
    if (!res.ok) throw new Error("Error en respuesta de API");

    const headerTotal = res.headers.get("X-Total-Count");
    const casos = await res.json();
    AppState.casos = casos;
    AppState.totalCasos = headerTotal !== null ? parseInt(headerTotal) : casos.length;

    // Actualizar badges y contadores en vivo con el total REAL de la base de datos
    const badgeVencidas = document.getElementById("badge-filtro-vencidas");
    if (badgeVencidas) {
      if (AppState.filtros.citas_vencidas) {
        badgeVencidas.classList.remove("hidden");
      } else {
        badgeVencidas.classList.add("hidden");
      }
    }

    const contadorEl = document.getElementById("contador-casos-mostrados");
    if (contadorEl) {
      if (AppState.filtros.citas_vencidas) {
        contadorEl.innerHTML = `<span class="text-rose-700 font-black">🚨 ${AppState.totalCasos.toLocaleString()} casos con citas vencidas</span>`;
      } else if (AppState.filtros.estado_caso === "En seguimiento") {
        contadorEl.innerHTML = `<strong class="text-slate-900">${AppState.totalCasos.toLocaleString()} casos en seguimiento activo</strong>`;
      } else {
        contadorEl.innerHTML = `<strong class="text-slate-900">${AppState.totalCasos.toLocaleString()} casos encontrados</strong>`;
      }
    }

    // Actualizar barra de paginación
    actualizarBarraPaginacion(page, limit, AppState.totalCasos);

    if (casos.length === 0) {
      tbody.innerHTML = '<tr><td colspan="10" class="text-center py-8 text-slate-400">No se encontraron casos con los filtros seleccionados.</td></tr>';
      return;
    }

    tbody.innerHTML = "";
    casos.forEach(c => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50 border-b border-slate-100 transition-colors";

      // Badge de estado nutricional
      const badgeClass = obtenerClaseBadge(c.clasificacion_nutricional_actual);

      // Semáforo de cita
      let citaBadge = `<span class="text-slate-400 text-xs">-</span>`;
      if (c.fecha_proxima_cita) {
        if (c.alerta_cita_vencida) {
          citaBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-rose-100 text-rose-700 animate-pulse">VENCIDA: ${c.fecha_proxima_cita}</span>`;
        } else {
          citaBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700">${c.fecha_proxima_cita}</span>`;
        }
      }

      // Alerta de edad
      let alertaEdadBadge = "";
      if (c.alerta_egreso_edad) {
        alertaEdadBadge = `<span class="ml-1 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-200 text-amber-900" title="Edad >= 60 meses. Debe salir de la ruta.">≥60m</span>`;
      }

      const nutri = c.nutricionista_asignado || c.sede_ipsi || "Sin asignar";

      tr.innerHTML = `
        <td class="py-3 px-3.5 font-mono font-medium text-slate-800 whitespace-nowrap">${c.numero_documento}</td>
        <td class="py-3 px-3.5 font-medium text-slate-900 whitespace-nowrap">${c.nombre_completo} ${alertaEdadBadge}</td>
        <td class="py-3 px-3.5 text-slate-600 text-center whitespace-nowrap">${c.edad_meses_actual ?? "-"} m</td>
        <td class="py-3 px-3.5 text-slate-600 whitespace-nowrap">${c.municipio || "-"}</td>
        <td class="py-3 px-3.5 text-slate-600 whitespace-nowrap">${c.eapb || "-"}</td>
        <td class="py-3 px-3.5 text-slate-700 whitespace-nowrap font-medium">
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-800 border border-slate-200">
            👤 ${nutri}
          </span>
        </td>
        <td class="py-3 px-3.5 whitespace-nowrap">
          <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${badgeClass}">
            ${c.clasificacion_nutricional_actual}
          </span>
        </td>
        <td class="py-3 px-3.5 text-center font-bold text-slate-700 whitespace-nowrap">${c.total_controles}</td>
        <td class="py-3 px-3.5 whitespace-nowrap">${citaBadge}</td>
        <td class="py-3 px-3.5 text-right whitespace-nowrap">
          <button onclick="verDetalleCaso(${c.caso_id})" class="text-sky-600 hover:text-sky-800 text-xs font-bold px-2 py-1 bg-sky-50 rounded hover:bg-sky-100 transition mr-1">
            Expediente
          </button>
          <button onclick="imprimirExpedientePorId(${c.caso_id})" title="Imprimir Expediente Clínico Completo" class="text-slate-700 hover:text-slate-900 text-xs font-bold px-2 py-1 bg-slate-100 rounded hover:bg-slate-200 transition mr-1">
            🖨️
          </button>
          <button onclick="abrirModalNuevoControl(${c.caso_id}, '${c.nombre_completo.replace(/'/g, "\\'")}')" class="text-emerald-600 hover:text-emerald-800 text-xs font-bold px-2 py-1 bg-emerald-50 rounded hover:bg-emerald-100 transition">
            + Control
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    if (typeof window.ajustarScrollCasos === "function") {
      window.ajustarScrollCasos();
    }
  } catch (err) {
    console.error("Error al cargar casos:", err);
    tbody.innerHTML = '<tr><td colspan="10" class="text-center py-8 text-rose-500">Error al conectar con el servidor backend.</td></tr>';
  }
}

function actualizarBarraPaginacion(page, limit, total) {
  const resumenEl = document.getElementById("paginacion-resumen");
  const indicadorEl = document.getElementById("paginacion-indicador");
  const btnAnt = document.getElementById("btn-pag-anterior");
  const btnSig = document.getElementById("btn-pag-siguiente");

  const totalPaginas = Math.ceil(total / limit) || 1;
  const inicio = total > 0 ? (page - 1) * limit + 1 : 0;
  const fin = Math.min(page * limit, total);

  if (resumenEl) {
    resumenEl.innerText = `Mostrando ${inicio} a ${fin} de ${total.toLocaleString()} casos`;
  }
  if (indicadorEl) {
    indicadorEl.innerText = `Página ${page} de ${totalPaginas}`;
  }
  if (btnAnt) {
    btnAnt.disabled = page <= 1;
  }
  if (btnSig) {
    btnSig.disabled = page >= totalPaginas;
  }
}

function cambiarPaginaCasos(delta) {
  const limit = AppState.filtros.limit || 50;
  const totalPaginas = Math.ceil(AppState.totalCasos / limit) || 1;
  let nuevaPagina = (AppState.filtros.page || 1) + delta;
  if (nuevaPagina < 1) nuevaPagina = 1;
  if (nuevaPagina > totalPaginas) nuevaPagina = totalPaginas;

  AppState.filtros.page = nuevaPagina;
  cargarCasos();
}

function obtenerClaseBadge(clasificacion) {
  if (!clasificacion) return "badge-sin-dato";
  const c = clasificacion.toLowerCase();
  if (c.includes("severa")) return "badge-dnt-severa";
  if (c.includes("moderada")) return "badge-dnt-moderada";
  if (c.includes("riesgo")) return "badge-riesgo-dnt";
  if (c.includes("adecuado")) return "badge-peso-adecuado";
  if (c.includes("sobrepeso")) return "badge-sobrepeso";
  return "badge-sin-dato";
}

function configurarEventosFiltros() {
  const selEst = document.getElementById("filtro-estado");
  const selMun = document.getElementById("filtro-municipio");
  const selEapb = document.getElementById("filtro-eapb");
  const selDx = document.getElementById("filtro-clasificacion");
  const chkVenc = document.getElementById("filtro-citas-vencidas");
  const inpBusq = document.getElementById("filtro-busqueda");
  const selLim = document.getElementById("paginacion-limite");

  const actualizar = () => {
    AppState.filtros.estado_caso = selEst ? selEst.value : "";
    AppState.filtros.municipio = selMun ? selMun.value : "";
    AppState.filtros.eapb = selEapb ? selEapb.value : "";
    AppState.filtros.clasificacion = selDx ? selDx.value : "";
    AppState.filtros.citas_vencidas = chkVenc ? chkVenc.checked : false;
    AppState.filtros.busqueda = inpBusq ? inpBusq.value.trim() : "";
    AppState.filtros.page = 1;
    cargarCasos();
  };

  if (selEst) selEst.addEventListener("change", actualizar);
  if (selMun) selMun.addEventListener("change", actualizar);
  if (selEapb) selEapb.addEventListener("change", actualizar);
  if (selDx) selDx.addEventListener("change", actualizar);
  if (chkVenc) chkVenc.addEventListener("change", actualizar);
  if (selLim) {
    selLim.addEventListener("change", () => {
      AppState.filtros.limit = parseInt(selLim.value) || 50;
      AppState.filtros.page = 1;
      cargarCasos();
    });
  }
  if (inpBusq) {
    let debounceTimer;
    inpBusq.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(actualizar, 300);
    });
  }

  const btnLimpiar = document.getElementById("btn-limpiar-filtros");
  if (btnLimpiar) {
    btnLimpiar.addEventListener("click", () => {
      if (selEst) selEst.value = "En seguimiento";
      if (selMun) selMun.value = "";
      if (selEapb) selEapb.value = "";
      if (selDx) selDx.value = "";
      if (chkVenc) chkVenc.checked = false;
      if (inpBusq) inpBusq.value = "";
      if (selLim) selLim.value = "50";
      AppState.filtros.limit = 50;
      AppState.filtros.page = 1;
      actualizar();
    });
  }
}

// =============================================================================
// MÓDULO 3: EXPEDIENTE CLÍNICO Y SEGUIMIENTOS
// =============================================================================
function imprimirExpedienteActual() {
  if (!AppState.casoActual || !AppState.casoActual.detalle || !AppState.casoActual.detalle.resumen) {
    alert("Por favor seleccione primero un caso en la tabla para imprimir su expediente clínico.");
    return;
  }
  const casoId = AppState.casoActual.detalle.resumen.caso_id;
  imprimirExpedientePorId(casoId);
}

function imprimirExpedientePorId(casoId) {
  if (!casoId) return;
  const url = `${API_BASE}/api/casos/${casoId}/imprimir?autoprint=true`;
  window.open(url, "_blank");
}

async function verDetalleCaso(casoId) {
  try {
    // Recordar de qué pestaña viene antes de pasar al expediente
    const pestañaActiva = document.querySelector(".tab-content.active");
    if (pestañaActiva && pestañaActiva.id !== "tab-expediente") {
      AppState.pestanaPreviaExpediente = pestañaActiva.id;
    }

    const [casoRes, controlesRes] = await Promise.all([
      fetch(`${API_BASE}/api/casos/${casoId}`),
      fetch(`${API_BASE}/api/casos/${casoId}/controles`)
    ]);

    if (!casoRes.ok) throw new Error("No se pudo cargar el caso");
    const detalle = await casoRes.json();
    const controles = await controlesRes.json();
    AppState.casoActual = { detalle, controles };

    renderizarExpediente(detalle, controles);
    activarPestana("tab-expediente");
  } catch (err) {
    console.error("Error al obtener detalle del caso:", err);
    alert("Error al cargar el expediente del paciente.");
  }
}

function renderizarExpediente(detalleData, controles) {
  const r = detalleData.resumen;
  const d = detalleData.detalle_notificacion;
  const timeline = detalleData.timeline_trazabilidad || [];
  const totalEpisodios = detalleData.total_episodios_paciente || 1;

  // Encabezado del paciente
  document.getElementById("exp-nombre").innerText = r.nombre_completo;
  document.getElementById("exp-documento").innerText = `${r.tipo_documento} ${r.numero_documento}`;
  document.getElementById("exp-edad").innerText = `${r.edad_meses_actual ?? "-"} meses`;
  document.getElementById("exp-municipio").innerText = r.municipio || "-";
  document.getElementById("exp-eapb").innerText = r.eapb || "-";
  document.getElementById("exp-sede").innerText = r.sede_ipsi || "-";
  document.getElementById("exp-cuidador").innerText = r.cuidador || "Sin dato";
  document.getElementById("exp-telefono").innerText = r.telefono_cuidador || "Sin dato";
  document.getElementById("exp-estado").innerText = r.estado_caso;

  const expEpisodios = document.getElementById("exp-episodios-badge");
  if (expEpisodios) {
    if (totalEpisodios > 1) {
      expEpisodios.innerHTML = `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-purple-100 text-purple-800">${totalEpisodios} Notificaciones registradas</span>`;
    } else {
      expEpisodios.innerText = "1 Notificación única";
    }
  }

  const badgeDx = document.getElementById("exp-diagnostico-badge");
  if (badgeDx) {
    badgeDx.className = `inline-flex items-center px-3 py-1 rounded-full text-xs font-bold ${obtenerClaseBadge(r.clasificacion_nutricional_actual)}`;
    badgeDx.innerText = r.clasificacion_nutricional_actual;
  }

  // Contador de hitos
  const contadorHitos = document.getElementById("exp-total-hitos-contador");
  if (contadorHitos) {
    contadorHitos.innerText = `${timeline.length} hitos de trazabilidad`;
  }

  // Configurar botones de acción
  const btnImprimir = document.getElementById("exp-btn-imprimir");
  if (btnImprimir) {
    btnImprimir.onclick = () => imprimirExpedientePorId(r.caso_id);
  }
  const btnNuevoCtrl = document.getElementById("exp-btn-nuevo-control");
  if (btnNuevoCtrl) {
    btnNuevoCtrl.onclick = () => abrirModalNuevoControl(r.caso_id, r.nombre_completo);
  }
  const btnCerrar = document.getElementById("exp-btn-cerrar-caso");
  if (btnCerrar) {
    btnCerrar.onclick = () => abrirModalCerrarCaso(r.caso_id, r.nombre_completo);
  }

  // 1. RENDERIZAR MÓDULO MULTIMODAL DE TRAZABILIDAD (KARDEX, TIMELINE Y TARJETAS PAGINADAS)
  renderizarModuloTrazabilidad(timeline);

  // 2. RENDERIZAR CURVA DE EVOLUCIÓN ANTROPOMÉTRICA CONSOLIDADA Y ORDENADA
  renderizarCurvaEvolucionTrazabilidad(timeline);
}

// =============================================================================
// CONMUTADOR Y RENDERIZADOR MULTIMODAL DE TRAZABILIDAD (3 VISTAS CLÍNICAS)
// =============================================================================
function cambiarVistaTrazabilidad(modo) {
  AppState.vistaTrazabilidad = modo;

  const btnKardex = document.getElementById("btn-vista-kardex");
  const btnTimeline = document.getElementById("btn-vista-timeline");
  const btnTarjetas = document.getElementById("btn-vista-tarjetas");

  const secKardex = document.getElementById("vista-trazabilidad-kardex");
  const secTimeline = document.getElementById("vista-trazabilidad-timeline");
  const secTarjetas = document.getElementById("vista-trazabilidad-tarjetas");

  const activoClass = "vista-trazabilidad-btn px-3 py-1.5 rounded-lg transition flex items-center space-x-1.5 bg-white text-sky-700 shadow-sm border border-slate-200 font-bold";
  const inactivoClass = "vista-trazabilidad-btn px-3 py-1.5 rounded-lg transition flex items-center space-x-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-200/60 font-medium border border-transparent";

  if (btnKardex) btnKardex.className = modo === "kardex" ? activoClass : inactivoClass;
  if (btnTimeline) btnTimeline.className = modo === "timeline" ? activoClass : inactivoClass;
  if (btnTarjetas) btnTarjetas.className = modo === "tarjetas" ? activoClass : inactivoClass;

  if (secKardex) secKardex.classList.toggle("hidden", modo !== "kardex");
  if (secTimeline) secTimeline.classList.toggle("hidden", modo !== "timeline");
  if (secTarjetas) secTarjetas.classList.toggle("hidden", modo !== "tarjetas");
}

function renderizarModuloTrazabilidad(timeline) {
  AppState.timelineActual = timeline || [];
  AppState.paginaTarjetas = 0;
  AppState.tarjetasPorPagina = 4;
  AppState.timelineIntermediosExpandidos = false;

  // Si tiene más de 4 hitos se recomienda 'kardex', si tiene 1-4 se usa 'tarjetas'
  if (!AppState.vistaTrazabilidad) {
    AppState.vistaTrazabilidad = timeline.length > 4 ? "kardex" : "tarjetas";
  }

  // 1. Resumen Macro de Fases
  renderizarResumenMacroFases(timeline);

  // 2. Tabla Kardex de Evolución
  renderizarTablaKardexEvolucion(timeline);

  // 3. Línea de Tiempo Vertical Colapsable
  renderizarTimelineVertical(timeline);

  // 4. Tarjetas Paginadas
  renderizarTarjetasPaginadas();

  // Activar la vista seleccionada
  cambiarVistaTrazabilidad(AppState.vistaTrazabilidad);
}

function renderizarResumenMacroFases(timeline) {
  const container = document.getElementById("exp-resumen-macro-fases");
  if (!container) return;

  const captacion = timeline.find(h => h.tipo_hito.includes("Captación"));
  const gbai = timeline.find(h => h.tipo_hito.includes("GBAI"));
  const primera = timeline.find(h => h.tipo_hito.includes("Primera") || h.tipo_hito.includes("1ra"));
  const seguimientos = timeline.filter(h => h.tipo_hito.includes("Seguimiento"));
  const ultimoHito = timeline[timeline.length - 1];

  let pesoInicial = captacion?.peso_kg || primera?.peso_kg || null;
  let pesoFinal = ultimoHito?.peso_kg || null;
  let deltaTotal = pesoInicial && pesoFinal ? (pesoFinal - pesoInicial).toFixed(2) : null;
  let signoDelta = deltaTotal > 0 ? `+${deltaTotal} kg` : (deltaTotal ? `${deltaTotal} kg` : "-");

  container.innerHTML = `
    <!-- Fase 1: Captación -->
    <div class="bg-amber-50/70 p-2.5 rounded-xl border border-amber-200 flex flex-col justify-between">
      <div>
        <span class="text-[10px] font-bold text-amber-800 uppercase tracking-wider block">1. Captación</span>
        <span class="text-xs font-bold text-slate-800 font-mono">${captacion?.fecha || "Sin fecha"}</span>
      </div>
      <div class="mt-1 text-[11px] text-slate-600">
        <span>Peso: <strong>${captacion?.peso_kg ? captacion.peso_kg + ' kg' : '-'}</strong></span>
        <span class="ml-1 text-slate-400">• Z: ${captacion?.zscore ?? '-'}</span>
      </div>
    </div>

    <!-- Fase 2: GBAI Búsqueda -->
    <div class="bg-blue-50/70 p-2.5 rounded-xl border border-blue-200 flex flex-col justify-between">
      <div>
        <span class="text-[10px] font-bold text-blue-800 uppercase tracking-wider block">2. Búsqueda GBAI</span>
        <span class="text-xs font-bold text-slate-800 font-mono">${gbai?.fecha || "Efectiva"}</span>
      </div>
      <div class="mt-1 text-[11px] text-slate-600 truncate">
        <span>${gbai?.detalle || "Búsqueda activa en territorio"}</span>
      </div>
    </div>

    <!-- Fase 3: 1ra Atención IPSI -->
    <div class="bg-sky-50/70 p-2.5 rounded-xl border border-sky-200 flex flex-col justify-between">
      <div>
        <span class="text-[10px] font-bold text-sky-800 uppercase tracking-wider block">3. 1ra Atención IPSI</span>
        <span class="text-xs font-bold text-slate-800 font-mono">${primera?.fecha || "Ingreso"}</span>
      </div>
      <div class="mt-1 text-[11px] text-slate-600">
        <span>Peso: <strong>${primera?.peso_kg ? primera.peso_kg + ' kg' : '-'}</strong></span>
        <span class="ml-1 text-slate-400">• Z: ${primera?.zscore ?? '-'}</span>
      </div>
    </div>

    <!-- Fase 4: Seguimientos Clínicos -->
    <div class="bg-emerald-50/70 p-2.5 rounded-xl border border-emerald-200 flex flex-col justify-between">
      <div>
        <span class="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">4. Seguimiento Activo</span>
        <span class="text-xs font-bold text-slate-800">${seguimientos.length} Controles</span>
      </div>
      <div class="mt-1 text-[11px]">
        <span class="text-slate-500">Δ Total:</span>
        <strong class="${deltaTotal >= 0 ? 'text-emerald-700' : 'text-rose-600'}">${signoDelta}</strong>
      </div>
    </div>
  `;
}

function renderizarTablaKardexEvolucion(timeline) {
  const tbody = document.getElementById("exp-tabla-kardex-body");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (timeline.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" class="text-center py-6 text-slate-400">No se registran eventos clínicos en la ruta.</td></tr>';
    return;
  }

  timeline.forEach((item, index) => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50 border-b border-slate-100 transition-colors";

    // Chip de variación de peso
    let deltaHtml = '<span class="text-slate-300">-</span>';
    if (item.delta_peso_kg !== null && item.delta_peso_kg !== undefined && index > 0) {
      if (item.delta_peso_kg > 0) {
        deltaHtml = `<span class="ml-1 px-1.5 py-0.2 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">+${item.delta_peso_kg} kg</span>`;
      } else if (item.delta_peso_kg < 0) {
        deltaHtml = `<span class="ml-1 px-1.5 py-0.2 rounded text-[10px] font-bold bg-rose-100 text-rose-800">${item.delta_peso_kg} kg</span>`;
      } else {
        deltaHtml = `<span class="ml-1 px-1.5 py-0.2 rounded text-[10px] font-medium bg-slate-100 text-slate-600">0.0 kg</span>`;
      }
    }

    // Ganancia en g/kg/día
    let gananciaHtml = '<span class="text-slate-300">-</span>';
    if (index > 0 && item.peso_kg && timeline[index - 1].peso_kg) {
      const pPrev = timeline[index - 1].peso_kg;
      const fAct = new Date(item.fecha);
      const fPrev = new Date(timeline[index - 1].fecha);
      const dias = Math.round((fAct - fPrev) / (1000 * 60 * 60 * 24));
      if (dias > 0 && pPrev > 0) {
        const gKgD = Math.round(((item.peso_kg - pPrev) * 1000) / (pPrev * dias) * 10) / 10;
        if (gKgD >= 5) {
          gananciaHtml = `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800">+${gKgD} g/kg/d</span>`;
        } else if (gKgD > 0) {
          gananciaHtml = `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-900" title="Ganancia menor a 5 g/kg/día">+${gKgD} g/kg/d</span>`;
        } else {
          gananciaHtml = `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-rose-100 text-rose-800" title="Pérdida o estancamiento">${gKgD} g/kg/d</span>`;
        }
      }
    }

    // Badge Z-Score
    let zScoreBadge = '<span class="text-slate-300">-</span>';
    if (item.zscore !== null && item.zscore !== undefined) {
      const zColor = item.zscore < -2 ? 'text-rose-600 bg-rose-50 border-rose-200' : (item.zscore < -1 ? 'text-amber-700 bg-amber-50 border-amber-200' : 'text-emerald-700 bg-emerald-50 border-emerald-200');
      zScoreBadge = `<span class="font-mono font-bold px-2 py-0.5 rounded border ${zColor}">${item.zscore}</span>`;
    }

    const badgeDx = item.clasificacion ? `
      <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold ${obtenerClaseBadge(item.clasificacion)}">
        ${item.clasificacion}
      </span>
    ` : '<span class="text-slate-300">-</span>';

    tr.innerHTML = `
      <td class="py-2.5 px-3.5 font-bold text-slate-800 whitespace-nowrap">
        <span class="mr-1">${item.icono}</span>
        <span>${item.tipo_hito}</span>
      </td>
      <td class="py-2.5 px-3.5 font-mono text-slate-600 whitespace-nowrap">${item.fecha}</td>
      <td class="py-2.5 px-3.5 text-center whitespace-nowrap font-medium text-slate-900">
        ${item.peso_kg ? `<strong>${item.peso_kg} kg</strong> ${deltaHtml}` : '-'}
      </td>
      <td class="py-2.5 px-3.5 text-center whitespace-nowrap text-slate-700">${item.talla_cm ? item.talla_cm + ' cm' : '-'}</td>
      <td class="py-2.5 px-3.5 text-center whitespace-nowrap text-slate-700">${item.pb_cm ? item.pb_cm + ' cm' : '-'}</td>
      <td class="py-2.5 px-3.5 text-center whitespace-nowrap">${zScoreBadge}</td>
      <td class="py-2.5 px-3.5 text-center whitespace-nowrap">${gananciaHtml}</td>
      <td class="py-2.5 px-3.5 whitespace-nowrap">${badgeDx}</td>
      <td class="py-2.5 px-3.5 text-center whitespace-nowrap font-bold text-sky-800">
        ${item.sobres_ftlc > 0 ? `🍫 ${item.sobres_ftlc}` : '-'}
      </td>
      <td class="py-2.5 px-3.5 text-right whitespace-nowrap">
        <button onclick="abrirModalDetalleHito(${index})" class="text-[11px] font-bold text-sky-700 hover:text-sky-900 bg-sky-50 hover:bg-sky-100 px-2 py-1 rounded transition border border-sky-200">
          🔍 Ver Ficha
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderizarTimelineVertical(timeline) {
  const container = document.getElementById("exp-timeline-vertical");
  if (!container) return;
  container.innerHTML = "";

  if (timeline.length === 0) {
    container.innerHTML = '<p class="text-xs text-slate-400 py-2">No hay eventos para la línea de tiempo.</p>';
    return;
  }

  const total = timeline.length;
  const colapsable = total > 6;
  const expandido = AppState.timelineIntermediosExpandidos;

  timeline.forEach((item, index) => {
    const esIntermedio = colapsable && index >= 3 && index < (total - 2);

    if (colapsable && index === 3 && !expandido) {
      const cantOcultos = total - 5;
      const accordBtn = document.createElement("div");
      accordBtn.className = "py-2 my-1";
      accordBtn.innerHTML = `
        <button onclick="toggleExpandirTimeline()" class="inline-flex items-center px-4 py-2 rounded-xl text-xs font-bold bg-white hover:bg-sky-50 text-sky-700 border border-sky-300 shadow-sm transition space-x-2">
          <span>🔽</span>
          <span>Ver ${cantOcultos} controles intermedios (${timeline[3].fecha} a ${timeline[total - 3].fecha})</span>
        </button>
      `;
      container.appendChild(accordBtn);
    }

    if (esIntermedio && !expandido) {
      return;
    }

    const node = document.createElement("div");
    node.className = "relative group";

    let dotColor = "text-sky-500 bg-sky-500 ring-sky-200";
    if (item.tipo_hito.includes("Captación")) dotColor = "text-amber-500 bg-amber-500 ring-amber-200";
    else if (item.tipo_hito.includes("GBAI")) dotColor = "text-blue-500 bg-blue-500 ring-blue-200";
    else if (item.tipo_hito.includes("Seguimiento")) dotColor = "text-emerald-500 bg-emerald-500 ring-emerald-200";
    else if (item.tipo_hito.includes("Cierre")) dotColor = "text-rose-500 bg-rose-500 ring-rose-200";

    node.innerHTML = `
      <div class="absolute -left-[30px] top-3.5 w-3.5 h-3.5 rounded-full ${dotColor} ring-4 bg-white border-2 border-current transition-transform group-hover:scale-125"></div>
      
      <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs hover:border-sky-400 hover:shadow-md transition">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pb-2 border-b border-slate-100">
          <div class="flex items-center space-x-2">
            <span class="text-base">${item.icono}</span>
            <strong class="text-slate-800 text-xs sm:text-sm font-bold">${item.tipo_hito}</strong>
            ${item.clasificacion ? `<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${obtenerClaseBadge(item.clasificacion)}">${item.clasificacion}</span>` : ''}
          </div>
          <span class="font-mono text-xs text-slate-500 font-semibold">${item.fecha}</span>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2 text-xs text-slate-600">
          <div><span class="text-slate-400 text-[11px]">Peso:</span> <strong>${item.peso_kg ? item.peso_kg + ' kg' : '-'}</strong></div>
          <div><span class="text-slate-400 text-[11px]">Talla:</span> <strong>${item.talla_cm ? item.talla_cm + ' cm' : '-'}</strong></div>
          <div><span class="text-slate-400 text-[11px]">PB:</span> <strong>${item.pb_cm ? item.pb_cm + ' cm' : '-'}</strong></div>
          <div><span class="text-slate-400 text-[11px]">Z-Score:</span> <strong class="${item.zscore < -2 ? 'text-rose-600' : 'text-slate-800'}">${item.zscore ?? '-'}</strong></div>
        </div>

        <div class="mt-2.5 pt-2 border-t border-slate-50 flex items-center justify-between text-xs">
          <span class="text-slate-500 truncate max-w-md">${item.detalle || 'Sin observaciones'}</span>
          <button onclick="abrirModalDetalleHito(${index})" class="text-sky-600 hover:text-sky-800 font-bold flex items-center space-x-1 shrink-0 ml-2">
            <span>Ver Ficha ➔</span>
          </button>
        </div>
      </div>
    `;
    container.appendChild(node);
  });

  if (colapsable && expandido) {
    const collapseBtn = document.createElement("div");
    collapseBtn.className = "pt-2";
    collapseBtn.innerHTML = `
      <button onclick="toggleExpandirTimeline()" class="px-4 py-2 rounded-xl text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 transition">
        ▲ Plegar controles intermedios
      </button>
    `;
    container.appendChild(collapseBtn);
  }
}

function toggleExpandirTimeline() {
  AppState.timelineIntermediosExpandidos = !AppState.timelineIntermediosExpandidos;
  renderizarTimelineVertical(AppState.timelineActual || []);
}

function renderizarTarjetasPaginadas() {
  const container = document.getElementById("exp-tarjetas-grid");
  const infoEl = document.getElementById("exp-tarjetas-paginacion-info");
  const indEl = document.getElementById("exp-tarjetas-indicador");
  const btnAnt = document.getElementById("btn-tarjetas-ant");
  const btnSig = document.getElementById("btn-tarjetas-sig");

  if (!container) return;
  container.innerHTML = "";

  const timeline = AppState.timelineActual || [];
  const total = timeline.length;
  const porPagina = AppState.tarjetasPorPagina || 4;
  const totalPaginas = Math.ceil(total / porPagina) || 1;
  const pag = Math.min(Math.max(AppState.paginaTarjetas || 0, 0), totalPaginas - 1);
  AppState.paginaTarjetas = pag;

  const inicio = pag * porPagina;
  const fin = Math.min(inicio + porPagina, total);
  const paginaItems = timeline.slice(inicio, fin);

  if (infoEl) infoEl.innerText = `Mostrando ${inicio + 1} a ${fin} de ${total} hitos`;
  if (indEl) indEl.innerText = `${pag + 1} / ${totalPaginas}`;
  if (btnAnt) btnAnt.disabled = pag === 0;
  if (btnSig) btnSig.disabled = pag >= totalPaginas - 1;

  if (paginaItems.length === 0) {
    container.innerHTML = '<p class="col-span-4 text-xs text-slate-400 py-4 text-center">No hay hitos para mostrar.</p>';
    return;
  }

  paginaItems.forEach((item, idx) => {
    const realIndex = inicio + idx;
    const card = document.createElement("div");
    card.className = "bg-white p-3.5 rounded-2xl border-2 border-slate-200 shadow-sm flex flex-col justify-between hover:border-sky-500 hover:shadow-md cursor-pointer transition-all duration-150 transform hover:-translate-y-0.5 group";
    card.onclick = () => abrirModalDetalleHito(realIndex);

    let badgeColor = "bg-slate-100 text-slate-700";
    if (item.tipo_hito.includes("Captación")) badgeColor = "bg-amber-100 text-amber-800 border-amber-300";
    else if (item.tipo_hito.includes("GBAI")) badgeColor = "bg-blue-100 text-blue-800 border-blue-300";
    else if (item.tipo_hito.includes("Primera")) badgeColor = "bg-sky-100 text-sky-800 border-sky-300";
    else if (item.tipo_hito.includes("Seguimiento")) badgeColor = "bg-emerald-100 text-emerald-800 border-emerald-300";
    else if (item.tipo_hito.includes("Cierre")) badgeColor = "bg-rose-100 text-rose-800 border-rose-300";

    let antropometriaHtml = "";
    if (item.peso_kg || item.zscore !== null && item.zscore !== undefined) {
      antropometriaHtml = `
        <div class="mt-2 pt-2 border-t border-slate-100 grid grid-cols-2 gap-1 text-[11px]">
          <div><span class="text-slate-400">Peso:</span> <strong class="text-slate-800">${item.peso_kg ? item.peso_kg + ' kg' : '-'}</strong></div>
          <div><span class="text-slate-400">Talla:</span> <strong class="text-slate-800">${item.talla_cm ? item.talla_cm + ' cm' : '-'}</strong></div>
          <div><span class="text-slate-400">PB:</span> <strong class="text-slate-800">${item.pb_cm ? item.pb_cm + ' cm' : '-'}</strong></div>
          <div><span class="text-slate-400">Z-Score:</span> <strong class="${item.zscore < -2 ? 'text-rose-600' : (item.zscore < -1 ? 'text-amber-600' : 'text-emerald-600')}">${item.zscore ?? '-'}</strong></div>
        </div>
      `;
    }

    card.innerHTML = `
      <div>
        <div class="flex items-center justify-between mb-1.5">
          <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border ${badgeColor}">
            ${item.icono} ${item.tipo_hito}
          </span>
          <span class="text-[11px] font-mono text-slate-500 font-semibold">${item.fecha}</span>
        </div>
        <p class="text-[11px] text-slate-600 line-clamp-2 mt-1 leading-relaxed">${item.detalle || ''}</p>
        ${antropometriaHtml}
      </div>
      <div class="mt-2.5 pt-2 border-t border-slate-100 flex items-center justify-between text-[10px]">
        ${item.sobres_ftlc > 0 ? `<span class="font-bold text-sky-700 bg-sky-50 px-2 py-0.5 rounded">🍫 ${item.sobres_ftlc} sobres FTLC</span>` : '<span class="text-slate-400 italic">Intervención clínica</span>'}
        <span class="font-bold text-sky-600 group-hover:text-sky-800 flex items-center space-x-1">
          <span>Ver Ficha ➔</span>
        </span>
      </div>
    `;
    container.appendChild(card);
  });
}

function cambiarPaginaTarjetas(delta) {
  AppState.paginaTarjetas = (AppState.paginaTarjetas || 0) + delta;
  renderizarTarjetasPaginadas();
}

function irAUltimaPaginaTarjetas() {
  const total = (AppState.timelineActual || []).length;
  const porPagina = AppState.tarjetasPorPagina || 4;
  AppState.paginaTarjetas = Math.max(0, Math.ceil(total / porPagina) - 1);
  renderizarTarjetasPaginadas();
}

function renderizarCurvaEvolucionTrazabilidad(timeline) {
  const ctx = document.getElementById("chart-curva-evolucion");
  if (!ctx) return;

  // Filtrar solo hitos con mediciones antropométricas y ordenar estrictamente por fecha
  const puntosMedicion = timeline
    .filter(item => item.zscore !== null && item.zscore !== undefined || item.peso_kg !== null && item.peso_kg !== undefined)
    .sort((a, b) => new Date(a.fecha) - new Date(b.fecha));

  const labels = puntosMedicion.map(p => `${p.tipo_hito.replace("Seguimiento", "Ctrl")} (${p.fecha})`);
  const datosZScore = puntosMedicion.map(p => p.zscore);
  const datosPeso = puntosMedicion.map(p => p.peso_kg);

  if (AppState.charts.curva) AppState.charts.curva.destroy();
  AppState.charts.curva = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Puntaje Z (P/T)",
          data: datosZScore,
          borderColor: "#0284c7",
          backgroundColor: "rgba(2, 132, 199, 0.1)",
          yAxisID: "yZ",
          borderWidth: 2.5,
          pointRadius: 6,
          pointHoverRadius: 8,
          pointBackgroundColor: "#0284c7",
          tension: 0.2
        },
        {
          label: "Peso Corporal (kg)",
          data: datosPeso,
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          yAxisID: "yPeso",
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 5,
          pointBackgroundColor: "#10b981",
          tension: 0.2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "top", labels: { boxWidth: 14, font: { size: 12, weight: 'bold' } } }
      },
      scales: {
        yZ: {
          type: "linear",
          position: "left",
          title: { display: true, text: "Puntaje Z (P/T)", font: { weight: 'bold' } },
          suggestedMin: -3.5,
          suggestedMax: 1.5
        },
        yPeso: {
          type: "linear",
          position: "right",
          title: { display: true, text: "Peso Corporal (kg)", font: { weight: 'bold' } },
          grid: { drawOnChartArea: false }
        }
      }
    }
  });
}

function renderizarTablaTrazabilidad(timeline) {
  // Integrado en renderizarTablaKardexEvolucion
  return;
}

// =============================================================================
// MODALES Y FORMULARIOS DE ACCIÓN
// =============================================================================
function abrirModalDetalleHito(index) {
  if (!AppState.casoActual || !AppState.casoActual.detalle) return;
  const timeline = AppState.casoActual.detalle.timeline_trazabilidad || [];
  const item = timeline[index];
  if (!item) return;

  const r = AppState.casoActual.detalle.resumen || {};

  // Encabezado
  document.getElementById("mdh-icono").innerText = item.icono || "📍";
  document.getElementById("mdh-titulo").innerText = item.tipo_hito;
  document.getElementById("mdh-fecha").innerText = `Fecha del evento: ${item.fecha || "-"}`;

  const badgeDx = document.getElementById("mdh-clasificacion-badge");
  if (badgeDx) {
    if (item.clasificacion) {
      badgeDx.className = `px-2.5 py-0.5 rounded-full text-xs font-bold ${obtenerClaseBadge(item.clasificacion)}`;
      badgeDx.innerText = item.clasificacion;
      badgeDx.style.display = "inline-block";
    } else {
      badgeDx.style.display = "none";
    }
  }

  // Bloque 1: Identificación y Contacto
  document.getElementById("mdh-paciente").innerText = r.nombre_completo || "-";
  document.getElementById("mdh-doc-paciente").innerText = `${r.tipo_documento || ""} ${r.numero_documento || "-"}`;
  document.getElementById("mdh-municipio-sede").innerText = `${r.municipio || "-"} • ${r.sede_ipsi || "Sede Principal"}`;
  document.getElementById("mdh-cuidador").innerText = `${r.cuidador || "Sin dato registrado"}${r.documento_cuidador ? " (" + r.documento_cuidador + ")" : ""}`;
  document.getElementById("mdh-telefono").innerText = r.telefono_cuidador || "Sin teléfono registrado";
  
  const georrefEl = document.getElementById("mdh-georref");
  if (georrefEl) {
    const geoText = r.georreferenciacion || "Sin comunidad o dirección georreferenciada";
    georrefEl.innerText = geoText;
    georrefEl.title = geoText;
  }

  // Bloque 2: Antropometría y Variaciones Ponderales
  document.getElementById("mdh-peso").innerText = item.peso_kg ? `${item.peso_kg} kg` : "-";
  document.getElementById("mdh-talla").innerText = item.talla_cm ? `${item.talla_cm} cm` : "-";
  document.getElementById("mdh-pb").innerText = item.pb_cm ? `${item.pb_cm} cm` : "-";
  document.getElementById("mdh-zscore").innerText = item.zscore !== null && item.zscore !== undefined ? `${item.zscore}` : "-";

  const deltaPesoEl = document.getElementById("mdh-delta-peso");
  if (deltaPesoEl) {
    if (item.delta_peso_kg !== null && item.delta_peso_kg !== undefined && item.delta_peso_kg !== 0) {
      const signo = item.delta_peso_kg > 0 ? "+" : "";
      const gramos = Math.round(item.delta_peso_kg * 1000);
      deltaPesoEl.innerText = `${signo}${item.delta_peso_kg} kg (${signo}${gramos} g)`;
      deltaPesoEl.className = `block text-[10px] font-bold mt-0.5 ${item.delta_peso_kg > 0 ? 'text-emerald-600' : 'text-rose-600'}`;
    } else if (item.delta_peso_kg === 0) {
      deltaPesoEl.innerText = "Sin cambio ponderal";
      deltaPesoEl.className = "block text-[10px] text-slate-400 mt-0.5";
    } else {
      deltaPesoEl.innerText = "Línea base / Inicial";
      deltaPesoEl.className = "block text-[10px] text-slate-400 mt-0.5";
    }
  }

  const deltaZEl = document.getElementById("mdh-delta-z");
  if (deltaZEl) {
    if (item.delta_zscore !== null && item.delta_zscore !== undefined && item.delta_zscore !== 0) {
      const signo = item.delta_zscore > 0 ? "+" : "";
      deltaZEl.innerText = `${signo}${item.delta_zscore} DE`;
      deltaZEl.className = `block text-[10px] font-bold mt-0.5 ${item.delta_zscore > 0 ? 'text-emerald-600' : 'text-rose-600'}`;
    } else if (item.delta_zscore === 0) {
      deltaZEl.innerText = "Estable (0.00 DE)";
      deltaZEl.className = "block text-[10px] text-sky-600 mt-0.5";
    } else {
      deltaZEl.innerText = "Medición inicial";
      deltaZEl.className = "block text-[10px] text-slate-400 mt-0.5";
    }
  }

  // Bloque 3: Tratamiento y Clínica
  document.getElementById("mdh-tratamiento").innerText = item.tratamiento || "Sin tratamiento registrado";
  document.getElementById("mdh-sobres").innerText = item.sobres_ftlc ? `${item.sobres_ftlc} sobres` : "0 sobres";
  document.getElementById("mdh-apetito").innerText = item.prueba_apetito || "No aplica / No evaluada";
  document.getElementById("mdh-escenario").innerText = item.escenario_manejo || "Manejo ambulatorio";
  document.getElementById("mdh-comorbilidad").innerText = item.comorbilidad || "Ninguna reportada";
  document.getElementById("mdh-novedad").innerText = item.novedad || "Sin novedad especial";

  // Bloque 4: Próxima Cita Normativa
  const bloqueCita = document.getElementById("mdh-bloque-cita");
  if (bloqueCita) {
    if (item.fecha_proxima_cita || item.dias_proxima_cita) {
      bloqueCita.classList.remove("hidden");
      document.getElementById("mdh-cita-intervalo").innerText = item.dias_proxima_cita ? `Cada ${item.dias_proxima_cita} días normativos (${item.clasificacion || "Seguimiento"})` : "Programación médica clínica";
      document.getElementById("mdh-cita-fecha").innerText = item.fecha_proxima_cita || "Pendiente agendamiento";
    } else {
      bloqueCita.classList.add("hidden");
    }
  }

  // Bloque 5: Trazabilidad Institucional y Notificación
  document.getElementById("mdh-fuente").innerText = item.fuente_notificacion || r.fuente_notificacion || "Vigilancia en Salud Pública";
  document.getElementById("mdh-medio-afiliacion").innerText = `Medio: ${item.medio_notificacion || "Oficio / Correo"} • Afiliación: ${item.tipo_afiliacion || "Subsidiado"}`;
  document.getElementById("mdh-cooperante").innerText = item.cooperante || "Notificación comunitaria / Extramural";

  const gbaiCont = document.getElementById("mdh-contenedor-gbai");
  if (gbaiCont) {
    if (item.asignacion_interna || item.estado_busqueda) {
      gbaiCont.style.display = "block";
      document.getElementById("mdh-gbai").innerText = `Equipo: ${item.asignacion_interna || "Promotor GBAI"} • Estado: ${item.estado_busqueda || "Efectiva"}`;
    } else {
      gbaiCont.style.display = "none";
    }
  }

  document.getElementById("mdh-observaciones").innerText = item.observaciones || item.detalle || "Sin observaciones adicionales registradas.";

  // Mostrar modal
  document.getElementById("modal-detalle-hito").classList.remove("hidden");
}

function cerrarModalDetalleHito() {
  const modal = document.getElementById("modal-detalle-hito");
  if (modal) modal.classList.add("hidden");
}
function abrirModalNuevoControl(casoId, nombrePaciente) {
  document.getElementById("modal-control-caso-id").value = casoId;
  document.getElementById("modal-control-nombre").innerText = nombrePaciente;
  document.getElementById("control-fecha").valueAsDate = new Date();
  document.getElementById("modal-nuevo-control").classList.remove("hidden");
}

function cerrarModalNuevoControl() {
  document.getElementById("modal-nuevo-control").classList.add("hidden");
}

function abrirModalCerrarCaso(casoId, nombrePaciente) {
  document.getElementById("modal-cierre-caso-id").value = casoId;
  document.getElementById("modal-cierre-nombre").innerText = nombrePaciente;
  document.getElementById("cierre-fecha").valueAsDate = new Date();
  document.getElementById("modal-cerrar-caso").classList.remove("hidden");
}

function cerrarModalCierre() {
  document.getElementById("modal-cerrar-caso").classList.add("hidden");
}

function configurarFormularios() {
  // Formulario Nuevo Control
  const formCtrl = document.getElementById("form-nuevo-control");
  if (formCtrl) {
    formCtrl.addEventListener("submit", async (e) => {
      e.preventDefault();
      const casoId = document.getElementById("modal-control-caso-id").value;
      const payload = {
        fecha_control: document.getElementById("control-fecha").value,
        peso_kg: parseFloat(document.getElementById("control-peso").value) || null,
        talla_cm: parseFloat(document.getElementById("control-talla").value) || null,
        perimetro_braquial_cm: parseFloat(document.getElementById("control-pb").value) || null,
        z_score: parseFloat(document.getElementById("control-zscore").value) || null,
        tratamiento: document.getElementById("control-tratamiento").value || null,
        sobres_ftlc_entregados: parseInt(document.getElementById("control-sobres").value) || 0,
        novedad_id: parseInt(document.getElementById("control-novedad").value) || null,
        observaciones: document.getElementById("control-observaciones").value || null
      };

      try {
        const res = await fetch(`${API_BASE}/api/casos/${casoId}/controles`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error("Error al guardar control");
        alert("Control de seguimiento registrado con éxito.");
        cerrarModalNuevoControl();
        verDetalleCaso(casoId);
      } catch (err) {
        console.error("Error guardando control:", err);
        alert("Error al registrar el control.");
      }
    });
  }

  // Formulario Cerrar Caso
  const formCierre = document.getElementById("form-cerrar-caso");
  if (formCierre) {
    formCierre.addEventListener("submit", async (e) => {
      e.preventDefault();
      const casoId = document.getElementById("modal-cierre-caso-id").value;
      const payload = {
        motivo_egreso: document.getElementById("cierre-motivo").value,
        fecha_egreso: document.getElementById("cierre-fecha").value,
        observaciones: document.getElementById("cierre-observaciones").value || null
      };

      try {
        const res = await fetch(`${API_BASE}/api/casos/${casoId}/cerrar`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error("Error al cerrar caso");
        alert("Caso cerrado exitosamente.");
        cerrarModalCierre();
        verDetalleCaso(casoId);
      } catch (err) {
        console.error("Error al cerrar caso:", err);
        alert("No se pudo cerrar el caso.");
      }
    });
  }

  // Formulario Registro de Nuevo Caso (FT-003)
  const formNuevoCaso = document.getElementById("form-nuevo-caso");
  if (formNuevoCaso) {
    formNuevoCaso.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        paciente: {
          tipo_documento: document.getElementById("nuevo-tipo-doc").value,
          numero_documento: document.getElementById("nuevo-doc-paciente").value.trim(),
          primer_nombre: document.getElementById("nuevo-primer-nombre").value.trim().toUpperCase(),
          segundo_nombre: document.getElementById("nuevo-segundo-nombre").value.trim().toUpperCase() || null,
          primer_apellido: document.getElementById("nuevo-primer-apellido").value.trim().toUpperCase(),
          segundo_apellido: document.getElementById("nuevo-segundo-apellido").value.trim().toUpperCase() || null,
          sexo: document.getElementById("nuevo-sexo").value,
          fecha_nacimiento: document.getElementById("nuevo-fecha-nac").value,
          municipio_id: parseInt(document.getElementById("nuevo-municipio").value) || null,
          georreferenciacion: document.getElementById("nuevo-georref").value || null,
          cuidador: {
            nombre_completo: document.getElementById("nuevo-cuidador-nombre").value.trim().toUpperCase(),
            documento_cuidador: document.getElementById("nuevo-cuidador-doc").value.trim() || null,
            telefono: document.getElementById("nuevo-cuidador-tel").value.trim() || null
          }
        },
        fuente_notificacion: document.getElementById("nuevo-fuente-notif").value,
        fecha_notificacion: document.getElementById("nuevo-fecha-notif").value || null,
        cooperante_notificador: document.getElementById("nuevo-cooperante").value || null,
        medio_notificacion: document.getElementById("nuevo-medio-notif").value || null,
        eapb_id: parseInt(document.getElementById("nuevo-eapb").value) || null,
        ips_primaria_id: parseInt(document.getElementById("nuevo-sede").value) || null,
        fecha_primera_atencion: document.getElementById("nuevo-fecha-atenc").value || null,
        peso_atencion_kg: parseFloat(document.getElementById("nuevo-peso-atenc").value) || null,
        talla_atencion_cm: parseFloat(document.getElementById("nuevo-talla-atenc").value) || null,
        pb_atencion_cm: parseFloat(document.getElementById("nuevo-pb-atenc").value) || null,
        zscore_atencion: parseFloat(document.getElementById("nuevo-zscore-atenc").value) || null,
        prueba_apetito: document.getElementById("nuevo-prueba-apetito").value || null,
        tratamiento_inicial: document.getElementById("nuevo-tratamiento").value || null,
        sobres_ftlc_inicial: parseInt(document.getElementById("nuevo-sobres-ftlc").value) || 0
      };

      try {
        const res = await fetch(`${API_BASE}/api/casos`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error("Error en la creación del caso");
        const respData = await res.json();
        alert(`¡Caso registrado exitosamente con ID #${respData.caso_id}!`);
        formNuevoCaso.reset();
        activarPestana("tab-casos");
      } catch (err) {
        console.error("Error al registrar nuevo caso:", err);
        alert("Ocurrió un error al registrar el caso en el sistema.");
      }
    });
  }
}

// =============================================================================
// MÓDULO 4: INDICADORES MENSUALES Y EXPORTACIÓN A EXCEL
// =============================================================================
async function cargarIndicadores(anioSeleccionado = null) {
  const container = document.getElementById("contenedor-indicadores-matriz");
  if (!container) return;
  container.innerHTML = '<p class="text-center py-8 text-slate-500 font-medium">Cargando matriz mensual de indicadores...</p>';

  try {
    const url = anioSeleccionado ? `${API_BASE}/api/reportes/indicadores-mensuales?anio=${anioSeleccionado}` : `${API_BASE}/api/reportes/indicadores-mensuales`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Error al obtener indicadores");
    const data = await res.json();

    // Poblar selector dinámico de años detectados automáticamente en la BD
    const selAnio = document.getElementById("indicadores-filtro-anio");
    if (selAnio && data.anios_disponibles) {
      selAnio.innerHTML = data.anios_disponibles.map(a => 
        `<option value="${a}" ${a === data.anio ? "selected" : ""}>Año ${a}</option>`
      ).join("");
    }

    const meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

    function generarHtmlMatriz(titulo, subtitulo, icono, datosMatriz, colorTema) {
      const municipios = Object.keys(datosMatriz).sort();
      if (municipios.length === 0) {
        return `
          <div class="mb-8 bg-white rounded-xl border border-slate-200 p-5">
            <h4 class="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
              <span>${icono}</span>
              <span>${titulo}</span>
            </h4>
            <p class="text-xs text-slate-400 py-4 text-center">No se registran eventos en este año.</p>
          </div>
        `;
      }

      // Totales por mes (columnas)
      const totalesColumna = { 1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0, 8:0, 9:0, 10:0, 11:0, 12:0 };
      let granTotalAnual = 0;

      let filasHtml = "";
      municipios.forEach(mun => {
        const valMeses = datosMatriz[mun];
        const filaTotal = Object.values(valMeses).reduce((a, b) => a + b, 0);
        granTotalAnual += filaTotal;

        for (let m = 1; m <= 12; m++) {
          totalesColumna[m] += (valMeses[m] || 0);
        }

        filasHtml += `
          <tr class="border-b hover:bg-slate-50 transition-colors">
            <td class="py-2.5 px-3 font-semibold text-slate-800">${mun}</td>
            ${[1,2,3,4,5,6,7,8,9,10,11,12].map(m => {
              const cant = valMeses[m] || 0;
              return `<td class="py-2.5 px-2 text-center ${cant > 0 ? `font-bold text-${colorTema}-700 bg-${colorTema}-50/30` : 'text-slate-300'}">${cant > 0 ? cant : '-'}</td>`;
            }).join("")}
            <td class="py-2.5 px-3 text-center font-bold bg-slate-50 text-slate-900">${filaTotal.toLocaleString()}</td>
          </tr>
        `;
      });

      return `
        <div class="mb-8 bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
          <div class="p-3 bg-slate-50 border-b border-slate-200 flex flex-col sm:flex-row justify-between sm:items-center gap-1">
            <h4 class="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center space-x-1.5">
              <span>${icono}</span>
              <span>${titulo}</span>
            </h4>
            <span class="text-xs font-bold text-${colorTema}-800 bg-${colorTema}-100 px-2.5 py-0.5 rounded-full border border-${colorTema}-200">
              Total ${data.anio}: ${granTotalAnual.toLocaleString()} eventos
            </span>
          </div>
          <div class="overflow-x-auto custom-scrollbar">
            <table class="w-full text-xs text-left">
              <thead class="bg-slate-100 text-slate-600 font-bold border-b border-slate-200">
                <tr>
                  <th class="py-2.5 px-3">Municipio</th>
                  ${meses.map(m => `<th class="py-2.5 px-2 text-center">${m}</th>`).join("")}
                  <th class="py-2.5 px-3 text-center bg-slate-200 text-slate-800">Total Anual</th>
                </tr>
              </thead>
              <tbody>
                ${filasHtml}
              </tbody>
              <tfoot class="bg-slate-100/90 font-bold border-t-2 border-slate-300 text-slate-800">
                <tr>
                  <td class="py-2.5 px-3 font-black uppercase text-[11px]">TOTAL MENSUAL</td>
                  ${[1,2,3,4,5,6,7,8,9,10,11,12].map(m => `
                    <td class="py-2.5 px-2 text-center font-black ${totalesColumna[m] > 0 ? `text-${colorTema}-800` : 'text-slate-400'}">
                      ${totalesColumna[m] > 0 ? totalesColumna[m].toLocaleString() : '-'}
                    </td>
                  `).join("")}
                  <td class="py-2.5 px-3 text-center font-black bg-slate-200 text-slate-900">${granTotalAnual.toLocaleString()}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      `;
    }

    let html = "";
    // 1. Matriz de Notificaciones
    html += generarHtmlMatriz(
      `1. Matriz de Notificaciones por Municipio (Año ${data.anio})`,
      "Casos notificados captados en el sistema por mes",
      "📋",
      data.por_fecha_notificacion || {},
      "sky"
    );

    // 2. Matriz de Primeras Atenciones en IPSI
    html += generarHtmlMatriz(
      `2. Matriz de Primeras Atenciones Clínicas en IPSI (Año ${data.anio})`,
      "Primer contacto e ingreso formal a la ruta",
      "🏥",
      data.por_fecha_primera_atencion || {},
      "emerald"
    );

    // 3. Matriz de Controles de Seguimiento
    html += generarHtmlMatriz(
      `3. Matriz de Controles Periódicos de Seguimiento (Año ${data.anio})`,
      "Consultas periódicas de evaluación nutricional realizadas",
      "📈",
      data.por_controles_seguimiento || {},
      "purple"
    );

    container.innerHTML = html;
  } catch (err) {
    console.error("Error al cargar indicadores:", err);
    container.innerHTML = '<p class="text-center py-8 text-rose-500 font-bold">Error al cargar matriz mensual de indicadores.</p>';
  }
}

function cambiarAnioIndicadores(anio) {
  cargarIndicadores(parseInt(anio));
}

function exportarExcel() {
  window.location.href = `${API_BASE}/api/reportes/exportar-excel`;
}

// =============================================================================
// MÓDULO 6: CARGA MASIVA Y SINCRONIZACIÓN EXCEL EPS
// =============================================================================

let archivoEPSSeleccionado = null;

function inicializarModuloImportacion() {
  const dropzone = document.getElementById("dropzone-excel-eps");
  const inputFile = document.getElementById("input-file-eps");

  if (!dropzone || !inputFile) return;

  // Drag and Drop
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("border-sky-500", "bg-sky-100/60");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("border-sky-500", "bg-sky-100/60");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("border-sky-500", "bg-sky-100/60");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      manejarArchivoSeleccionado(e.dataTransfer.files[0]);
    }
  });

  inputFile.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      manejarArchivoSeleccionado(e.target.files[0]);
    }
  });
}

function manejarArchivoSeleccionado(file) {
  if (!file) return;
  const nombre = file.name.toLowerCase();
  if (!nombre.endsWith(".xlsx") && !nombre.endsWith(".xls")) {
    alert("Por favor seleccione un archivo de hoja de cálculo Excel válido (.xlsx o .xls).");
    return;
  }

  archivoEPSSeleccionado = file;

  // Mostrar panel de confirmación
  document.getElementById("archivo-nombre-display").innerText = file.name;
  const tamanoKb = (file.size / 1024).toFixed(1);
  document.getElementById("archivo-tamano-display").innerText = `${tamanoKb} KB • Listo para procesar`;
  document.getElementById("contenedor-archivo-seleccionado").classList.remove("hidden");
  document.getElementById("contenedor-resultados-importacion").classList.add("hidden");
}

function cancelarArchivoSeleccionado() {
  archivoEPSSeleccionado = null;
  const input = document.getElementById("input-file-eps");
  if (input) input.value = "";
  document.getElementById("contenedor-archivo-seleccionado").classList.add("hidden");
  document.getElementById("contenedor-resultados-importacion").classList.add("hidden");
}

async function subirYProcesarExcelEPS() {
  if (!archivoEPSSeleccionado) {
    alert("No hay ningún archivo seleccionado.");
    return;
  }

  const contenedorProcesando = document.getElementById("contenedor-procesando-excel");
  const contenedorResultados = document.getElementById("contenedor-resultados-importacion");
  const btnProcesar = document.getElementById("btn-procesar-excel-eps");

  try {
    btnProcesar.disabled = true;
    contenedorProcesando.classList.remove("hidden");
    contenedorResultados.classList.add("hidden");

    const formData = new FormData();
    formData.append("file", archivoEPSSeleccionado);

    const res = await fetch(`${API_BASE}/api/importacion/subir-excel`, {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "Error al procesar el archivo Excel.");
    }

    const data = await res.json();

    // Renderizar resultados
    document.getElementById("res-pacientes-creados").innerText = data.pacientes_creados || 0;
    document.getElementById("res-pacientes-actualizados").innerText = data.pacientes_actualizados || 0;
    document.getElementById("res-controles-nuevos").innerText = data.controles_nuevos || 0;
    document.getElementById("res-controles-actualizados").innerText = data.controles_actualizados || 0;

    document.getElementById("res-archivo-nombre").innerText = data.archivo || archivoEPSSeleccionado.name;
    document.getElementById("res-hojas-procesadas").innerText = (data.hojas_procesadas || []).join(", ") || "Hojas estándar";
    document.getElementById("res-tiempo-proceso").innerText = `${data.tiempo_segundos} segundos`;
    document.getElementById("res-total-movimientos").innerText = `${data.total_movimientos} registros impactados`;

    contenedorResultados.classList.remove("hidden");

    // Refrescar en segundo plano el dashboard y los casos
    cargarDashboard();
    cargarCasos();

  } catch (err) {
    console.error("Error al sincronizar Excel EPS:", err);
    alert(`Ocurrió un error al procesar el archivo: ${err.message}`);
  } finally {
    contenedorProcesando.classList.add("hidden");
    btnProcesar.disabled = false;
  }
}

function verCasosActualizados() {
  activarPestana("tab-casos");
  cargarCasos();
}

// =============================================================================
// MÓDULO 6: LIBRO OFICIAL DE NOTIFICADOS (FORMATO PM-RIA-FT-003)
// =============================================================================

async function cargarKpisNotificados() {
  try {
    const res = await fetch(`${API_BASE}/api/notificaciones/resumen-kpis`);
    if (!res.ok) return;
    const kpis = await res.json();

    const setKpi = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.innerText = (val ?? 0).toLocaleString();
    };

    setKpi("kpi-notif-total", kpis.total_notificados);
    setKpi("kpi-notif-113", kpis.evento_113_dnt);
    setKpi("kpi-notif-114", kpis.evento_114_riesgo);
    setKpi("kpi-notif-con-atencion", kpis.con_primera_atencion);
    setKpi("kpi-notif-sin-atencion", kpis.sin_primera_atencion);
    setKpi("kpi-notif-gbai", kpis.en_busqueda_gbai);
    setKpi("kpi-notif-seguimiento", kpis.en_seguimiento);
    setKpi("kpi-notif-cerrados", kpis.cerrados);
  } catch (err) {
    console.error("Error al cargar KPIs de notificados:", err);
  }
}

async function cargarNotificados() {
  const tbody = document.getElementById("tabla-notificados-body");
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="9" class="text-center py-8 text-slate-500 font-medium">Cargando libro oficial de notificados (FT-003)...</td></tr>';

  try {
    const f = AppState.filtrosNotificados;
    const params = new URLSearchParams();

    if (f.evento) params.append("evento", f.evento);
    if (f.primera_atencion) params.append("primera_atencion", f.primera_atencion);
    if (f.municipio) params.append("municipio", f.municipio);
    if (f.eapb) params.append("eapb", f.eapb);
    if (f.estado_caso) params.append("estado_caso", f.estado_caso);
    if (f.busqueda) params.append("busqueda", f.busqueda);

    const limit = f.limit || 50;
    const page = f.page || 1;
    const offset = (page - 1) * limit;

    params.append("limit", limit.toString());
    params.append("offset", offset.toString());

    const res = await fetch(`${API_BASE}/api/notificaciones?${params.toString()}`);
    if (!res.ok) throw new Error("Error en respuesta de la API de notificaciones");

    const headerTotal = res.headers.get("X-Total-Count");
    const notificados = await res.json();
    AppState.notificados = notificados;
    AppState.totalNotificados = headerTotal !== null ? parseInt(headerTotal) : notificados.length;

    renderizarTablaNotificados(notificados);
    actualizarPaginacionNotificados();

  } catch (err) {
    console.error("Error al listar notificados:", err);
    tbody.innerHTML = `<tr><td colspan="9" class="text-center py-6 text-rose-600 font-semibold">Error al cargar registros: ${err.message}</td></tr>`;
  }
}

function renderizarTablaNotificados(items) {
  const tbody = document.getElementById("tabla-notificados-body");
  if (!tbody) return;

  if (!items || items.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" class="text-center py-10 text-slate-400">
          <div class="flex flex-col items-center justify-center space-y-2">
            <span class="text-3xl">🔍</span>
            <p class="font-semibold text-slate-600">No se encontraron notificaciones con los filtros aplicados</p>
            <p class="text-xs text-slate-400">Intente restablecer los filtros para ver todos los registros del libro FT-003</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = items.map(n => {
    // Badges de Evento SIVIGILA
    const es113 = (n.fuente_notificacion || "").includes("113");
    const badgeEvento = es113
      ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300">Ev. 113 DNT</span>`
      : `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">Ev. 114 Riesgo</span>`;

    // Captación inicial
    const tieneCaptacion = n.peso_inicial_kg !== null && n.peso_inicial_kg !== undefined;
    let badgeZScoreInicial = `<span class="text-slate-400">-</span>`;
    if (n.zscore_inicial !== null && n.zscore_inicial !== undefined) {
      const z = Number(n.zscore_inicial);
      let colorClass = "bg-emerald-100 text-emerald-800 border-emerald-300";
      if (z < -3) colorClass = "bg-rose-100 text-rose-800 border-rose-300";
      else if (z < -2) colorClass = "bg-orange-100 text-orange-800 border-orange-300";
      else if (z < -1) colorClass = "bg-amber-100 text-amber-800 border-amber-300";
      badgeZScoreInicial = `<span class="px-1.5 py-0.5 rounded text-[10px] font-bold font-mono border ${colorClass}">Z: ${z.toFixed(2)}</span>`;
    }

    // Búsqueda GBAI
    let infoGbai = `<span class="text-slate-400 text-[11px]">Sin registro</span>`;
    if (n.estado_busqueda || n.fecha_busqueda_gbai) {
      const est = n.estado_busqueda || "En proceso";
      let badgeGbai = "bg-slate-100 text-slate-700";
      if (est.toLowerCase().includes("efectiva")) badgeGbai = "bg-emerald-100 text-emerald-800";
      else if (est.toLowerCase().includes("busqueda") || est.toLowerCase().includes("búsqueda")) badgeGbai = "bg-sky-100 text-sky-800";
      else badgeGbai = "bg-amber-100 text-amber-800";

      infoGbai = `
        <div class="space-y-0.5">
          <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${badgeGbai}">${est}</span>
          <span class="block text-[10px] text-slate-500 font-mono">${n.fecha_busqueda_gbai || ""}</span>
        </div>
      `;
    }

    // Primera Atención IPSI
    let info1raAten = `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-orange-50 text-orange-700 border border-orange-200">Pendiente</span>`;
    if (n.fecha_primera_atencion) {
      const zAt = n.zscore_atencion !== null && n.zscore_atencion !== undefined ? `Z: ${Number(n.zscore_atencion).toFixed(2)}` : "";
      const ftlc = n.sobres_ftlc_inicial ? `<span class="text-[10px] text-amber-700 font-bold block">💊 ${n.sobres_ftlc_inicial} sobres FTLC</span>` : "";
      const apetito = n.prueba_apetito ? `<span class="text-[9px] text-slate-500 block">Apetito: ${n.prueba_apetito}</span>` : "";
      info1raAten = `
        <div class="space-y-0.5">
          <span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">Atendido</span>
          <span class="block text-[10px] font-mono text-slate-600 font-semibold">${n.fecha_primera_atencion}</span>
          <span class="block text-[10px] text-slate-500 font-mono">${n.peso_atencion_kg ? n.peso_atencion_kg + 'kg' : ''} ${zAt}</span>
          ${ftlc}
          ${apetito}
        </div>
      `;
    }

    // Alertas normativas de edad
    let badgeAlertaEdad = "";
    if (n.alerta_egreso_edad) {
      badgeAlertaEdad = `<span class="ml-1 px-1 py-0.2 rounded text-[9px] font-black bg-rose-100 text-rose-800 border border-rose-300" title="Debe salir de la ruta por cumplir ≥ 60 meses">≥60m</span>`;
    } else if (n.alerta_ingreso_fuera_rango) {
      badgeAlertaEdad = `<span class="ml-1 px-1 py-0.2 rounded text-[9px] font-bold bg-amber-100 text-amber-800 border border-amber-300" title="Ingresó con edad > 59 meses">>59m</span>`;
    }

    // Badge de Estado del Caso
    let badgeEstado = "bg-slate-100 text-slate-700";
    if (n.estado_caso === "En seguimiento") badgeEstado = "bg-sky-100 text-sky-800 border-sky-300";
    else if (n.estado_caso === "Cerrado") badgeEstado = "bg-slate-100 text-slate-600 border-slate-300";
    else if (n.estado_caso === "En Busqueda") badgeEstado = "bg-amber-100 text-amber-800 border-amber-300";

    return `
      <tr class="hover:bg-slate-50/80 transition-colors">
        <!-- 1. Caso / Paciente -->
        <td class="py-2.5 px-3">
          <div class="flex items-start space-x-2">
            <span class="px-1.5 py-0.5 bg-slate-100 rounded text-[10px] font-mono font-bold text-slate-600">#${n.caso_id}</span>
            <div>
              <div class="font-bold text-slate-900 hover:text-sky-700 cursor-pointer text-xs flex items-center" onclick="verDetalleCaso(${n.caso_id})">
                <span>${n.nombre_completo || "SIN NOMBRE"}</span>
                ${badgeAlertaEdad}
              </div>
              <div class="text-[11px] text-slate-500 font-mono mt-0.5">
                <span class="font-semibold text-slate-700">${n.tipo_documento || "RC"}:</span> ${n.numero_documento}
                <span class="ml-1 text-slate-400">• ${n.sexo || "-"} • ${n.edad_meses_actual ?? n.edad_meses_notificacion ?? "-"}m</span>
              </div>
            </div>
          </div>
        </td>

        <!-- 2. Ubicación & EAPB -->
        <td class="py-2.5 px-3">
          <div class="font-semibold text-slate-800 text-xs">${n.municipio || "-"}</div>
          <div class="text-[10px] text-slate-500 truncate max-w-[150px]" title="${n.georreferenciacion || '-'}">
            ${n.georreferenciacion || "Sin comunidad"}
          </div>
          <div class="text-[10px] text-sky-700 font-medium mt-0.5">
            ${n.eapb || "-"} ${n.tipo_afiliacion ? `• <span class="text-slate-400">${n.tipo_afiliacion}</span>` : ""}
          </div>
        </td>

        <!-- 3. Contacto Cuidador -->
        <td class="py-2.5 px-3">
          <div class="text-xs font-medium text-slate-800">${n.cuidador || "No registrado"}</div>
          ${n.documento_cuidador ? `<div class="text-[10px] text-slate-400 font-mono">CC: ${n.documento_cuidador}</div>` : ""}
          <div class="text-[11px] font-mono font-bold text-sky-700 mt-0.5 flex items-center space-x-1">
            ${n.telefono_cuidador ? `<span>📞 ${n.telefono_cuidador}</span>` : `<span class="text-slate-400 font-normal">Sin tel</span>`}
          </div>
        </td>

        <!-- 4. Notificación -->
        <td class="py-2.5 px-3">
          <div class="flex flex-col space-y-1">
            ${badgeEvento}
            <span class="text-[10px] text-slate-600 font-mono">${n.fecha_notificacion || "Sin fecha"}</span>
            <span class="text-[10px] text-slate-500 truncate max-w-[140px]" title="${n.cooperante_notificador || ''}">
              ${n.cooperante_notificador || "IPS / Territorial"}
            </span>
            ${n.medio_notificacion ? `<span class="text-[9px] text-slate-400 font-mono">Vía: ${n.medio_notificacion}</span>` : ""}
          </div>
        </td>

        <!-- 5. Captación Inicial -->
        <td class="py-2.5 px-3">
          ${tieneCaptacion ? `
            <div class="space-y-0.5">
              <div class="text-[11px] font-mono font-semibold text-slate-800">
                ${n.peso_inicial_kg}kg • ${n.talla_inicial_cm}cm
              </div>
              <div class="text-[10px] text-slate-500">
                PB: ${n.pb_inicial_cm ? n.pb_inicial_cm + 'cm' : '-'} • ${badgeZScoreInicial}
              </div>
              <div class="text-[10px] text-slate-400 font-mono">${n.fecha_captacion || ""}</div>
            </div>
          ` : `<span class="text-slate-400 text-[11px]">Sin medidas</span>`}
        </td>

        <!-- 6. Búsqueda GBAI -->
        <td class="py-2.5 px-3">
          ${infoGbai}
          ${n.asignacion_interna ? `<span class="text-[9px] text-slate-500 block truncate max-w-[120px] mt-0.5" title="${n.asignacion_interna}">👤 ${n.asignacion_interna}</span>` : ""}
        </td>

        <!-- 7. Primera Atención IPSI -->
        <td class="py-2.5 px-3">
          ${info1raAten}
        </td>

        <!-- 8. Estado del Caso -->
        <td class="py-2.5 px-3 text-center">
          <span class="px-2 py-0.5 rounded-full text-[10px] font-bold border ${badgeEstado}">
            ${n.estado_caso || "Sin estado"}
          </span>
        </td>

        <!-- 9. Acciones -->
        <td class="py-2.5 px-3 text-right">
          <div class="flex items-center justify-end space-x-1">
            <button onclick="verDetalleCaso(${n.caso_id})" title="Ver Expediente y Ruta" class="p-1 rounded text-slate-500 hover:text-sky-600 hover:bg-sky-50 transition">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>
            </button>
            <button onclick="imprimirExpedientePorId(${n.caso_id})" title="Imprimir Reporte Clínico Oficial" class="p-1 rounded text-slate-500 hover:text-emerald-600 hover:bg-emerald-50 transition">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"></path></svg>
            </button>
            <button onclick="abrirModalEditarNotificacion(${n.caso_id})" title="Editar Notificación (FT-003)" class="p-1 rounded text-slate-500 hover:text-amber-600 hover:bg-amber-50 transition">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

function actualizarPaginacionNotificados() {
  const f = AppState.filtrosNotificados;
  const total = AppState.totalNotificados;
  const limit = f.limit || 50;
  const page = f.page || 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  // Texto contador superior
  const start = total === 0 ? 0 : (page - 1) * limit + 1;
  const end = Math.min(page * limit, total);
  
  const contSup = document.getElementById("contador-notif-mostrados");
  if (contSup) contSup.innerText = `Mostrando ${start.toLocaleString()} - ${end.toLocaleString()} de ${total.toLocaleString()} notificaciones`;

  const contInf = document.getElementById("contador-notif-inferior");
  if (contInf) contInf.innerText = `Página ${page} de ${totalPages} • Total ${total.toLocaleString()} registros`;

  // Indicadores
  const indSup = document.getElementById("indicador-pag-notif");
  if (indSup) indSup.innerText = `${page} / ${totalPages}`;

  const indInf = document.getElementById("indicador-pag-notif-inf");
  if (indInf) indInf.innerText = `${page} / ${totalPages}`;

  // Botones
  const btnAntSup = document.getElementById("btn-pag-notif-ant");
  const btnSigSup = document.getElementById("btn-pag-notif-sig");
  const btnAntInf = document.getElementById("btn-pag-notif-ant-inf");
  const btnSigInf = document.getElementById("btn-pag-notif-sig-inf");

  const deshabAnt = page <= 1;
  const deshabSig = page >= totalPages;

  if (btnAntSup) btnAntSup.disabled = deshabAnt;
  if (btnSigSup) btnSigSup.disabled = deshabSig;
  if (btnAntInf) btnAntInf.disabled = deshabAnt;
  if (btnSigInf) btnSigInf.disabled = deshabSig;
}

function cambiarPaginaNotificados(delta) {
  const f = AppState.filtrosNotificados;
  const limit = f.limit || 50;
  const totalPages = Math.max(1, Math.ceil(AppState.totalNotificados / limit));
  const nuevaPag = (f.page || 1) + delta;

  if (nuevaPag >= 1 && nuevaPag <= totalPages) {
    f.page = nuevaPag;
    cargarNotificados();
  }
}

function configurarEventosFiltrosNotificados() {
  // Búsqueda con debounce
  const inputBusq = document.getElementById("filtro-notif-busqueda");
  let timerBusq = null;
  if (inputBusq) {
    inputBusq.addEventListener("input", (e) => {
      clearTimeout(timerBusq);
      timerBusq = setTimeout(() => {
        AppState.filtrosNotificados.busqueda = e.target.value.trim();
        AppState.filtrosNotificados.page = 1;
        cargarNotificados();
      }, 300);
    });
  }

  // Selectores
  const binds = [
    { id: "filtro-notif-evento", key: "evento" },
    { id: "filtro-notif-atencion", key: "primera_atencion" },
    { id: "filtro-notif-municipio", key: "municipio" },
    { id: "filtro-notif-eapb", key: "eapb" },
    { id: "filtro-notif-estado", key: "estado_caso" }
  ];

  binds.forEach(b => {
    const el = document.getElementById(b.id);
    if (el) {
      el.addEventListener("change", (e) => {
        AppState.filtrosNotificados[b.key] = e.target.value;
        AppState.filtrosNotificados.page = 1;
        cargarNotificados();
      });
    }
  });

  // Selector de límite por página
  const selLim = document.getElementById("paginacion-notif-limite");
  if (selLim) {
    selLim.addEventListener("change", (e) => {
      AppState.filtrosNotificados.limit = parseInt(e.target.value) || 50;
      AppState.filtrosNotificados.page = 1;
      cargarNotificados();
    });
  }

  // Botón Limpiar Filtros
  const btnLimpiar = document.getElementById("btn-limpiar-filtros-notif");
  if (btnLimpiar) {
    btnLimpiar.addEventListener("click", () => {
      AppState.filtrosNotificados = {
        evento: "",
        primera_atencion: "",
        municipio: "",
        eapb: "",
        estado_caso: "",
        busqueda: "",
        page: 1,
        limit: 50
      };
      if (inputBusq) inputBusq.value = "";
      binds.forEach(b => {
        const el = document.getElementById(b.id);
        if (el) el.value = "";
      });
      if (selLim) selLim.value = "50";
      cargarNotificados();
    });
  }

  // Botones Paginación
  const btnAnt = document.getElementById("btn-pag-notif-ant");
  const btnSig = document.getElementById("btn-pag-notif-sig");
  const btnAntInf = document.getElementById("btn-pag-notif-ant-inf");
  const btnSigInf = document.getElementById("btn-pag-notif-sig-inf");

  if (btnAnt) btnAnt.addEventListener("click", () => cambiarPaginaNotificados(-1));
  if (btnSig) btnSig.addEventListener("click", () => cambiarPaginaNotificados(1));
  if (btnAntInf) btnAntInf.addEventListener("click", () => cambiarPaginaNotificados(-1));
  if (btnSigInf) btnSigInf.addEventListener("click", () => cambiarPaginaNotificados(1));
}

// -----------------------------------------------------------------------------
// MODAL DE EDICIÓN DE NOTIFICACIÓN
// -----------------------------------------------------------------------------

async function abrirModalEditarNotificacion(casoId) {
  try {
    const res = await fetch(`${API_BASE}/api/notificaciones/${casoId}`);
    if (!res.ok) throw new Error("No se pudo obtener la información de la notificación.");

    const d = await res.json();

    document.getElementById("men-caso-id").value = d.caso_id;
    document.getElementById("men-caso-id-badge").innerText = `Caso #${d.caso_id}`;
    document.getElementById("men-subtitulo").innerText = `${d.nombre_completo || 'Paciente'} • ${d.tipo_documento || 'RC'}: ${d.numero_documento} • ${d.municipio || ''} • ${d.eapb || ''}`;

    // Bloque 1: Notificación
    document.getElementById("men-fuente").value = d.fuente_notificacion || "Evento 114: Riesgo DNT";
    document.getElementById("men-fecha-notificacion").value = d.fecha_notificacion || "";
    document.getElementById("men-medio").value = d.medio_notificacion || "";
    document.getElementById("men-cooperante").value = d.cooperante_notificador || "";

    // Bloque 2: Captación Inicial
    document.getElementById("men-fecha-captacion").value = d.fecha_captacion || "";
    document.getElementById("men-peso-inicial").value = d.peso_inicial_kg ?? "";
    document.getElementById("men-talla-inicial").value = d.talla_inicial_cm ?? "";
    document.getElementById("men-pb-inicial").value = d.pb_inicial_cm ?? "";
    document.getElementById("men-zscore-inicial").value = d.zscore_inicial ?? "";

    // Bloque 3: Búsqueda GBAI
    document.getElementById("men-fecha-gbai").value = d.fecha_busqueda_gbai || "";
    document.getElementById("men-asignacion-gbai").value = d.asignacion_interna || "";
    document.getElementById("men-estado-gbai").value = d.estado_busqueda || "";

    // Bloque 4: Primera Atención IPSI
    document.getElementById("men-fecha-atencion").value = d.fecha_primera_atencion || "";
    document.getElementById("men-peso-atencion").value = d.peso_atencion_kg ?? "";
    document.getElementById("men-talla-atencion").value = d.talla_atencion_cm ?? "";
    document.getElementById("men-pb-atencion").value = d.pb_atencion_cm ?? "";
    document.getElementById("men-zscore-atencion").value = d.zscore_atencion ?? "";
    document.getElementById("men-apetito").value = d.prueba_apetito || "";
    document.getElementById("men-tratamiento").value = d.tratamiento_inicial || "";
    document.getElementById("men-sobres").value = d.sobres_ftlc_inicial ?? "";
    document.getElementById("men-escenario").value = d.escenario_manejo || "Ambulatorio";
    document.getElementById("men-comorbilidad").value = d.comorbilidad_inicial || "";

    // Bloque 5: Contacto y Estado
    document.getElementById("men-cuidador").value = d.cuidador || "";
    document.getElementById("men-telefono").value = d.telefono_cuidador || "";
    document.getElementById("men-estado-caso").value = d.estado_caso || "En seguimiento";
    document.getElementById("men-georreferenciacion").value = d.georreferenciacion || "";
    document.getElementById("men-observaciones").value = d.observaciones || "";

    const msg = document.getElementById("men-mensaje-estado");
    if (msg) msg.innerText = "";

    document.getElementById("modal-editar-notificacion").classList.remove("hidden");

  } catch (err) {
    console.error("Error al abrir modal editar notificación:", err);
    alert(`Error: ${err.message}`);
  }
}

function cerrarModalEditarNotificacion() {
  const modal = document.getElementById("modal-editar-notificacion");
  if (modal) modal.classList.add("hidden");
}

async function guardarEdicionNotificacion(e) {
  e.preventDefault();
  const casoId = document.getElementById("men-caso-id").value;
  if (!casoId) return;

  const btnGuardar = document.getElementById("men-btn-guardar");
  const msg = document.getElementById("men-mensaje-estado");

  try {
    btnGuardar.disabled = true;
    if (msg) {
      msg.className = "text-xs font-medium text-sky-700";
      msg.innerText = "Guardando cambios en el libro oficial...";
    }

    const parseNum = val => (val === "" || isNaN(Number(val))) ? null : Number(val);
    const parseStr = val => val.trim() === "" ? null : val.trim();

    const payload = {
      fuente_notificacion: parseStr(document.getElementById("men-fuente").value),
      fecha_notificacion: parseStr(document.getElementById("men-fecha-notificacion").value),
      medio_notificacion: parseStr(document.getElementById("men-medio").value),
      cooperante_notificador: parseStr(document.getElementById("men-cooperante").value),
      fecha_captacion: parseStr(document.getElementById("men-fecha-captacion").value),
      peso_inicial_kg: parseNum(document.getElementById("men-peso-inicial").value),
      talla_inicial_cm: parseNum(document.getElementById("men-talla-inicial").value),
      pb_inicial_cm: parseNum(document.getElementById("men-pb-inicial").value),
      zscore_inicial: parseNum(document.getElementById("men-zscore-inicial").value),
      fecha_busqueda_gbai: parseStr(document.getElementById("men-fecha-gbai").value),
      asignacion_interna: parseStr(document.getElementById("men-asignacion-gbai").value),
      estado_busqueda: parseStr(document.getElementById("men-estado-gbai").value),
      fecha_primera_atencion: parseStr(document.getElementById("men-fecha-atencion").value),
      peso_atencion_kg: parseNum(document.getElementById("men-peso-atencion").value),
      talla_atencion_cm: parseNum(document.getElementById("men-talla-atencion").value),
      pb_atencion_cm: parseNum(document.getElementById("men-pb-atencion").value),
      zscore_atencion: parseNum(document.getElementById("men-zscore-atencion").value),
      prueba_apetito: parseStr(document.getElementById("men-apetito").value),
      tratamiento_inicial: parseStr(document.getElementById("men-tratamiento").value),
      sobres_ftlc_inicial: parseNum(document.getElementById("men-sobres").value) ? parseInt(document.getElementById("men-sobres").value) : null,
      escenario_manejo: parseStr(document.getElementById("men-escenario").value),
      comorbilidad_inicial: parseStr(document.getElementById("men-comorbilidad").value),
      cuidador: parseStr(document.getElementById("men-cuidador").value),
      telefono_cuidador: parseStr(document.getElementById("men-telefono").value),
      estado_caso: parseStr(document.getElementById("men-estado-caso").value),
      georreferenciacion: parseStr(document.getElementById("men-georreferenciacion").value),
      observaciones: parseStr(document.getElementById("men-observaciones").value)
    };

    const res = await fetch(`${API_BASE}/api/notificaciones/${casoId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "Error al actualizar la notificación");
    }

    if (msg) {
      msg.className = "text-xs font-bold text-emerald-600";
      msg.innerText = "¡Notificación actualizada con éxito!";
    }

    // Refrescar KPIs y tabla
    cargarKpisNotificados();
    cargarNotificados();
    cargarCasos();

    setTimeout(() => {
      cerrarModalEditarNotificacion();
    }, 800);

  } catch (err) {
    console.error("Error al guardar notificación:", err);
    if (msg) {
      msg.className = "text-xs font-bold text-rose-600";
      msg.innerText = `Error: ${err.message}`;
    }
  } finally {
    btnGuardar.disabled = false;
  }
}

function exportarNotificadosExcel() {
  window.location.href = `${API_BASE}/api/notificaciones/exportar-excel`;
}

// =============================================================================
// MÓDULO 1: BÚSQUEDA GLOBAL RÁPIDA (CTRL + K)
// =============================================================================
let timerBusquedaGlobal = null;

function inicializarBusquedaGlobal() {
  const modal = document.getElementById("modal-busqueda-global");
  const input = document.getElementById("input-busqueda-global");
  if (!modal || !input) return;

  // Atajos de teclado global
  document.addEventListener("keydown", (e) => {
    // Ctrl + K o Cmd + K
    if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
      e.preventDefault();
      abrirBusquedaGlobal();
    }
    // Escape cierra búsqueda o modal de alertas
    if (e.key === "Escape") {
      if (!modal.classList.contains("hidden")) {
        cerrarBusquedaGlobal();
      }
      const modalAlertas = document.getElementById("modal-alertas-rescate");
      if (modalAlertas && !modalAlertas.classList.contains("hidden")) {
        cerrarModalAlertasRescate();
      }
    }
  });

  // Cerrar al hacer clic en el backdrop
  modal.addEventListener("click", (e) => {
    if (e.target === modal) cerrarBusquedaGlobal();
  });

  // Input con debounce
  input.addEventListener("input", (e) => {
    clearTimeout(timerBusquedaGlobal);
    const q = e.target.value.trim();
    if (q.length < 2) {
      renderizarResultadosBusqueda([], q);
      return;
    }
    timerBusquedaGlobal = setTimeout(() => {
      ejecutarBusquedaGlobal(q);
    }, 200);
  });

  // Navegación con flechas y Enter
  input.addEventListener("keydown", (e) => {
    const total = AppState.busquedaResultados.length;
    if (total === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      AppState.indiceBusquedaActivo = (AppState.indiceBusquedaActivo + 1) % total;
      actualizarSeleccionBusquedaVisual();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      AppState.indiceBusquedaActivo = (AppState.indiceBusquedaActivo - 1 + total) % total;
      actualizarSeleccionBusquedaVisual();
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (AppState.indiceBusquedaActivo >= 0 && AppState.indiceBusquedaActivo < total) {
        const item = AppState.busquedaResultados[AppState.indiceBusquedaActivo];
        abrirCasoDesdeBusqueda(item.caso_id);
      } else if (total > 0) {
        abrirCasoDesdeBusqueda(AppState.busquedaResultados[0].caso_id);
      }
    }
  });
}

function abrirBusquedaGlobal() {
  const modal = document.getElementById("modal-busqueda-global");
  const input = document.getElementById("input-busqueda-global");
  if (!modal || !input) return;

  modal.classList.remove("hidden");
  setTimeout(() => {
    input.focus();
    input.select();
  }, 50);
}

function cerrarBusquedaGlobal() {
  const modal = document.getElementById("modal-busqueda-global");
  if (modal) modal.classList.add("hidden");
}

async function ejecutarBusquedaGlobal(q) {
  const contenedor = document.getElementById("lista-resultados-busqueda");
  if (contenedor) {
    contenedor.innerHTML = `
      <div class="py-8 text-center text-slate-400 text-xs">
        <div class="inline-block animate-spin rounded-full h-5 w-5 border-2 border-sky-600 border-t-transparent mb-2"></div>
        <p>Buscando coincidencias para "${q}"...</p>
      </div>
    `;
  }

  try {
    const res = await fetch(`${API_BASE}/api/casos/busqueda-global?q=${encodeURIComponent(q)}`);
    if (!res.ok) throw new Error("Error en la búsqueda");
    const data = await res.json();
    AppState.busquedaResultados = data;
    AppState.indiceBusquedaActivo = data.length > 0 ? 0 : -1;
    renderizarResultadosBusqueda(data, q);
  } catch (err) {
    console.error("Error en búsqueda global:", err);
    if (contenedor) {
      contenedor.innerHTML = `
        <div class="py-6 text-center text-rose-500 text-xs">
          Ocurrió un error al buscar pacientes. Por favor intente nuevamente.
        </div>
      `;
    }
  }
}

function renderizarResultadosBusqueda(resultados, q) {
  const contenedor = document.getElementById("lista-resultados-busqueda");
  if (!contenedor) return;

  if (q.length < 2) {
    contenedor.innerHTML = `
      <div class="py-10 text-center text-slate-400 text-xs">
        <div class="w-10 h-10 mx-auto mb-2 text-slate-300 text-2xl">🔍</div>
        <p class="font-semibold text-slate-600">Búsqueda rápida en toda la IPSI</p>
        <p class="text-[11px] text-slate-400 mt-1">Escriba cualquier número de cédula o nombre para abrir de inmediato su ficha.</p>
      </div>
    `;
    return;
  }

  if (resultados.length === 0) {
    contenedor.innerHTML = `
      <div class="py-10 text-center text-slate-500 text-xs">
        <div class="text-3xl mb-1.5">📂</div>
        <p class="font-bold text-slate-700">No se encontraron pacientes para "${q}"</p>
        <p class="text-[11px] text-slate-400 mt-1">Verifique el número de documento o intente con otro nombre.</p>
      </div>
    `;
    return;
  }

  let html = "";
  resultados.forEach((r, idx) => {
    const dx = r.clasificacion_nutricional_actual || "Sin dato";
    let badgeColor = "bg-slate-100 text-slate-700";
    if (dx.includes("Severa")) badgeColor = "bg-rose-100 text-rose-800";
    else if (dx.includes("Moderada")) badgeColor = "bg-amber-100 text-amber-800";
    else if (dx.includes("Riesgo")) badgeColor = "bg-yellow-100 text-yellow-800";
    else if (dx.includes("Adecuado") || dx.includes("Normal")) badgeColor = "bg-emerald-100 text-emerald-800";

    const estadoBadge = r.estado_caso === "En seguimiento" 
      ? '<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-sky-100 text-sky-800">En seguimiento</span>'
      : '<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600">Cerrado</span>';

    const activoClass = idx === AppState.indiceBusquedaActivo ? "bg-sky-50 border-sky-300 ring-1 ring-sky-300" : "hover:bg-slate-50";

    html += `
      <div 
        id="item-busqueda-${idx}" 
        onclick="abrirCasoDesdeBusqueda(${r.caso_id})"
        class="p-3 rounded-xl cursor-pointer transition flex items-center justify-between border border-transparent ${activoClass}"
      >
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center font-black text-xs">
            ${r.sexo === "F" ? "👧" : "👦"}
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <span class="font-bold text-slate-900 text-xs sm:text-sm">${r.nombre_completo}</span>
              ${estadoBadge}
            </div>
            <div class="flex items-center space-x-2 text-[11px] text-slate-500 mt-0.5">
              <span class="font-mono font-semibold text-slate-700">${r.tipo_documento} ${r.numero_documento}</span>
              <span>•</span>
              <span>${r.edad_meses_actual ?? "-"} meses</span>
              <span>•</span>
              <span>${r.municipio || "Sin municipio"}</span>
            </div>
            ${r.cuidador ? `<div class="text-[10px] text-slate-400 mt-0.5">Cuidador: ${r.cuidador} ${r.telefono_cuidador ? `(${r.telefono_cuidador})` : ""}</div>` : ""}
          </div>
        </div>
        <div class="text-right flex flex-col items-end space-y-1">
          <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${badgeColor}">
            ${dx}
          </span>
          <span class="text-[10px] text-sky-600 font-bold flex items-center space-x-1">
            <span>Abrir ficha</span>
            <span>→</span>
          </span>
        </div>
      </div>
    `;
  });

  contenedor.innerHTML = html;
}

function actualizarSeleccionBusquedaVisual() {
  document.querySelectorAll("[id^='item-busqueda-']").forEach((el, idx) => {
    if (idx === AppState.indiceBusquedaActivo) {
      el.classList.add("bg-sky-50", "border-sky-300", "ring-1", "ring-sky-300");
      el.classList.remove("border-transparent");
      el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    } else {
      el.classList.remove("bg-sky-50", "border-sky-300", "ring-1", "ring-sky-300");
      el.classList.add("border-transparent");
    }
  });
}

function abrirCasoDesdeBusqueda(casoId) {
  cerrarBusquedaGlobal();
  verDetalleCaso(casoId);
}

// =============================================================================
// MÓDULO 2: CENTRO DE ALERTAS DE RESCATE NUTRICIONAL
// =============================================================================
async function cargarAlertasRescate() {
  try {
    const res = await fetch(`${API_BASE}/api/reportes/alertas-rescate`);
    if (!res.ok) return;
    const data = await res.json();
    AppState.alertasRescate = data;

    // Actualizar badges
    const total = data.resumen?.total_alertas || 0;
    const badgeHeader = document.getElementById("badge-total-alertas");
    if (badgeHeader) {
      badgeHeader.innerText = total;
      if (total > 0) {
        badgeHeader.classList.remove("hidden");
      }
    }

    const badgeModalTotal = document.getElementById("modal-alertas-total-badge");
    if (badgeModalTotal) badgeModalTotal.innerText = `${total} alertas activas`;

    const badgePerdida = document.getElementById("badge-alerta-perdida");
    if (badgePerdida) badgePerdida.innerText = data.resumen?.total_perdida_peso || 0;

    const badgeEstancamiento = document.getElementById("badge-alerta-estancamiento");
    if (badgeEstancamiento) badgeEstancamiento.innerText = data.resumen?.total_estancamiento || 0;

    const badgeAbandono = document.getElementById("badge-alerta-abandono");
    if (badgeAbandono) badgeAbandono.innerText = data.resumen?.total_abandono || 0;

    const badgeEgresos = document.getElementById("badge-alerta-egresos");
    if (badgeEgresos) badgeEgresos.innerText = data.resumen?.total_proximos_egresos || 0;

  } catch (err) {
    console.error("Error al cargar alertas de rescate:", err);
  }
}

function abrirModalAlertasRescate() {
  const modal = document.getElementById("modal-alertas-rescate");
  if (!modal) return;
  modal.classList.remove("hidden");
  cargarAlertasRescate().then(() => {
    cambiarPestanaAlerta(AppState.pestañaAlertaActiva || "perdida_peso");
  });
}

function cerrarModalAlertasRescate() {
  const modal = document.getElementById("modal-alertas-rescate");
  if (modal) modal.classList.add("hidden");
}

function cambiarPestanaAlerta(tipo) {
  AppState.pestañaAlertaActiva = tipo;

  // Actualizar estilos de pestañas (Estilo Pills espacioso y legible)
  const botones = {
    perdida_peso: document.getElementById("tab-btn-alerta-perdida"),
    estancamiento: document.getElementById("tab-btn-alerta-estancamiento"),
    abandono: document.getElementById("tab-btn-alerta-abandono"),
    proximos_egresos: document.getElementById("tab-btn-alerta-egresos")
  };

  const estilosActivos = {
    perdida_peso: "tab-alerta-btn px-2.5 sm:px-3.5 py-1.5 sm:py-2 rounded-xl text-[11px] sm:text-xs font-bold transition flex items-center space-x-1.5 sm:space-x-2 bg-white text-rose-700 shadow-sm border border-rose-300 ring-1 ring-rose-200",
    estancamiento: "tab-alerta-btn px-2.5 sm:px-3.5 py-1.5 sm:py-2 rounded-xl text-[11px] sm:text-xs font-bold transition flex items-center space-x-1.5 sm:space-x-2 bg-white text-amber-800 shadow-sm border border-amber-300 ring-1 ring-amber-200",
    abandono: "tab-alerta-btn px-2.5 sm:px-3.5 py-1.5 sm:py-2 rounded-xl text-[11px] sm:text-xs font-bold transition flex items-center space-x-1.5 sm:space-x-2 bg-white text-orange-800 shadow-sm border border-orange-300 ring-1 ring-orange-200",
    proximos_egresos: "tab-alerta-btn px-2.5 sm:px-3.5 py-1.5 sm:py-2 rounded-xl text-[11px] sm:text-xs font-bold transition flex items-center space-x-1.5 sm:space-x-2 bg-white text-sky-800 shadow-sm border border-sky-300 ring-1 ring-sky-200"
  };

  Object.keys(botones).forEach(k => {
    const btn = botones[k];
    if (!btn) return;
    if (k === tipo) {
      btn.className = estilosActivos[k];
    } else {
      btn.className = "tab-alerta-btn px-2.5 sm:px-3.5 py-1.5 sm:py-2 rounded-xl text-[11px] sm:text-xs font-bold transition flex items-center space-x-1.5 sm:space-x-2 bg-slate-200/80 text-slate-700 hover:bg-slate-300 border border-transparent";
    }
  });

  renderizarContenidoAlerta(tipo);
}

function renderizarContenidoAlerta(tipo) {
  const contenedor = document.getElementById("contenedor-lista-alertas");
  if (!contenedor) return;

  const data = AppState.alertasRescate;
  if (!data) {
    contenedor.innerHTML = `<div class="p-8 text-center text-slate-400">Cargando alertas...</div>`;
    return;
  }

  const items = data[tipo] || [];

  if (items.length === 0) {
    contenedor.innerHTML = `
      <div class="py-12 text-center text-slate-500 bg-white rounded-xl border border-slate-200">
        <div class="text-4xl mb-2">🎉</div>
        <h4 class="font-bold text-slate-800 text-sm">¡Sin casos en esta categoría de alerta!</h4>
        <p class="text-xs text-slate-400 mt-1">Todos los pacientes en seguimiento cumplen los criterios esperados para este parámetro.</p>
      </div>
    `;
    return;
  }

  let html = "";

  if (tipo === "perdida_peso") {
    html = `
      <div class="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 mb-3 flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <span class="text-lg">⚠️</span>
          <span><strong>Desmejora Clínica:</strong> Menores que registraron menor peso en su último control respecto al anterior. Requieren rescate nutricional inmediato y revisión médica.</span>
        </div>
        <span class="font-black font-mono text-sm">${items.length} casos</span>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
    `;

    items.forEach(c => {
      const delta = parseFloat(c.delta_peso_kg);
      const tel = c.telefono_cuidador ? c.telefono_cuidador.trim() : null;
      html += `
        <div class="bg-white p-4 rounded-xl border border-rose-200 shadow-sm flex flex-col justify-between hover:border-rose-400 transition">
          <div>
            <div class="flex justify-between items-start">
              <div>
                <span class="font-bold text-slate-900 text-xs sm:text-sm">${c.nombre_completo}</span>
                <p class="text-[11px] text-slate-500 font-mono">${c.tipo_documento} ${c.numero_documento} • ${c.municipio || "Sin municipio"}</p>
              </div>
              <span class="px-2.5 py-1 rounded-lg text-xs font-black bg-rose-100 text-rose-700">
                ${delta} kg
              </span>
            </div>

            <div class="grid grid-cols-3 gap-2 mt-3 p-2.5 bg-slate-50 rounded-lg text-center text-[11px]">
              <div>
                <span class="text-slate-400 block text-[10px]">Peso Anterior:</span>
                <span class="font-bold text-slate-700">${c.peso_anterior} kg</span>
              </div>
              <div>
                <span class="text-slate-400 block text-[10px]">Peso Último:</span>
                <span class="font-bold text-rose-600">${c.peso_actual} kg</span>
              </div>
              <div>
                <span class="text-slate-400 block text-[10px]">Lapso:</span>
                <span class="font-bold text-slate-700">${c.dias_lapso} días</span>
              </div>
            </div>

            <div class="mt-2 text-[11px] text-slate-600">
              <span class="text-slate-400">Cuidador:</span> ${c.cuidador || "Sin registro"}
              ${tel ? `<span class="ml-2 font-mono text-slate-700 font-semibold">📞 Tel: ${tel}</span>` : ""}
            </div>
          </div>

          <div class="mt-3 pt-2.5 border-t border-slate-100 flex justify-end items-center">
            <button onclick="cerrarModalAlertasRescate(); verDetalleCaso(${c.caso_id})" class="inline-flex items-center px-4 py-2 rounded-xl text-xs font-bold bg-sky-600 hover:bg-sky-500 text-white shadow-sm transition">
              <span>Ver Expediente →</span>
            </button>
          </div>
        </div>
      `;
    });
    html += `</div>`;

  } else if (tipo === "estancamiento") {
    html = `
      <div class="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 mb-3 flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <span class="text-lg">⚖️</span>
          <span><strong>Estancamiento Ponderal:</strong> Niños con ganancia de peso deficiente (&lt; 5 g/kg/día) entre controles. Indican probable fallo terapéutico o inapetencia.</span>
        </div>
        <span class="font-black font-mono text-sm">${items.length} casos</span>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
    `;

    items.forEach(c => {
      const gKg = parseFloat(c.ganancia_g_kg_dia);
      const tel = c.telefono_cuidador ? c.telefono_cuidador.trim() : null;
      html += `
        <div class="bg-white p-4 rounded-xl border border-amber-200 shadow-sm flex flex-col justify-between hover:border-amber-400 transition">
          <div>
            <div class="flex justify-between items-start">
              <div>
                <span class="font-bold text-slate-900 text-xs sm:text-sm">${c.nombre_completo}</span>
                <p class="text-[11px] text-slate-500 font-mono">${c.tipo_documento} ${c.numero_documento} • ${c.municipio || "Sin municipio"}</p>
              </div>
              <span class="px-2.5 py-1 rounded-lg text-xs font-black bg-amber-100 text-amber-800">
                ${gKg} g/kg/d
              </span>
            </div>

            <div class="grid grid-cols-3 gap-2 mt-3 p-2.5 bg-slate-50 rounded-lg text-center text-[11px]">
              <div>
                <span class="text-slate-400 block text-[10px]">Δ Peso:</span>
                <span class="font-bold text-amber-700">+${c.delta_peso_kg} kg</span>
              </div>
              <div>
                <span class="text-slate-400 block text-[10px]">Peso Actual:</span>
                <span class="font-bold text-slate-700">${c.peso_actual} kg</span>
              </div>
              <div>
                <span class="text-slate-400 block text-[10px]">Lapso:</span>
                <span class="font-bold text-slate-700">${c.dias_lapso} días</span>
              </div>
            </div>

            <div class="mt-2 text-[11px] text-slate-600">
              <span class="text-slate-400">Cuidador:</span> ${c.cuidador || "Sin registro"}
              ${tel ? `<span class="ml-2 font-mono text-slate-700 font-semibold">📞 Tel: ${tel}</span>` : ""}
            </div>
          </div>

          <div class="mt-3 pt-2.5 border-t border-slate-100 flex justify-end items-center">
            <button onclick="cerrarModalAlertasRescate(); verDetalleCaso(${c.caso_id})" class="inline-flex items-center px-4 py-2 rounded-xl text-xs font-bold bg-sky-600 hover:bg-sky-500 text-white shadow-sm transition">
              <span>Ver Expediente →</span>
            </button>
          </div>
        </div>
      `;
    });
    html += `</div>`;

  } else if (tipo === "abandono") {
    html = `
      <div class="p-3 bg-orange-50 border border-orange-200 rounded-xl text-xs text-orange-900 mb-3 flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <span class="text-lg">⏰</span>
          <span><strong>Riesgo de Inasistencia / Abandono:</strong> Citas programadas con más de 15 días de vencimiento sin reporte de control. Requieren búsqueda activa comunitaria (GBAI).</span>
        </div>
        <span class="font-black font-mono text-sm">${items.length} casos</span>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
    `;

    items.forEach(c => {
      const dias = c.dias_vencido;
      const tel = c.telefono_cuidador ? c.telefono_cuidador.trim() : null;
      html += `
        <div class="bg-white p-4 rounded-xl border border-orange-200 shadow-sm flex flex-col justify-between hover:border-orange-400 transition">
          <div>
            <div class="flex justify-between items-start">
              <div>
                <span class="font-bold text-slate-900 text-xs sm:text-sm">${c.nombre_completo}</span>
                <p class="text-[11px] text-slate-500 font-mono">${c.tipo_documento} ${c.numero_documento} • ${c.municipio || "Sin municipio"}</p>
              </div>
              <span class="px-2.5 py-1 rounded-lg text-xs font-black bg-orange-100 text-orange-800">
                ${dias} días vencido
              </span>
            </div>

            <div class="grid grid-cols-2 gap-2 mt-3 p-2.5 bg-slate-50 rounded-lg text-center text-[11px]">
              <div>
                <span class="text-slate-400 block text-[10px]">Próxima Cita Era:</span>
                <span class="font-bold text-rose-600">${c.fecha_proxima_cita || "-"}</span>
              </div>
              <div>
                <span class="text-slate-400 block text-[10px]">Última Atención:</span>
                <span class="font-bold text-slate-700">${c.fecha_ultima_atencion || "-"}</span>
              </div>
            </div>

            <div class="mt-2 text-[11px] text-slate-600">
              <span class="text-slate-400">Cuidador:</span> ${c.cuidador || "Sin registro"}
              ${tel ? `<span class="ml-2 font-mono text-slate-700 font-semibold">📞 Tel: ${tel}</span>` : ""}
            </div>
          </div>

          <div class="mt-3 pt-2.5 border-t border-slate-100 flex justify-end items-center">
            <button onclick="cerrarModalAlertasRescate(); verDetalleCaso(${c.caso_id})" class="inline-flex items-center px-4 py-2 rounded-xl text-xs font-bold bg-sky-600 hover:bg-sky-500 text-white shadow-sm transition">
              <span>Ver Expediente →</span>
            </button>
          </div>
        </div>
      `;
    });
    html += `</div>`;

  } else if (tipo === "proximos_egresos") {
    html = `
      <div class="p-3 bg-sky-50 border border-sky-200 rounded-xl text-xs text-sky-900 mb-3 flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <span class="text-lg">🎓</span>
          <span><strong>Próximos Egresos por Edad (59 Meses):</strong> Menores que cumplirán 60 meses (5 años) próximamente. Se debe coordinar el egreso de la ruta y su remisión formal a ICBF / Alimentación Escolar.</span>
        </div>
        <span class="font-black font-mono text-sm">${items.length} casos</span>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
    `;

    items.forEach(c => {
      const dias = c.dias_para_60;
      const tel = c.telefono_cuidador ? c.telefono_cuidador.trim() : null;
      let badgeDias = dias < 0 
        ? `<span class="px-2.5 py-1 rounded-lg text-xs font-black bg-rose-100 text-rose-800">Ya cumplió 60 meses</span>`
        : `<span class="px-2.5 py-1 rounded-lg text-xs font-black bg-sky-100 text-sky-800">Faltan ${dias} días para 5 años</span>`;

      html += `
        <div class="bg-white p-4 rounded-xl border border-sky-200 shadow-sm flex flex-col justify-between hover:border-sky-400 transition">
          <div>
            <div class="flex justify-between items-start">
              <div>
                <span class="font-bold text-slate-900 text-xs sm:text-sm">${c.nombre_completo}</span>
                <p class="text-[11px] text-slate-500 font-mono">${c.tipo_documento} ${c.numero_documento} • ${c.municipio || "Sin municipio"}</p>
              </div>
              ${badgeDias}
            </div>

            <div class="grid grid-cols-2 gap-2 mt-3 p-2.5 bg-slate-50 rounded-lg text-center text-[11px]">
              <div>
                <span class="text-slate-400 block text-[10px]">Edad Actual:</span>
                <span class="font-bold text-slate-800">${c.edad_meses_actual} meses</span>
              </div>
              <div>
                <span class="text-slate-400 block text-[10px]">Fecha Cumple 5 Años:</span>
                <span class="font-bold text-sky-700">${c.fecha_cumple_60}</span>
              </div>
            </div>

            <div class="mt-2 text-[11px] text-slate-600">
              <span class="text-slate-400">Cuidador:</span> ${c.cuidador || "Sin registro"}
              ${tel ? `<span class="ml-2 font-mono text-slate-700 font-semibold">📞 Tel: ${tel}</span>` : ""}
            </div>
          </div>

          <div class="mt-3 pt-2.5 border-t border-slate-100 flex justify-end items-center">
            <button onclick="cerrarModalAlertasRescate(); verDetalleCaso(${c.caso_id})" class="inline-flex items-center px-4 py-2 rounded-xl text-xs font-bold bg-sky-600 hover:bg-sky-500 text-white shadow-sm transition">
              <span>Ver Expediente →</span>
            </button>
          </div>
        </div>
      `;
    });
    html += `</div>`;
  }

  contenedor.innerHTML = html;
}

// =============================================================================
// MÓDULO 3: COPIA DE SEGURIDAD BD (POSTGRESQL EN 1 CLIC)
// =============================================================================
function descargarBackupBD() {
  const conf = confirm(
    "¿Desea generar y descargar ahora una copia de seguridad comprimida (.sql.gz) de la base de datos de la IPSI?\\n\\n" +
    "Esta operación generará un respaldo íntegro de todas las tablas, pacientes, notificaciones y controles."
  );
  if (!conf) return;

  // Notificación visual en pantalla
  const notif = document.createElement("div");
  notif.className = "fixed bottom-5 right-5 z-50 bg-slate-900 text-white px-4 py-3 rounded-xl shadow-2xl text-xs flex items-center space-x-3 border border-slate-700 animate-bounce";
  notif.innerHTML = `
    <div class="w-3 h-3 rounded-full bg-emerald-400 animate-ping"></div>
    <span>Generando respaldo de la base de datos PostgreSQL...</span>
  `;
  document.body.appendChild(notif);

  setTimeout(() => {
    window.location.href = `${API_BASE}/api/reportes/backup-bd`;
    setTimeout(() => {
      notif.remove();
    }, 4000);
  }, 500);
}

// =============================================================================
// MÓDULO 4: CENTRO OFICIAL DE REPORTES Y GENERACIÓN DE ARCHIVOS
// =============================================================================

function poblarSelectoresReportesOficiales() {
  // 1. Selector de Semanas SIVIGILA (SE 1 a 52)
  const selSemana = document.getElementById("rep-sivigila-semana");
  if (selSemana && selSemana.children.length <= 1) {
    selSemana.innerHTML = '<option value="">Todas las Semanas Epidemiológicas (1 - 52)</option>';
    for (let s = 1; s <= 52; s++) {
      selSemana.innerHTML += `<option value="${s}">Semana Epidemiológica ${s} (S.E. ${s})</option>`;
    }
  }

  // 2. Selectores de EAPB (Aseguradoras)
  const eapbs = AppState.catalogos?.eapb || [];
  const selMatrizEapb = document.getElementById("rep-matriz-eapb");
  const selT302Eapb = document.getElementById("rep-t302-eapb");

  if (selMatrizEapb && selMatrizEapb.children.length <= 1) {
    selMatrizEapb.innerHTML = '<option value="TODAS">Todas las Aseguradoras (EPS)</option>';
    eapbs.forEach(e => {
      selMatrizEapb.innerHTML += `<option value="${e.nombre}">${e.nombre}</option>`;
    });
  }
  if (selT302Eapb && selT302Eapb.children.length <= 1) {
    selT302Eapb.innerHTML = '<option value="TODAS">Todas las Aseguradoras (EPS)</option>';
    eapbs.forEach(e => {
      selT302Eapb.innerHTML += `<option value="${e.nombre}">${e.nombre}</option>`;
    });
  }

  // 3. Selectores de Municipios
  const municipios = AppState.catalogos?.municipios || [];
  const selMatrizMun = document.getElementById("rep-matriz-municipio");
  const selGbaiMun = document.getElementById("rep-gbai-municipio");

  if (selMatrizMun && selMatrizMun.children.length <= 1) {
    selMatrizMun.innerHTML = '<option value="TODOS">Todos los Municipios</option>';
    municipios.forEach(m => {
      selMatrizMun.innerHTML += `<option value="${m.nombre}">${m.nombre}</option>`;
    });
  }
  if (selGbaiMun && selGbaiMun.children.length <= 1) {
    selGbaiMun.innerHTML = '<option value="TODOS">Todos los Municipios (La Guajira)</option>';
    municipios.forEach(m => {
      selGbaiMun.innerHTML += `<option value="${m.nombre}">${m.nombre}</option>`;
    });
  }
}

function mostrarNotificacionDescarga(mensaje) {
  const notif = document.createElement("div");
  notif.className = "fixed bottom-5 right-5 z-50 bg-slate-900 text-white px-4 py-3 rounded-xl shadow-2xl text-xs flex items-center space-x-3 border border-slate-700 animate-bounce";
  notif.innerHTML = `
    <div class="w-3 h-3 rounded-full bg-emerald-400 animate-ping"></div>
    <span>${mensaje}</span>
  `;
  document.body.appendChild(notif);
  setTimeout(() => notif.remove(), 4000);
}

function generarReporteMatrizMaestra() {
  const eapb = document.getElementById("rep-matriz-eapb")?.value || "TODAS";
  const mun = document.getElementById("rep-matriz-municipio")?.value || "TODOS";

  mostrarNotificacionDescarga("Generando Matriz Maestra FT-003/004 con formato institucional...");

  const params = new URLSearchParams();
  if (eapb !== "TODAS") params.append("eapb", eapb);
  if (mun !== "TODOS") params.append("municipio", mun);

  const url = `${API_BASE}/api/reportes/exportar-excel?${params.toString()}`;
  setTimeout(() => { window.location.href = url; }, 500);
}

function generarReporteSivigila() {
  const evento = document.getElementById("rep-sivigila-evento")?.value || "";
  const semana = document.getElementById("rep-sivigila-semana")?.value || "";
  const anio = document.getElementById("rep-sivigila-anio")?.value || "";

  mostrarNotificacionDescarga("Generando Reporte Oficial SIVIGILA (INS)...");

  const params = new URLSearchParams();
  if (evento) params.append("evento", evento);
  if (semana) params.append("semana", semana);
  if (anio) params.append("anio", anio);

  const url = `${API_BASE}/api/reportes/exportar-sivigila?${params.toString()}`;
  setTimeout(() => { window.location.href = url; }, 500);
}

function generarReporteT302() {
  const mun = document.getElementById("rep-t302-municipio")?.value || "TODOS";
  const eapb = document.getElementById("rep-t302-eapb")?.value || "TODAS";

  mostrarNotificacionDescarga("Generando Dossier de la Sentencia T-302 / Comités...");

  const params = new URLSearchParams();
  if (mun !== "TODOS") params.append("municipio", mun);
  if (eapb !== "TODAS") params.append("eapb", eapb);

  const url = `${API_BASE}/api/reportes/exportar-t302?${params.toString()}`;
  setTimeout(() => { window.location.href = url; }, 500);
}

function generarReporteBusquedaActiva() {
  const dias = document.getElementById("rep-gbai-dias")?.value || "15";
  const mun = document.getElementById("rep-gbai-municipio")?.value || "TODOS";

  mostrarNotificacionDescarga("Generando Planilla de Rescate de Campo GBAI...");

  const params = new URLSearchParams();
  params.append("dias_vencido_min", dias);
  if (mun !== "TODOS") params.append("municipio", mun);

  const url = `${API_BASE}/api/reportes/exportar-busqueda-activa?${params.toString()}`;
  setTimeout(() => { window.location.href = url; }, 500);
}

// =============================================================================
// NAVEGACIÓN Y DESPLAZAMIENTO HORIZONTAL ASISTIDO EN TABLAS CLÍNICAS
// =============================================================================
function desplazarTabla(wrapperId, delta) {
  const el = document.getElementById(wrapperId);
  if (!el) return;
  if (delta === 9999) {
    el.scrollTo({ left: el.scrollWidth, behavior: "smooth" });
  } else if (delta === -9999) {
    el.scrollTo({ left: 0, behavior: "smooth" });
  } else {
    el.scrollBy({ left: delta, behavior: "smooth" });
  }
}

function inicializarSincronizacionScroll() {
  const wrapper = document.getElementById("wrapper-tabla-casos");
  const topScroll = document.getElementById("top-scrollbar-casos");
  const topInner = document.getElementById("top-scrollbar-casos-inner");
  const indicador = document.getElementById("scroll-indicador-casos");
  const tabla = document.getElementById("tabla-casos-element");

  if (!wrapper) return;

  function sincronizarDimensiones() {
    if (topInner && tabla) {
      topInner.style.minWidth = `${Math.max(tabla.scrollWidth, 1350)}px`;
    }
    actualizarIndicador();
  }

  let sincronizando = false;

  if (topScroll) {
    topScroll.addEventListener("scroll", () => {
      if (sincronizando) return;
      sincronizando = true;
      wrapper.scrollLeft = topScroll.scrollLeft;
      actualizarIndicador();
      sincronizando = false;
    }, { passive: true });

    wrapper.addEventListener("scroll", () => {
      if (sincronizando) return;
      sincronizando = true;
      topScroll.scrollLeft = wrapper.scrollLeft;
      actualizarIndicador();
      sincronizando = false;
    }, { passive: true });
  }

  function actualizarIndicador() {
    if (!indicador) return;
    const maxScroll = wrapper.scrollWidth - wrapper.clientWidth;
    if (maxScroll <= 10) {
      indicador.innerText = "Vista Completa";
      indicador.className = "text-[11px] font-mono text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded border border-emerald-200 font-bold";
      return;
    }
    const current = wrapper.scrollLeft;
    const pct = Math.round((current / maxScroll) * 100);
    if (pct < 15) {
      indicador.innerText = "Inicio ◀ (Desliza a la derecha)";
      indicador.className = "text-[11px] font-mono text-sky-700 bg-white px-2.5 py-0.5 rounded border border-sky-300 font-bold shadow-xs";
    } else if (pct > 85) {
      indicador.innerText = "Fin ▶ (Acciones y Citas Visibles)";
      indicador.className = "text-[11px] font-mono text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded border border-emerald-300 font-black shadow-xs";
    } else {
      indicador.innerText = `Desplazado ${pct}%`;
      indicador.className = "text-[11px] font-mono text-slate-700 bg-white px-2.5 py-0.5 rounded border border-slate-300 font-semibold";
    }
  }

  window.ajustarScrollCasos = sincronizarDimensiones;
  window.addEventListener("resize", sincronizarDimensiones);

  // Sincronización inicial con reintento tras render
  setTimeout(sincronizarDimensiones, 200);
  setTimeout(sincronizarDimensiones, 1000);
}

// Alias globales para acciones de la tabla y navegación
window.desplazarTabla = desplazarTabla;
window.inicializarSincronizacionScroll = inicializarSincronizacionScroll;
window.verExpediente = verDetalleCaso;
window.verDetalleCaso = verDetalleCaso;
window.volverDeExpediente = volverDeExpediente;
window.imprimirExpediente = imprimirExpedientePorId;
window.imprimirExpedientePorId = imprimirExpedientePorId;
window.abrirModalEditarNotificacion = abrirModalEditarNotificacion;
window.abrirBusquedaGlobal = abrirBusquedaGlobal;
window.cerrarBusquedaGlobal = cerrarBusquedaGlobal;
window.abrirCasoDesdeBusqueda = abrirCasoDesdeBusqueda;
window.abrirModalAlertasRescate = abrirModalAlertasRescate;
window.cerrarModalAlertasRescate = cerrarModalAlertasRescate;
window.cambiarPestanaAlerta = cambiarPestanaAlerta;
window.descargarBackupBD = descargarBackupBD;
window.exportarNotificadosExcel = exportarNotificadosExcel;
window.poblarSelectoresReportesOficiales = poblarSelectoresReportesOficiales;
window.generarReporteMatrizMaestra = generarReporteMatrizMaestra;
window.generarReporteSivigila = generarReporteSivigila;
window.generarReporteT302 = generarReporteT302;
window.generarReporteBusquedaActiva = generarReporteBusquedaActiva;
window.cambiarVistaTrazabilidad = cambiarVistaTrazabilidad;
window.cambiarPaginaTarjetas = cambiarPaginaTarjetas;
window.irAUltimaPaginaTarjetas = irAUltimaPaginaTarjetas;
window.toggleExpandirTimeline = toggleExpandirTimeline;


