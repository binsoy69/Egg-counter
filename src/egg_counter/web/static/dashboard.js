const PERIODS = ["weekly", "monthly", "yearly"];
const SIZE_ORDER = ["small", "medium", "large", "jumbo"];
const BAR_COLORS = {
  small: "#3f7ae3",
  medium: "#27c267",
  large: "#f59c0f",
  jumbo: "#f1484c",
};

let selectedPeriod = "weekly";
let toastTimer = null;
const periodSnapshots = {};

function numberFormat(value) {
  return new Intl.NumberFormat("en-US").format(value ?? 0);
}

function titleCaseSize(size) {
  if (!size) {
    return "No data";
  }
  return size.charAt(0).toUpperCase() + size.slice(1);
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function getPeriodSummary(snapshot) {
  const total = (snapshot.production_series || []).reduce(
    (sum, entry) => sum + (entry.total || 0),
    0,
  );
  const labels = {
    weekly: ["Last 7 days", "Rolling window"],
    monthly: ["Month to date", "Calendar month"],
    yearly: ["Year to date", "Calendar year"],
  };
  return {
    total,
    label: labels[snapshot.period]?.[0] || "Current period",
    range: labels[snapshot.period]?.[1] || "",
  };
}

function renderPeriodCards() {
  PERIODS.forEach((period) => {
    const snapshot = periodSnapshots[period];
    if (!snapshot) {
      return;
    }
    const summary = getPeriodSummary(snapshot);
    setText(`period-${period}-total`, numberFormat(summary.total));
    setText(`period-${period}-label`, summary.label);
    setText(`period-${period}-range`, summary.range);
  });
}

function buildLineChart(series) {
  if (!series.length) {
    return '<div class="chart-empty">No production data yet for this period.</div>';
  }

  const width = 680;
  const height = 300;
  const left = 42;
  const right = 20;
  const top = 16;
  const bottom = 38;
  const innerWidth = width - left - right;
  const innerHeight = height - top - bottom;
  const max = Math.max(...series.map((entry) => entry.total), 1);
  const points = series.map((entry, index) => {
    const x = left + (series.length === 1 ? innerWidth / 2 : (innerWidth * index) / (series.length - 1));
    const y = top + innerHeight - (entry.total / max) * innerHeight;
    return { x, y, label: entry.date, total: entry.total };
  });
  const path = points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
  const area = `${path} L ${points[points.length - 1].x} ${height - bottom} L ${points[0].x} ${height - bottom} Z`;
  const grid = Array.from({ length: 4 }, (_, index) => {
    const y = top + (innerHeight / 3) * index;
    return `<line x1="${left}" y1="${y}" x2="${width - right}" y2="${y}"></line>`;
  }).join("");
  const xLabels = points.map((point) => {
    const label = new Date(point.label).toLocaleDateString("en-US", { month: "short", day: "numeric" });
    return `<text class="axis-label" x="${point.x}" y="${height - 10}" text-anchor="middle">${label}</text>`;
  }).join("");
  const markers = points.map((point) => (
    `<circle class="line-point" cx="${point.x}" cy="${point.y}" r="5">
      <title>${point.label}: ${point.total}</title>
    </circle>`
  )).join("");

  return `
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <defs>
        <linearGradient id="productionArea" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="rgba(245, 156, 15, 0.28)"></stop>
          <stop offset="100%" stop-color="rgba(245, 156, 15, 0.02)"></stop>
        </linearGradient>
      </defs>
      <g class="chart-grid-lines">${grid}</g>
      <path class="line-area" d="${area}"></path>
      <path class="line-path" d="${path}"></path>
      ${markers}
      ${xLabels}
    </svg>
  `;
}

function buildBarChart(sizeBreakdown) {
  const entries = SIZE_ORDER.map((size) => ({
    size,
    value: sizeBreakdown?.[size] || 0,
  }));
  const max = Math.max(...entries.map((entry) => entry.value), 1);
  if (entries.every((entry) => entry.value === 0)) {
    return '<div class="chart-empty">Size distribution will appear after detections arrive.</div>';
  }

  const width = 520;
  const height = 300;
  const floor = 250;
  const bars = entries.map((entry, index) => {
    const barWidth = 62;
    const gap = 34;
    const x = 46 + index * (barWidth + gap);
    const barHeight = Math.max((entry.value / max) * 180, entry.value > 0 ? 14 : 0);
    const y = floor - barHeight;
    return `
      <rect class="bar" x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" fill="${BAR_COLORS[entry.size]}"></rect>
      <text class="axis-label" x="${x + barWidth / 2}" y="278" text-anchor="middle">${titleCaseSize(entry.size)}</text>
      <text class="axis-label" x="${x + barWidth / 2}" y="${Math.max(y - 8, 20)}" text-anchor="middle">${entry.value}</text>
    `;
  }).join("");

  return `
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <g class="chart-grid-lines">
        <line x1="32" y1="250" x2="490" y2="250"></line>
        <line x1="32" y1="180" x2="490" y2="180"></line>
        <line x1="32" y1="110" x2="490" y2="110"></line>
        <line x1="32" y1="40" x2="490" y2="40"></line>
      </g>
      ${bars}
    </svg>
  `;
}

function renderSnapshot(snapshot) {
  setText("today-total", numberFormat(snapshot.today_total));
  setText("kpi-today-total", numberFormat(snapshot.today_total));
  setText("kpi-all-time", numberFormat(snapshot.all_time_total));

  SIZE_ORDER.forEach((size) => {
    setText(`size-${size}`, numberFormat(snapshot.today_by_size?.[size] || 0));
  });

  const bestDay = snapshot.best_day?.date
    ? `${new Date(snapshot.best_day.date).toLocaleDateString("en-US", { month: "short", day: "numeric" })} (${snapshot.best_day.total})`
    : "No data";
  setText("kpi-best-day", bestDay);

  const topSize = snapshot.top_size?.size
    ? `${titleCaseSize(snapshot.top_size.size)} (${snapshot.top_size.total})`
    : "No data";
  setText("kpi-top-size", topSize);

  renderPeriodCards();
  PERIODS.forEach((period) => {
    document.getElementById(`period-${period}`)?.classList.toggle("is-selected", period === snapshot.period);
  });

  const productionChart = document.getElementById("production-chart");
  const sizeChart = document.getElementById("size-chart");
  if (productionChart) {
    productionChart.innerHTML = buildLineChart(snapshot.production_series || []);
  }
  if (sizeChart) {
    sizeChart.innerHTML = buildBarChart(snapshot.size_breakdown || {});
  }

  setText("production-caption", `${titleCaseSize(snapshot.period)} production window`);
  setText("size-caption", `${titleCaseSize(snapshot.period)} size mix`);
}

async function loadSnapshot(period = selectedPeriod) {
  selectedPeriod = period;
  const response = await fetch(`/api/dashboard/snapshot?period=${encodeURIComponent(period)}`);
  if (!response.ok) {
    throw new Error(`Snapshot request failed: ${response.status}`);
  }
  const snapshot = await response.json();
  periodSnapshots[period] = snapshot;
  renderSnapshot(snapshot);
  return snapshot;
}

async function refreshAllPeriods(activePeriod = selectedPeriod) {
  const snapshots = await Promise.all(
    PERIODS.map(async (period) => {
      const response = await fetch(`/api/dashboard/snapshot?period=${encodeURIComponent(period)}`);
      if (!response.ok) {
        throw new Error(`Snapshot request failed: ${response.status}`);
      }
      const snapshot = await response.json();
      periodSnapshots[period] = snapshot;
      return snapshot;
    }),
  );
  const activeSnapshot = snapshots.find((snapshot) => snapshot.period === activePeriod) || snapshots[0];
  selectedPeriod = activeSnapshot.period;
  renderSnapshot(activeSnapshot);
  return activeSnapshot;
}

function showToast(message) {
  const toast = document.getElementById("live-toast");
  if (!toast) {
    return;
  }
  toast.textContent = message;
  toast.classList.add("is-visible");
  toast.setAttribute("aria-hidden", "false");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    toast.classList.remove("is-visible");
    toast.setAttribute("aria-hidden", "true");
  }, 2600);
}

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/dashboard`);

  socket.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    if (payload.snapshot) {
      refreshAllPeriods(selectedPeriod).catch((error) => console.error(error));
    }
    if (payload.type === "egg_detected") {
      showToast(payload.toast || "1 new egg added");
    } else if (payload.toast) {
      showToast(payload.toast);
    }
  });

  socket.addEventListener("close", () => {
    window.setTimeout(connectWebSocket, 1500);
  });
}

async function handleCollect() {
  const confirmed = window.confirm("Mark all currently visible eggs as collected?");
  if (!confirmed) {
    return;
  }

  const response = await fetch("/api/dashboard/collect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    throw new Error(`Collection request failed: ${response.status}`);
  }

  const payload = await response.json();
  await refreshAllPeriods(selectedPeriod);
  showToast(payload.message || "Collection saved");
}

function bindEvents() {
  PERIODS.forEach((period) => {
    const button = document.getElementById(`period-${period}`);
    button?.addEventListener("click", () => {
      loadSnapshot(period).catch((error) => {
        console.error(error);
        showToast("Could not update this period");
      });
    });
  });

  document.getElementById("collect-button")?.addEventListener("click", () => {
    handleCollect().catch((error) => {
      console.error(error);
      showToast("Collection failed");
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  refreshAllPeriods().catch((error) => {
    console.error(error);
    showToast("Could not load dashboard");
  });
  connectWebSocket();
});
