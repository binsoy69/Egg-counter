function setHistoryTotal(count) {
  const total = document.getElementById("history-total");
  if (total) {
    total.textContent = `${count} record${count === 1 ? "" : "s"}`;
  }
}

function formatDisplayDate(value) {
  return new Date(value).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatDisplayTimestamp(value) {
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function renderHistory(records) {
  const container = document.getElementById("history-records");
  if (!container) {
    return;
  }

  setHistoryTotal(records.length);

  if (!records.length) {
    container.innerHTML = '<div class="history-empty">No egg records match these filters yet.</div>';
    return;
  }

  container.innerHTML = records.map((record) => `
    <article class="history-record" data-timestamp="${record.timestamp}">
      <div class="history-record-date">${formatDisplayDate(record.detected_date)}</div>
      <span class="history-size-badge history-size-${record.size}">${record.size}</span>
      <div class="history-record-timestamp">${formatDisplayTimestamp(record.timestamp)}</div>
    </article>
  `).join("");
}

function readFilters() {
  return {
    size: document.getElementById("filter-size")?.value || "",
    from: document.getElementById("filter-from")?.value || "",
    to: document.getElementById("filter-to")?.value || "",
  };
}

function applyFiltersToInputs(params) {
  const size = params.get("size") || "";
  const from = params.get("from") || "";
  const to = params.get("to") || "";

  document.getElementById("filter-size").value = size;
  document.getElementById("filter-from").value = from;
  document.getElementById("filter-to").value = to;
}

function syncUrl(filters) {
  const params = new URLSearchParams();
  if (filters.size) {
    params.set("size", filters.size);
  }
  if (filters.from) {
    params.set("from", filters.from);
  }
  if (filters.to) {
    params.set("to", filters.to);
  }
  const query = params.toString();
  window.history.replaceState({}, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
}

async function loadHistory() {
  const filters = readFilters();
  syncUrl(filters);

  const params = new URLSearchParams();
  if (filters.size) {
    params.set("size", filters.size);
  }
  if (filters.from) {
    params.set("from", filters.from);
  }
  if (filters.to) {
    params.set("to", filters.to);
  }

  const response = await fetch(`/api/history?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`History request failed: ${response.status}`);
  }

  const records = await response.json();
  renderHistory(records);
}

document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  applyFiltersToInputs(params);
  document.getElementById("history-filters")?.addEventListener("input", () => {
    loadHistory().catch((error) => console.error(error));
  });
  loadHistory().catch((error) => console.error(error));
});
