/* global Chart */

let chartInstance = null;
/** @type {{ body: object, payload: object } | null} */
let lastExport = null;

function sanitizeBase(name) {
  return String(name || "chart")
    .replace(/[/\\?%*:|"<>]/g, "-")
    .replace(/\s+/g, "_")
    .slice(0, 80);
}

function buildCsvFromChart(payload, body) {
  const x = body.x || "x";
  const y = body.y || "y";
  if (payload.type === "scatter" && Array.isArray(payload.points)) {
    const lines = [`${x},${y}`];
    for (const p of payload.points) {
      lines.push(`${p.x},${p.y}`);
    }
    return lines.join("\n");
  }
  const labels = payload.labels || [];
  const values = payload.values || [];
  const esc = (v) => {
    const s = String(v);
    if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
    return s;
  };
  const lines = [`${esc(x)},${esc(y)}`];
  for (let i = 0; i < labels.length; i++) {
    lines.push(`${esc(labels[i])},${values[i] ?? ""}`);
  }
  return lines.join("\n");
}

function setExportEnabled(on) {
  const b = document.getElementById("btn-export-all");
  if (b) b.disabled = !on;
}

document.getElementById("btn-export-all").addEventListener("click", () => {
  const err = document.getElementById("chart-err");
  err.textContent = "";
  if (!lastExport || !chartInstance) {
    err.textContent = "Render a chart first.";
    return;
  }
  const base = `${sanitizeBase(lastExport.body.file)}_${Date.now()}`;
  const canvas = document.getElementById("chart-main");
  const pngUrl = canvas.toDataURL("image/png");
  const a = document.createElement("a");
  a.href = pngUrl;
  a.download = `${base}.png`;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  const csv = buildCsvFromChart(lastExport.payload, lastExport.body);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a2 = document.createElement("a");
  a2.href = url;
  a2.download = `${base}.csv`;
  a2.rel = "noopener";
  document.body.appendChild(a2);
  a2.click();
  document.body.removeChild(a2);
  URL.revokeObjectURL(url);
});

async function loadDatasets() {
  const res = await fetch("/api/datasets");
  const data = await res.json();
  const sel = document.getElementById("ds-file");
  sel.innerHTML = "";
  const sets = data.datasets || [];
  for (const d of sets) {
    if (d.error) continue;
    const o = document.createElement("option");
    o.value = d.rel;
    o.textContent = `${d.rel} (${d.rows} rows)`;
    sel.appendChild(o);
  }
  if (sets.length) {
    sel.dispatchEvent(new Event("change"));
  }
}

function fillColumns(ds) {
  const cols = ds.columns || [];
  const sx = document.getElementById("ds-x");
  const sy = document.getElementById("ds-y");
  sx.innerHTML = "";
  sy.innerHTML = "";
  for (const c of cols) {
    const ox = document.createElement("option");
    ox.value = c.name;
    ox.textContent = `${c.name} (${c.dtype})`;
    sx.appendChild(ox);
    const oy = document.createElement("option");
    oy.value = c.name;
    oy.textContent = `${c.name} (${c.dtype})`;
    sy.appendChild(oy);
  }
}

document.getElementById("ds-file").addEventListener("change", async () => {
  const rel = document.getElementById("ds-file").value;
  const res = await fetch("/api/datasets");
  const data = await res.json();
  const ds = (data.datasets || []).find((d) => d.rel === rel);
  if (ds) fillColumns(ds);
});

document.getElementById("btn-render").addEventListener("click", async () => {
  const err = document.getElementById("chart-err");
  err.textContent = "";
  const body = {
    file: document.getElementById("ds-file").value,
    x: document.getElementById("ds-x").value,
    y: document.getElementById("ds-y").value,
    chart: document.getElementById("ds-chart").value,
    agg: document.getElementById("ds-agg").value,
    limit: parseInt(document.getElementById("ds-limit").value, 10) || 60,
  };
  const res = await fetch("/api/chart-data", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await res.json();
  if (!res.ok) {
    err.textContent = payload.error || "Request failed";
    setExportEnabled(false);
    lastExport = null;
    return;
  }
  lastExport = { body, payload };
  setExportEnabled(true);
  const ctx = document.getElementById("chart-main").getContext("2d");
  if (chartInstance) chartInstance.destroy();
  if (payload.type === "scatter") {
    chartInstance = new Chart(ctx, {
      type: "scatter",
      data: {
        datasets: [
          {
            label: `${body.y} vs ${body.x}`,
            data: payload.points,
            backgroundColor: "rgba(110,181,255,0.5)",
          },
        ],
      },
      options: {
        parsing: false,
        scales: {
          x: { title: { display: true, text: body.x } },
          y: { title: { display: true, text: body.y } },
        },
      },
    });
  } else {
    chartInstance = new Chart(ctx, {
      type: payload.type === "bar" ? "bar" : "line",
      data: {
        labels: payload.labels,
        datasets: [
          {
            label: body.y,
            data: payload.values,
            backgroundColor:
              payload.type === "bar"
                ? "rgba(110,181,255,0.7)"
                : "rgba(110,181,255,0.3)",
            borderColor: "rgba(110,181,255,1)",
            borderWidth: 1,
            fill: payload.type === "line",
          },
        ],
      },
      options: {
        scales: {
          y: { beginAtZero: true },
        },
      },
    });
  }
});

document.getElementById("btn-chat").addEventListener("click", async () => {
  const out = document.getElementById("chat-out");
  const err = document.getElementById("chat-err");
  err.textContent = "";
  out.textContent = "…";
  const message = document.getElementById("chat-in").value.trim();
  if (!message) return;
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  const data = await res.json();
  if (!res.ok || data.error) {
    out.textContent = "";
    err.textContent = data.hint
      ? `${data.error}\n${data.hint}`
      : data.error || "Chat failed";
    return;
  }
  out.textContent = data.reply || "";
});

loadDatasets().catch((e) => {
  document.getElementById("chart-err").textContent = String(e);
});
