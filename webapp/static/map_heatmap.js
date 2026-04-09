/**
 * Leaflet + OSM: strong heat gradient, per-state circle markers, sidebar, layer toggles.
 */
(function () {
  const cfg = window.__HEATMAP__;
  if (!cfg || !cfg.dataUrl) return;

  const el = document.getElementById("map-heatmap");
  const statusEl = document.getElementById("heatmap-status");
  const emptyEl = document.getElementById("heatmap-empty");
  const listEl = document.getElementById("map-state-list");

  /** @type {L.Map|null} */
  let leafMap = null;
  /** @type {L.Layer|null} */
  let heatLayer = null;
  /** @type {L.FeatureGroup|null} */
  let circlesLayer = null;
  /** @type {Map<string, L.CircleMarker>} */
  const markersByState = new Map();

  const layersVisible = { heat: true, circles: true };

  function setStatus(msg) {
    if (statusEl) statusEl.textContent = msg || "";
  }

  function waitForLeaflet() {
    return new Promise(function (resolve, reject) {
      let n = 0;
      const t = setInterval(function () {
        if (typeof L !== "undefined" && typeof L.heatLayer === "function") {
          clearInterval(t);
          resolve();
        } else if (++n > 200) {
          clearInterval(t);
          reject(new Error("Leaflet failed to load"));
        }
      }, 50);
    });
  }

  async function fetchData(weight) {
    const u = new URL(cfg.dataUrl, window.location.origin);
    u.searchParams.set("weight", weight === "revenue" ? "revenue" : "orders");
    const r = await fetch(u.toString());
    if (!r.ok) throw new Error("Failed to load heatmap data");
    return r.json();
  }

  function showEmpty(data) {
    const has = data.points && data.points.length > 0;
    if (emptyEl) emptyEl.classList.toggle("hidden", has);
    if (el) el.classList.toggle("hidden", !has);
    const explorer = document.querySelector(".map-explorer");
    if (explorer) explorer.classList.toggle("hidden", !has);
    return has;
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function fmtMoney(n) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(n);
  }

  function weightColor(weight, wMin, wMax) {
    if (wMax <= wMin) return "hsl(200, 80%, 42%)";
    const t = (weight - wMin) / (wMax - wMin);
    const h = 210 * (1 - t) + 0 * t;
    const s = 88;
    const l = 42 + 12 * (1 - t);
    return "hsl(" + h + "," + s + "%," + l + "%)";
  }

  function destroyLeaflet() {
    markersByState.clear();
    heatLayer = null;
    circlesLayer = null;
    if (leafMap) {
      leafMap.remove();
      leafMap = null;
    }
    if (listEl) listEl.innerHTML = "";
  }

  function applyLayerVisibility() {
    if (!leafMap) return;
    if (heatLayer) {
      if (layersVisible.heat) leafMap.addLayer(heatLayer);
      else leafMap.removeLayer(heatLayer);
    }
    if (circlesLayer) {
      if (layersVisible.circles) leafMap.addLayer(circlesLayer);
      else leafMap.removeLayer(circlesLayer);
    }
    const ch = document.getElementById("toggle-heat-layer");
    const cc = document.getElementById("toggle-circles");
    if (ch) ch.checked = layersVisible.heat;
    if (cc) cc.checked = layersVisible.circles;
  }

  function focusState(abbr) {
    const m = markersByState.get(abbr);
    if (!m || !leafMap) return;
    const ll = m.getLatLng();
    leafMap.flyTo(ll, Math.max(leafMap.getZoom(), 6), { duration: 0.6 });
    m.openPopup();
    listEl.querySelectorAll(".map-state-row").forEach(function (row) {
      row.classList.toggle("active", row.getAttribute("data-state") === abbr);
    });
  }

  function buildSidebar(sortedPoints) {
    if (!listEl) return;
    listEl.innerHTML = "";
    sortedPoints.forEach(function (p, idx) {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "map-state-row";
      row.setAttribute("data-state", p.state);
      row.innerHTML =
        '<span class="map-state-rank">#' +
        (idx + 1) +
        "</span>" +
        '<span class="map-state-abbr">' +
        escapeHtml(p.state) +
        "</span>" +
        '<span class="map-state-metrics"><span class="n-ord">' +
        p.n_orders +
        ' orders</span><span class="n-rev">' +
        fmtMoney(p.net_revenue) +
        "</span></span></span>";
      row.addEventListener("click", function () {
        focusState(p.state);
      });
      listEl.appendChild(row);
    });
  }

  function renderLeaflet(data) {
    destroyLeaflet();
    if (!showEmpty(data)) return;

    const points = data.points.slice();
    const sortedForSidebar = points.slice().sort(function (a, b) {
      return b.n_orders - a.n_orders;
    });

    const wList = points.map(function (p) {
      return p.weight;
    });
    const wMin = Math.min.apply(null, wList);
    const wMax = Math.max.apply(null, wList);

    leafMap = L.map(el, { scrollWheelZoom: true }).setView([39.5, -98.35], 4);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(leafMap);

    const heatPoints = points.map(function (p) {
      return [p.lat, p.lng, p.weight];
    });
    const heatMax = wMax > 0 ? wMax * 0.92 : 1;

    heatLayer = L.heatLayer(heatPoints, {
      radius: 72,
      blur: 38,
      minOpacity: 0.35,
      maxZoom: 17,
      max: heatMax,
      gradient: {
        0.0: "#1e3a5f",
        0.25: "#0066cc",
        0.45: "#00a86b",
        0.65: "#d4a017",
        0.85: "#e85d04",
        1.0: "#dc2f02",
      },
    });

    circlesLayer = L.featureGroup();
    const nMax = Math.max.apply(
      null,
      points.map(function (p) {
        return p.n_orders;
      })
    );

    points.forEach(function (p) {
      const radiusPx = 14 + 46 * Math.sqrt(p.n_orders / Math.max(nMax, 1));
      const fill = weightColor(p.weight, wMin, wMax);
      const cm = L.circleMarker([p.lat, p.lng], {
        radius: radiusPx,
        stroke: true,
        weight: 2.5,
        color: "#0f1419",
        opacity: 0.95,
        fillColor: fill,
        fillOpacity: 0.82,
      });

      const tip =
        "<strong>" +
        escapeHtml(p.state) +
        "</strong><br>" +
        p.n_orders +
        " orders · " +
        fmtMoney(p.net_revenue);
      cm.bindTooltip(tip, {
        direction: "top",
        sticky: true,
        opacity: 0.95,
        className: "map-state-tooltip",
      });

      const popupHtml =
        "<div class='map-popup-inner'>" +
        "<h4>" +
        escapeHtml(p.state) +
        "</h4>" +
        "<dl>" +
        "<dt>Orders</dt><dd>" +
        p.n_orders +
        "</dd>" +
        "<dt>Net revenue</dt><dd>" +
        fmtMoney(p.net_revenue) +
        "</dd>" +
        "</dl>" +
        "</div>";
      cm.bindPopup(popupHtml, {
        maxWidth: 260,
        className: "map-popup-themed",
        autoPanPadding: [20, 20],
      });

      cm.on("click", function () {
        listEl.querySelectorAll(".map-state-row").forEach(function (row) {
          row.classList.toggle("active", row.getAttribute("data-state") === p.state);
        });
      });
      cm.on("mouseover", function (ev) {
        ev.target.bringToFront();
      });

      markersByState.set(p.state, cm);
      circlesLayer.addLayer(cm);
    });

    const farmIcon = L.divIcon({
      className: "farm-star-marker",
      html: '<span aria-hidden="true">★</span>',
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    });
    L.marker([data.farm.lat, data.farm.lng], {
      title: data.farm.title,
      icon: farmIcon,
      zIndexOffset: 1000,
      riseOnHover: true,
    })
      .addTo(leafMap)
      .bindPopup("<strong>" + escapeHtml(data.farm.title) + "</strong>", {
        className: "map-popup-themed",
      });

    applyLayerVisibility();

    const bounds = L.latLngBounds(
      points.map(function (p) {
        return [p.lat, p.lng];
      })
    );
    bounds.extend([data.farm.lat, data.farm.lng]);
    leafMap.fitBounds(bounds, { padding: [48, 48], maxZoom: 7 });

    buildSidebar(sortedForSidebar);
    setTimeout(function () {
      leafMap.invalidateSize();
    }, 300);

    leafMap.whenReady(function () {
      leafMap.invalidateSize();
    });
  }

  async function run(weight) {
    setStatus("Loading…");
    try {
      const data = await fetchData(weight);
      if (data.meta && data.meta.message && (!data.points || !data.points.length)) {
        setStatus(data.meta.message);
      } else if (data.meta && data.meta.source) {
        setStatus(data.meta.source + " · " + (data.meta.weight_by || weight));
      } else {
        setStatus("");
      }

      await waitForLeaflet();
      renderLeaflet(data);
    } catch (e) {
      setStatus("Error: " + (e.message || String(e)));
      if (emptyEl) {
        emptyEl.textContent =
          "Could not draw map. Check the browser console and network (OpenStreetMap tiles).";
        emptyEl.classList.remove("hidden");
      }
      if (el) el.classList.add("hidden");
    }
  }

  window.__HEATMAP_RERUN__ = function (weight) {
    run(weight || "orders");
  };

  window.__HEATMAP_TOGGLE_LAYERS__ = function (opts) {
    if (opts.heat !== undefined) layersVisible.heat = !!opts.heat;
    if (opts.circles !== undefined) layersVisible.circles = !!opts.circles;
    applyLayerVisibility();
  };

  function start() {
    const sel = document.getElementById("heatmap-weight");
    const w = sel && sel.value ? sel.value : "orders";
    const ch = document.getElementById("toggle-heat-layer");
    const cc = document.getElementById("toggle-circles");
    if (ch) layersVisible.heat = ch.checked;
    if (cc) layersVisible.circles = cc.checked;
    run(w);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
