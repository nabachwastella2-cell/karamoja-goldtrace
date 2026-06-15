const state = {
  token: localStorage.getItem("goldtrace_token"),
  user: JSON.parse(localStorage.getItem("goldtrace_user") || "null"),
  view: "dashboard",
  data: {}
};

const qs = (selector) => document.querySelector(selector);
const money = (value) => `$${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
const grams = (value) => `${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })} g`;
const nice = (value) => String(value || "").replaceAll("_", " ");

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "content-type": "application/json",
      ...(state.token ? { authorization: `Bearer ${state.token}` } : {}),
      ...(options.headers || {})
    }
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

function showApp() {
  qs("#loginView").classList.toggle("hidden", Boolean(state.token));
  qs("#appView").classList.toggle("hidden", !state.token);
  if (state.user) {
    qs("#roleLabel").textContent = `${state.user.name || state.user.email} - ${state.user.role}`;
  }
}

async function login(event) {
  event.preventDefault();
  qs("#loginError").textContent = "";
  try {
    const data = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: qs("#email").value, password: qs("#password").value })
    });
    state.token = data.token;
    state.user = data.user;
    localStorage.setItem("goldtrace_token", state.token);
    localStorage.setItem("goldtrace_user", JSON.stringify(state.user));
    showApp();
    await loadAll();
  } catch (error) {
    qs("#loginError").textContent = error.message;
  }
}

function logout() {
  localStorage.removeItem("goldtrace_token");
  localStorage.removeItem("goldtrace_user");
  state.token = null;
  state.user = null;
  showApp();
}

async function loadAll() {
  if (!state.token) return;
  const [dashboard, ledger, batches, escrows, blocks, audits, prices] = await Promise.all([
    api("/api/dashboard"),
    api("/api/ledger"),
    api("/api/batches"),
    api("/api/escrows"),
    api("/api/mining-blocks"),
    api("/api/audits"),
    api("/api/prices")
  ]);
  state.data = { dashboard, ledger, batches, escrows, blocks, audits, prices };
  render();
}

function setView(view) {
  state.view = view;
  document.querySelectorAll(".nav").forEach((btn) => btn.classList.toggle("active", btn.dataset.view === view));
  document.querySelectorAll(".view").forEach((el) => el.classList.toggle("active", el.id === view));
  qs("#viewTitle").textContent = document.querySelector(`[data-view="${view}"]`).textContent.trim();
}

function render() {
  if (!state.data.dashboard) return;
  renderDashboard();
  renderBatches();
  renderEscrow();
  renderBlocks();
  renderAudits();
  renderPrices();
  renderExport();
}

function renderDashboard() {
  const data = state.data.dashboard;
  const funded = data.escrow_by_status.find((item) => item.status === "funded")?.amount || 0;
  const statusBars = data.batch_status.map((item) => {
    const width = Math.max(12, item.count * 24);
    return `<div class="bar"><b>${nice(item.status)}</b><span><i style="width:${width}%"></i></span><em>${item.count}</em></div>`;
  }).join("");
  const benefits = data.benefits.map((benefit) => {
    const [title, ...body] = benefit.split(":");
    return `<div class="benefit"><b>${title}</b><span class="muted">${body.join(":").trim()}</span></div>`;
  }).join("");
  const latestEvents = state.data.ledger.events.slice(0, 3).map((event) => `
    <article class="card event">
      <span class="status-pill gold">${nice(event.event_type)}</span>
      <h3>${event.batch_code}</h3>
      <p>${event.notes}</p>
      <p class="muted">${event.actor} - ${event.created_at}</p>
    </article>`).join("");

  qs("#dashboard").innerHTML = `
    <article class="card hero-card">
      <p class="eyebrow">Command center</p>
      <h3>Good morning, ${state.user?.name || "Regulator"}. Every certified gram is visible.</h3>
      <p>Monitor cooperative allocations, ethical extraction, escrow releases, and export readiness from one secure regulator dashboard.</p>
    </article>
    <div class="grid cards" style="margin-top:16px">
      <article class="card"><p class="eyebrow">Traceable lots</p><p class="metric">${data.totals.batches}</p><span class="muted">${grams(data.totals.grams)} gross gold</span></article>
      <article class="card"><p class="eyebrow">Fine gold</p><p class="metric">${grams(data.totals.fine_grams)}</p><span class="muted">Purity-adjusted supply</span></article>
      <article class="card"><p class="eyebrow">Escrow protected</p><p class="metric">${money(funded)}</p><span class="muted">Funded transaction value</span></article>
      <article class="card"><p class="eyebrow">Spot price</p><p class="metric">${money(data.latest_price.price_usd_per_gram)}</p><span class="muted">USD per gram</span></article>
    </div>
    <div class="grid two" style="margin-top:16px">
      <article class="card"><h3>Supply status</h3><div class="bars">${statusBars}</div></article>
      <article class="card image-card"><img src="/assets/certified-gold.svg" alt="Certified fair-trade gold bars" /><div class="pad"><h3>Compliance signal</h3><p class="muted">Average audit health is ${data.audit.avg_score}% with a lowest score of ${data.audit.min_score}%.</p></div></article>
    </div>
    <div class="benefit-grid" style="margin-top:16px">${benefits}</div>
    <div class="grid three" style="margin-top:16px">${latestEvents}</div>`;
}

function renderBatches() {
  const rows = state.data.batches.batches.map((batch) => `
    <tr>
      <td><b>${batch.batch_code}</b><br><span class="muted">${batch.district} - ${batch.block_code}</span></td>
      <td>${batch.cooperative}</td>
      <td>${batch.current_holder}</td>
      <td>${grams(batch.gross_weight_g)}</td>
      <td>${batch.purity_pct}%</td>
      <td>${batch.fair_trade_premium_pct}%</td>
      <td><span class="status-pill">${nice(batch.status)}</span></td>
    </tr>`).join("");
  qs("#batches").innerHTML = `
    <div class="grid two">
      <article class="card image-card"><img src="/assets/karamoja-landscape.svg" alt="Karamoja gold mining landscape" /><div class="pad"><h3>Gold lots registry</h3><p class="muted">Cooperative allocations are tied to licensed blocks, custody holders, purity, and fair-trade premium records.</p></div></article>
      <article class="card"><h3>Traceability rules</h3><p><span class="status-pill gold">Allocation</span> Lot created at a registered block.</p><p><span class="status-pill gold">Custody</span> Holder changes are written to the ledger.</p><p><span class="status-pill gold">Certification</span> Export requires audit and escrow evidence.</p></article>
    </div>
    <div class="table-wrap" style="margin-top:16px"><table><thead><tr><th>Lot</th><th>Cooperative</th><th>Holder</th><th>Gross</th><th>Purity</th><th>Premium</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table></div>
    <div class="timeline" style="margin-top:16px">${renderLedgerEvents()}</div>`;
}

function renderLedgerEvents() {
  return state.data.ledger.events.map((event) => `
    <article class="card event">
      <div class="status-pill">${nice(event.event_type)}</div>
      <h3>${event.batch_code}</h3>
      <p>${event.notes}</p>
      <p class="muted">${event.actor} - ${event.created_at}</p>
      <p class="hash">hash ${event.event_hash}${event.previous_hash ? ` - prev ${event.previous_hash}` : ""}</p>
    </article>`).join("");
}

function renderEscrow() {
  const rows = state.data.escrows.escrows.map((e) => `
    <tr>
      <td><b>${e.batch_code}</b><br><span class="muted">${e.release_conditions}</span></td>
      <td>${e.buyer}</td>
      <td>${e.seller}</td>
      <td>${money(e.amount_usd)}</td>
      <td><span class="status-pill">${nice(e.status)}</span></td>
      <td>${e.status !== "released" ? `<button class="secondary" onclick="releaseEscrow(${e.id})">Release</button>` : e.released_at}</td>
    </tr>`).join("");
  qs("#escrow").innerHTML = `
    <div class="grid two">
      <article class="card image-card"><img src="/assets/refinery-chain.svg" alt="Cooperative to refiner to export chain" /><div class="pad"><h3>Escrow desk</h3><p class="muted">Protected buyer funds move only after assay, audit, and export milestones are satisfied.</p></div></article>
      <article class="card"><h3>Security model</h3><p>Signed tokens, role checks, audit logs, and append-only custody hashes protect transaction operations.</p></article>
    </div>
    <div class="table-wrap" style="margin-top:16px"><table><thead><tr><th>Batch</th><th>Buyer</th><th>Seller</th><th>Amount</th><th>Status</th><th>Action</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

