/**
 * Sistema de Gestión Operativa — Frontend JavaScript
 * Sin frameworks. Vanilla JS puro.
 * Usa Chart.js (CDN) para gráficos y fetch() nativo para la API.
 */

"use strict";

// ── Formateadores ──────────────────────────────────────────────────────────────

/** Formatea un número como moneda ARS */
function fmtARS(n) {
  return new Intl.NumberFormat("es-AR", {
    style: "currency", currency: "ARS",
    minimumFractionDigits: 0, maximumFractionDigits: 0,
  }).format(n);
}

/** Formatea una fecha ISO a DD/MM/YYYY */
function fmtFecha(iso) {
  if (!iso) return "—";
  // The database might return a date like "2026-04-12" or a datetime "2026-04-12T00:00:00"
  try {
    const d = new Date(iso);
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    if (isNaN(year)) return "—"; // fallback if parsing fails
    return `${day}/${month}/${year}`;
  } catch(e) {
    return iso;
  }
}

/** Badge HTML para tipo de movimiento */
function badgeTipo(tipo) {
  const t = (tipo || "").toLowerCase();
  const map = {
    ingreso: "badge-ingreso", venta: "badge-venta",
    egreso:  "badge-egreso",  compra: "badge-compra",
  };
  return `<span class="badge ${map[t] || ''}">${tipo}</span>`;
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

let chartMes    = null;
let chartCat    = null;

/**
 * Carga los datos de la API y renderiza el dashboard completo.
 * Llamada al DOMContentLoaded si estamos en la página de dashboard.
 */
async function cargarDashboard() {
  try {
    const res  = await fetch("/api/datos");
    const data = await res.json();

    // Actualizar timestamp
    const ts = document.getElementById("last-update");
    if (ts) ts.textContent = data.ultima_actualizacion;

    // ── KPI Cards ────────────────────────────────────────────────
    setKPI("kpi-ingresos", fmtARS(data.ingresos));
    setKPI("kpi-egresos",  fmtARS(data.egresos));
    setKPI("kpi-saldo",    fmtARS(data.saldo));
    setKPI("kpi-stock",    data.stock_critico + " ítems");

    // Color saldo: verde si positivo, rojo si negativo
    const saldoEl = document.querySelector("#kpi-saldo .kpi-value");
    if (saldoEl) {
      saldoEl.style.color = data.saldo >= 0
        ? "var(--green)"
        : "var(--red)";
    }

    // ── Gráfico de barras: Ingresos vs Egresos por mes ───────────
    const labels   = data.por_mes.map(d => d.mes);
    const ingresos = data.por_mes.map(d => d.ingresos);
    const egresos  = data.por_mes.map(d => d.egresos);

    const ctxMes = document.getElementById("chart-mes");
    if (ctxMes) {
      if (chartMes) chartMes.destroy();
      chartMes = new Chart(ctxMes.getContext("2d"), {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: "Ingresos",
              data: ingresos,
              backgroundColor: "rgba(16,185,129,.75)",
              hoverBackgroundColor: "#10B981",
              borderRadius: 6, borderSkipped: false, barThickness: 28,
            },
            {
              label: "Egresos",
              data: egresos,
              backgroundColor: "rgba(239,68,68,.65)",
              hoverBackgroundColor: "#EF4444",
              borderRadius: 6, borderSkipped: false, barThickness: 28,
            },
          ],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: "#94A3B8", font: { size: 11 }, boxWidth: 12 } },
            tooltip: {
              backgroundColor: "#1A2035", borderColor: "#1E3A5F", borderWidth: 1,
              titleColor: "#94A3B8", bodyColor: "#F1F5F9", bodyFont: { weight: "700" },
              callbacks: { label: ctx => fmtARS(ctx.parsed.y) },
            },
          },
          scales: {
            x: { grid: { display: false }, ticks: { color: "#475569", font: { size: 11 } },
                 border: { display: false } },
            y: { grid: { color: "rgba(30,58,95,.5)" }, border: { display: false },
                 ticks: { color: "#475569", font: { size: 11 },
                          callback: v => v >= 1e6 ? `$${(v/1e6).toFixed(1)}M` : `$${(v/1e3).toFixed(0)}k` } },
          },
        },
      });
    }

    // ── Gráfico de dona: Por categoría ───────────────────────────
    const ctxCat = document.getElementById("chart-cat");
    if (ctxCat && data.por_categoria.length > 0) {
      if (chartCat) chartCat.destroy();
      const COLORS = ["#3B82F6","#10B981","#F59E0B","#8B5CF6","#EF4444","#06B6D4"];
      chartCat = new Chart(ctxCat.getContext("2d"), {
        type: "doughnut",
        data: {
          labels: data.por_categoria.map(d => d.categoria),
          datasets: [{
            data:            data.por_categoria.map(d => d.total),
            backgroundColor: COLORS.map(c => c + "BB"),
            hoverBackgroundColor: COLORS,
            borderColor:     "#1A2035",
            borderWidth:     3,
            hoverOffset:     6,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: "65%",
          plugins: {
            legend: { position: "bottom",
              labels: { color: "#94A3B8", font: { size: 11 }, boxWidth: 12, padding: 14 } },
            tooltip: {
              backgroundColor: "#1A2035", borderColor: "#1E3A5F", borderWidth: 1,
              titleColor: "#94A3B8", bodyColor: "#F1F5F9", bodyFont: { weight: "700" },
              callbacks: { label: ctx => fmtARS(ctx.parsed) },
            },
          },
        },
      });
    }

    // ── Tabla de movimientos recientes ───────────────────────────
    const tbody = document.getElementById("tbody-recientes");
    if (tbody) {
      tbody.innerHTML = data.recientes.map(m => `
        <tr>
          <td>${fmtFecha(m.fecha)}</td>
          <td>${badgeTipo(m.tipo)}</td>
          <td style="max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${m.concepto}</td>
          <td>${m.categoria}</td>
          <td>${fmtARS(m.monto)}</td>
        </tr>
      `).join("") || `<tr><td colspan="5" class="table-empty">Sin movimientos recientes.</td></tr>`;
    }

  } catch (err) {
    console.error("Error al cargar dashboard:", err);
  }
}