async function releaseEscrow(id) {
  await api(`/api/escrows/${id}/release`, { method: "POST" });
  await loadAll();
}
window.releaseEscrow = releaseEscrow;

function renderBlocks() {
  const cards = state.data.blocks.blocks.map((b) => `
    <article class="card block-card">
      <span class="status-pill">${nice(b.license_status)}</span>
      <h3>${b.block_code}</h3>
      <p>${b.district} - ${b.cooperative}</p>
      <p class="muted">Geofence ${b.radius_km} km around ${b.latitude}, ${b.longitude}</p>
      <p>Environment: <b>${nice(b.environmental_status)}</b></p>
    </article>`).join("");
  qs("#blocks").innerHTML = `
    <article class="card image-card"><img src="/assets/block-registry.svg" alt="Map of registered Karamoja mining blocks" /><div class="pad"><h3>Geo-fenced block registry</h3><p class="muted">Registered extraction zones link each gold lot to an approved location and environmental status.</p></div></article>
    <div class="map-list" style="margin-top:16px">${cards}</div>`;
}

function renderAudits() {
  const rows = state.data.audits.audits.map((a) => `
    <tr>
      <td><b>${a.batch_code}</b><br>${nice(a.audit_type)}</td>
      <td>${a.auditor}</td>
      <td>${a.score}%</td>
      <td>${a.finding}</td>
      <td>${a.corrective_action || "None"}</td>
      <td>${a.created_at}</td>
    </tr>`).join("");
  qs("#audits").innerHTML = `
    <div class="grid three">
      <article class="card"><p class="eyebrow">Labor</p><p class="metric">PPE</p><span class="muted">Worker payment and safety controls tracked.</span></article>
      <article class="card"><p class="eyebrow">Environment</p><p class="metric">Water</p><span class="muted">Settling controls and extraction impacts monitored.</span></article>
      <article class="card"><p class="eyebrow">Custody</p><p class="metric">Hash</p><span class="muted">Seals and custody records checked against ledger hashes.</span></article>
    </div>
    <div class="table-wrap" style="margin-top:16px"><table><thead><tr><th>Audit</th><th>Auditor</th><th>Score</th><th>Finding</th><th>Corrective action</th><th>Date</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderPrices() {
  const prices = state.data.prices.prices;
  const width = 760;
  const height = 220;
  const min = Math.min(...prices.map((p) => p.price_usd_per_gram)) - 0.5;
  const max = Math.max(...prices.map((p) => p.price_usd_per_gram)) + 0.5;
  const pointList = prices.map((p, index) => {
    const x = 30 + index * ((width - 60) / Math.max(1, prices.length - 1));
    const y = height - 25 - ((p.price_usd_per_gram - min) / (max - min)) * (height - 55);
    return { x, y };
  });
  const points = pointList.map((p) => `${p.x},${p.y}`).join(" ");
  const rows = state.data.prices.valuations.map((v) => `
    <tr><td>${v.batch_code}</td><td>${grams(v.fine_grams)}</td><td>${v.fair_trade_premium_pct}%</td><td>${money(v.spot_value_usd)}</td><td><b>${money(v.fair_trade_value_usd)}</b></td></tr>`).join("");
  qs("#prices").innerHTML = `
    <article class="card">
      <p class="eyebrow">Gold-price spot analytics fabric</p>
      <h3>Latest source price: ${money(prices.at(-1).price_usd_per_gram)} per gram</h3>
      <svg class="price-line" viewBox="0 0 ${width} ${height}" role="img" aria-label="Gold price trend">
        <polyline fill="none" stroke="#d6a53e" stroke-width="5" points="${points}" />
        ${pointList.map((p) => `<circle cx="${p.x}" cy="${p.y}" r="5" fill="#176b4d" />`).join("")}
      </svg>
    </article>
    <div class="table-wrap" style="margin-top:16px"><table><thead><tr><th>Batch</th><th>Fine grams</th><th>Premium</th><th>Spot value</th><th>Fair-trade value</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderExport() {
  const batches = state.data.batches.batches;
  const escrows = state.data.escrows.escrows;
  const audits = state.data.audits.audits;
  const rows = batches.map((batch) => {
    const escrow = escrows.find((e) => e.batch_code === batch.batch_code);
    const batchAudits = audits.filter((a) => a.batch_code === batch.batch_code);
    const auditScore = batchAudits.length ? Math.round(batchAudits.reduce((sum, a) => sum + a.score, 0) / batchAudits.length) : 0;
    const ready = batch.status === "certified" || batch.status === "exported" || (escrow?.status === "released" && auditScore >= 85);
    return `
      <tr>
        <td><b>${batch.batch_code}</b><br><span class="muted">${batch.current_holder}</span></td>
        <td>${nice(batch.status)}</td>
        <td>${escrow ? nice(escrow.status) : "not opened"}</td>
        <td>${auditScore || "pending"}${auditScore ? "%" : ""}</td>
        <td><span class="status-pill ${ready ? "gold" : ""}">${ready ? "ready" : "hold"}</span></td>
      </tr>`;
  }).join("");
  qs("#export").innerHTML = `
    <div class="grid two">
      <article class="card image-card"><img src="/assets/certified-gold.svg" alt="Certified export-ready gold" /><div class="pad"><h3>Export readiness</h3><p class="muted">International buyers can trust certified gold when lot status, escrow release, audit score, and provenance line up.</p></div></article>
      <article class="card"><h3>Readiness gate</h3><p><span class="status-pill gold">Certified</span> Chain-of-custody complete.</p><p><span class="status-pill gold">Released</span> Escrow milestone cleared.</p><p><span class="status-pill gold">85%+</span> Ethical audit threshold met.</p></article>
    </div>
    <div class="table-wrap" style="margin-top:16px"><table><thead><tr><th>Lot</th><th>Status</th><th>Escrow</th><th>Audit score</th><th>Decision</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

qs("#loginForm").addEventListener("submit", login);
qs("#logoutBtn").addEventListener("click", logout);
qs("#refreshBtn").addEventListener("click", loadAll);
document.querySelectorAll(".nav").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
showApp();
setView("dashboard");
loadAll().catch(() => logout());