/** Actualiza el texto de una KPI card por su ID */
function setKPI(id, value) {
  const el = document.querySelector(`#${id} .kpi-value`);
  if (el) {
    el.textContent = value;
    el.classList.remove("kpi-loading");
  }
}

// ── Upload CSV ────────────────────────────────────────────────────────────────

function initUpload() {
  const dropZone  = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const fileName  = document.getElementById("file-name");
  if (!dropZone) return;

  dropZone.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", () => {
    const f = fileInput.files[0];
    if (f) {
      fileName.textContent = f.name;
      dropZone.querySelector(".drop-zone-text").innerHTML =
        `<strong>${f.name}</strong> seleccionado`;
    }
  });

  dropZone.addEventListener("dragover", e => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
  dropZone.addEventListener("drop", e => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    const f = e.dataTransfer.files?.[0];
    if (f) {
      fileInput.files = e.dataTransfer.files;
      fileName.textContent = f.name;
    }
  });
}

// ── Stock bars ────────────────────────────────────────────────────────────────

function initStockBars() {
  document.querySelectorAll(".stock-bar").forEach(bar => {
    const pct = parseFloat(bar.dataset.pct || 0);
    bar.style.width = Math.min(pct, 100) + "%";
    bar.style.background = pct <= 30
      ? "var(--red)"
      : pct <= 60
      ? "var(--amber)"
      : "var(--green)";
    setTimeout(() => { bar.style.width = Math.min(pct, 100) + "%"; }, 100);
  });
}

// ── Filtro detalle: limpiar fechas ────────────────────────────────────────────

function clearFilters() {
  const form = document.getElementById("filter-form");
  if (form) {
    form.reset();
    form.submit();
  }
}

// ── DOMContentLoaded: dispatch por página ─────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;

  if (page === "dashboard") cargarDashboard();
  if (page === "upload")   initUpload();
  if (page === "stock")    initStockBars();

  // Sidebar: marcar enlace activo
  const current = window.location.pathname;
  document.querySelectorAll(".nav-item").forEach(link => {
    const href = link.getAttribute("href") || "";
    if (href !== "/" && current.startsWith(href)) {
      link.classList.add("active");
    } else if (href === "/" && current === "/") {
      link.classList.add("active");
    }
  });
});
