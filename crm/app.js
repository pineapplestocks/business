const PITCH_STATUS_OPTIONS = [
  "new",
  "attempting_contact",
  "contacted",
  "follow_up",
  "interested",
  "proposal_sent",
  "won",
  "lost",
  "do_not_call",
]

const CALL_OUTCOME_OPTIONS = [
  "not_called",
  "no_answer",
  "left_voicemail",
  "bad_number",
  "spoke_needs_follow_up",
  "not_interested",
  "demo_sent",
  "sold",
]

const CRM_EDITABLE_FIELDS = [
  "pitch_status",
  "call_outcome",
  "last_called_on",
  "next_follow_up_on",
  "owner_name",
  "owner_email",
  "quoted_price",
  "sale_amount",
  "sale_date",
  "call_summary",
  "notes",
]

const CRM_CSV_FIELDS = [
  "business_name",
  "trade",
  "city",
  "state",
  "phone",
  "pitch_status",
  "call_outcome",
  "last_called_on",
  "next_follow_up_on",
  "sale_amount",
  "google_maps_url",
  "generated_site_url",
  "notes",
  "call_summary",
]

const CONNECTION_STORAGE_KEY = "business-crm-api-connection"

const state = {
  mode: "loading",
  records: [],
  stats: {},
  options: {
    pitch_statuses: PITCH_STATUS_OPTIONS,
    call_outcomes: CALL_OUTCOME_OPTIONS,
    editable_fields: CRM_EDITABLE_FIELDS,
  },
  selectedId: null,
  publishedUpdatedAt: "",
  sourceFile: "",
  connection: {
    baseUrl: "",
    token: "",
  },
  apiConfig: {
    auth_required: false,
  },
  connectionPanelOpen: false,
  filters: {
    search: "",
    pitchStatus: "",
    callOutcome: "",
    showArchived: false,
  },
}

const elements = {
  modeBadge: document.querySelector("#modeBadge"),
  modeNotice: document.querySelector("#modeNotice"),
  connectionPanel: document.querySelector("#connectionPanel"),
  connectionToggleButton: document.querySelector("#connectionToggleButton"),
  apiBaseInput: document.querySelector("#apiBaseInput"),
  apiTokenInput: document.querySelector("#apiTokenInput"),
  saveConnectionButton: document.querySelector("#saveConnectionButton"),
  clearConnectionButton: document.querySelector("#clearConnectionButton"),
  connectionMessage: document.querySelector("#connectionMessage"),
  statsRow: document.querySelector("#statsRow"),
  searchInput: document.querySelector("#searchInput"),
  pitchFilter: document.querySelector("#pitchFilter"),
  outcomeFilter: document.querySelector("#outcomeFilter"),
  showArchived: document.querySelector("#showArchived"),
  leadList: document.querySelector("#leadList"),
  recordCount: document.querySelector("#recordCount"),
  emptyState: document.querySelector("#emptyState"),
  detailPane: document.querySelector("#detailPane"),
  detailTrade: document.querySelector("#detailTrade"),
  detailName: document.querySelector("#detailName"),
  detailLocation: document.querySelector("#detailLocation"),
  callLink: document.querySelector("#callLink"),
  siteLink: document.querySelector("#siteLink"),
  mapsLink: document.querySelector("#mapsLink"),
  verificationStatus: document.querySelector("#verificationStatus"),
  verificationNotes: document.querySelector("#verificationNotes"),
  detailPhone: document.querySelector("#detailPhone"),
  detailCategory: document.querySelector("#detailCategory"),
  detailSourceQuery: document.querySelector("#detailSourceQuery"),
  detailUpdatedAt: document.querySelector("#detailUpdatedAt"),
  recordForm: document.querySelector("#recordForm"),
  saveMessage: document.querySelector("#saveMessage"),
  saveButton: document.querySelector("#saveButton"),
  syncButton: document.querySelector("#syncButton"),
  exportCsvButton: document.querySelector("#exportCsvButton"),
}

const formFields = [...CRM_EDITABLE_FIELDS]

function labelize(value) {
  return (value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;")
}

function formatDateTime(value) {
  if (!value) {
    return ""
  }
  const timestamp = new Date(value)
  if (Number.isNaN(timestamp.getTime())) {
    return value
  }
  return timestamp.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  })
}

function selectedRecord() {
  return state.records.find((record) => record.record_id === state.selectedId) || null
}

function visibleRecords() {
  const search = state.filters.search.trim().toLowerCase()
  return state.records.filter((record) => {
    if (!state.filters.showArchived && record.active === false) {
      return false
    }
    if (state.filters.pitchStatus && record.pitch_status !== state.filters.pitchStatus) {
      return false
    }
    if (state.filters.callOutcome && record.call_outcome !== state.filters.callOutcome) {
      return false
    }
    if (!search) {
      return true
    }
    const haystack = [
      record.business_name,
      record.city,
      record.state,
      record.phone,
      record.notes,
      record.call_summary,
    ]
      .join(" ")
      .toLowerCase()
    return haystack.includes(search)
  })
}

function sortRecords(records) {
  return [...records].sort((left, right) => {
    const leftFollowUp = left.next_follow_up_on || "9999-99-99"
    const rightFollowUp = right.next_follow_up_on || "9999-99-99"
    if (left.active !== right.active) {
      return left.active === false ? 1 : -1
    }
    if (leftFollowUp !== rightFollowUp) {
      return leftFollowUp.localeCompare(rightFollowUp)
    }
    return `${left.city} ${left.business_name}`.localeCompare(`${right.city} ${right.business_name}`)
  })
}

function computeStats(records) {
  const activeRecords = records.filter((record) => record.active !== false)
  const byPitchStatus = {}
  for (const record of activeRecords) {
    const key = record.pitch_status || "new"
    byPitchStatus[key] = (byPitchStatus[key] || 0) + 1
  }

  return {
    total: activeRecords.length,
    won: activeRecords.filter((record) => record.pitch_status === "won").length,
    follow_up: activeRecords.filter((record) => Boolean(record.next_follow_up_on)).length,
    by_pitch_status: byPitchStatus,
  }
}

function normalizeApiBase(baseUrl) {
  return String(baseUrl || "").trim().replace(/\/+$/, "")
}

function sameOriginApiBase() {
  if (window.location.pathname.includes("/crm/")) {
    return ""
  }
  return window.location.origin
}

function loadSavedConnection() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(CONNECTION_STORAGE_KEY) || "null")
    if (!parsed || typeof parsed !== "object") {
      return { baseUrl: "", token: "" }
    }
    return {
      baseUrl: normalizeApiBase(parsed.baseUrl),
      token: String(parsed.token || ""),
    }
  } catch (error) {
    return { baseUrl: "", token: "" }
  }
}

function saveConnection(connection) {
  const normalized = {
    baseUrl: normalizeApiBase(connection.baseUrl),
    token: String(connection.token || ""),
  }
  window.localStorage.setItem(CONNECTION_STORAGE_KEY, JSON.stringify(normalized))
  state.connection = normalized
}

function clearSavedConnection() {
  window.localStorage.removeItem(CONNECTION_STORAGE_KEY)
  state.connection = { baseUrl: "", token: "" }
}

function activeApiBase() {
  return normalizeApiBase(state.connection.baseUrl || sameOriginApiBase())
}

function hasWritableApi() {
  return state.mode === "api" && Boolean(activeApiBase())
}

function apiUrl(path) {
  return new URL(String(path).replace(/^\/+/, ""), `${activeApiBase()}/`).toString()
}

function apiHeaders(extraHeaders = {}) {
  const headers = { ...extraHeaders }
  if (state.connection.token) {
    headers.Authorization = `Bearer ${state.connection.token}`
  }
  return headers
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options)
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`)
  }
  return response.json()
}

async function fetchApiJson(path, options = {}) {
  const headers = apiHeaders(options.headers || {})
  return fetchJson(apiUrl(path), {
    ...options,
    headers,
  })
}

function staticDataUrl() {
  return new URL("../data/crm_records.json", window.location.href).toString()
}

function setSaveMessage(message, tone = "") {
  elements.saveMessage.textContent = message
  elements.saveMessage.className = `save-message${tone ? ` ${tone}` : ""}`
}

function setConnectionMessage(message, tone = "") {
  elements.connectionMessage.textContent = message
  elements.connectionMessage.className = `save-message${tone ? ` ${tone}` : ""}`
}

function setConnectionPanel(open) {
  state.connectionPanelOpen = open
  elements.connectionPanel.classList.toggle("hidden", !open)
}

function renderConnectionFields() {
  elements.apiBaseInput.value = state.connection.baseUrl || sameOriginApiBase()
  elements.apiTokenInput.value = state.connection.token || ""
}

function setFormDisabled(disabled) {
  elements.recordForm.querySelectorAll("input, select, textarea").forEach((field) => {
    field.disabled = disabled
  })
  elements.saveButton.disabled = disabled
  elements.saveButton.textContent = disabled ? "Connect Live CRM To Save" : "Save Record"
}

function setModeUi() {
  renderConnectionFields()

  if (state.mode === "api") {
    elements.modeBadge.textContent = "Live CRM"
    elements.modeBadge.className = "mode-badge mode-api"
    elements.modeNotice.textContent = state.sourceFile
      ? `Connected to the shared CRM API at ${activeApiBase()}. Changes save centrally for every device using this same CRM server. Lead source: ${state.sourceFile}`
      : `Connected to the shared CRM API at ${activeApiBase()}. Changes save centrally for every device using this same CRM server.`
    elements.modeNotice.classList.remove("hidden")
    elements.syncButton.textContent = "Sync Leads"
    setFormDisabled(false)
    return
  }

  elements.modeBadge.textContent = "Public Snapshot"
  elements.modeBadge.className = "mode-badge mode-static"
  elements.modeNotice.textContent = state.publishedUpdatedAt
    ? `Viewing the published CRM snapshot from ${formatDateTime(state.publishedUpdatedAt)}. To save call notes, deal stages, and sales centrally, connect this page to the live CRM API.`
    : "Viewing the published CRM snapshot. To save call notes, deal stages, and sales centrally, connect this page to the live CRM API."
  elements.modeNotice.classList.remove("hidden")
  elements.syncButton.textContent = "Refresh Snapshot"
  setFormDisabled(true)
}

function renderStats() {
  const stats = state.stats || {}
  const stageCounts = stats.by_pitch_status || {}
  const cards = [
    {
      label: "Active Leads",
      value: stats.total || 0,
      text: "Qualified businesses ready for outreach.",
    },
    {
      label: "Won Deals",
      value: stats.won || 0,
      text: "Closed sales currently tracked in the CRM.",
    },
    {
      label: "Follow-Ups",
      value: stats.follow_up || 0,
      text: "Leads with a next follow-up date scheduled.",
    },
    {
      label: "In Motion",
      value: (stageCounts.interested || 0) + (stageCounts.proposal_sent || 0) + (stageCounts.follow_up || 0),
      text: "Leads already moving past the first call.",
    },
  ]

  elements.statsRow.innerHTML = cards
    .map(
      (card) => `
        <article class="stat-card">
          <span class="label">${escapeHtml(card.label)}</span>
          <strong>${escapeHtml(card.value)}</strong>
          <p>${escapeHtml(card.text)}</p>
        </article>
      `,
    )
    .join("")
}

function renderFilters() {
  const pitchOptions = ['<option value="">All stages</option>']
    .concat(
      state.options.pitch_statuses.map(
        (value) =>
          `<option value="${escapeHtml(value)}" ${value === state.filters.pitchStatus ? "selected" : ""}>${escapeHtml(labelize(value))}</option>`,
      ),
    )
    .join("")

  const outcomeOptions = ['<option value="">All outcomes</option>']
    .concat(
      state.options.call_outcomes.map(
        (value) =>
          `<option value="${escapeHtml(value)}" ${value === state.filters.callOutcome ? "selected" : ""}>${escapeHtml(labelize(value))}</option>`,
      ),
    )
    .join("")

  elements.pitchFilter.innerHTML = pitchOptions
  elements.outcomeFilter.innerHTML = outcomeOptions
  elements.showArchived.checked = state.filters.showArchived
  elements.searchInput.value = state.filters.search
}

function renderLeadList() {
  const records = sortRecords(visibleRecords())
  elements.recordCount.textContent = String(records.length)

  if (!records.length) {
    state.selectedId = null
    elements.leadList.innerHTML = '<div class="empty-list">No leads match the current filters.</div>'
    renderDetail()
    return
  }

  if (!records.some((record) => record.record_id === state.selectedId)) {
    state.selectedId = records[0].record_id
  }

  elements.leadList.innerHTML = records
    .map((record) => {
      const isActive = record.record_id === state.selectedId
      const location = [record.city, record.state].filter(Boolean).join(", ")
      const followUp = record.next_follow_up_on ? `Follow-up ${record.next_follow_up_on}` : "No follow-up date"
      const classes = ["lead-item"]
      if (isActive) classes.push("active")

      return `
        <button class="${classes.join(" ")}" data-record-id="${escapeHtml(record.record_id)}" type="button">
          <div class="lead-name">${escapeHtml(record.business_name)}</div>
          <div class="lead-meta">${escapeHtml(location || "Location unknown")} · ${escapeHtml(record.phone || "No phone")}</div>
          <div class="lead-submeta">
            <span class="pill">${escapeHtml(labelize(record.pitch_status || "new"))}</span>
            <span class="pill">${escapeHtml(labelize(record.call_outcome || "not_called"))}</span>
          </div>
          <div class="lead-submeta">
            <span>${escapeHtml(followUp)}</span>
          </div>
        </button>
      `
    })
    .join("")

  elements.leadList.querySelectorAll("[data-record-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedId = button.dataset.recordId
      renderLeadList()
      renderDetail()
    })
  })
}

function populateSelect(selectId, values, currentValue) {
  const select = document.querySelector(`#${selectId}`)
  const options = values.includes(currentValue) || !currentValue ? values : [currentValue, ...values]
  select.innerHTML = options
    .map(
      (value) =>
        `<option value="${escapeHtml(value)}" ${value === currentValue ? "selected" : ""}>${escapeHtml(labelize(value))}</option>`,
    )
    .join("")
}

function setLinkState(link, href, label) {
  link.href = href || "#"
  link.classList.toggle("hidden", !href)
  if (label) {
    link.textContent = label
  }
}

function detailUpdatedText(record) {
  return record.updated_at ? `Last updated ${formatDateTime(record.updated_at)}` : ""
}

function renderDetail() {
  const record = selectedRecord()
  if (!record) {
    elements.emptyState.classList.remove("hidden")
    elements.detailPane.classList.add("hidden")
    return
  }

  elements.emptyState.classList.add("hidden")
  elements.detailPane.classList.remove("hidden")

  elements.detailTrade.textContent = labelize(record.trade)
  elements.detailName.textContent = record.business_name
  elements.detailLocation.textContent = [record.city, record.state].filter(Boolean).join(", ")
  elements.verificationStatus.textContent = labelize(record.website_verification_status)
  elements.verificationNotes.textContent = record.website_verification_notes || "No qualification note available."
  elements.detailPhone.textContent = record.phone || "No phone on file"
  elements.detailCategory.textContent = record.category || "No category"
  elements.detailSourceQuery.textContent = record.source_query || "No source query"
  elements.detailUpdatedAt.textContent = detailUpdatedText(record)

  setLinkState(elements.callLink, record.phone ? `tel:${record.phone.replace(/\D+/g, "")}` : "", "Call")
  setLinkState(elements.siteLink, record.generated_site_url || "", "Generated Site")
  setLinkState(elements.mapsLink, record.google_maps_url || "", "Google Maps")

  populateSelect("pitchStatus", state.options.pitch_statuses, record.pitch_status || "new")
  populateSelect("callOutcome", state.options.call_outcomes, record.call_outcome || "not_called")

  document.querySelector("#lastCalledOn").value = record.last_called_on || ""
  document.querySelector("#nextFollowUpOn").value = record.next_follow_up_on || ""
  document.querySelector("#ownerName").value = record.owner_name || ""
  document.querySelector("#ownerEmail").value = record.owner_email || ""
  document.querySelector("#quotedPrice").value = record.quoted_price || ""
  document.querySelector("#saleAmount").value = record.sale_amount || ""
  document.querySelector("#saleDate").value = record.sale_date || ""
  document.querySelector("#callSummary").value = record.call_summary || ""
  document.querySelector("#notes").value = record.notes || ""
}

function applyPayload(payload, preserveSelection = true) {
  const currentSelection = preserveSelection ? state.selectedId : null
  state.records = payload.records || []
  state.stats = payload.stats || computeStats(state.records)
  state.options = payload.options || state.options
  state.publishedUpdatedAt = payload.updated_at || ""
  state.sourceFile = payload.source_file || ""

  if (currentSelection && state.records.some((record) => record.record_id === currentSelection)) {
    state.selectedId = currentSelection
  } else {
    state.selectedId = state.records[0]?.record_id || null
  }

  setModeUi()
  renderFilters()
  renderStats()
  renderLeadList()
  renderDetail()
}

async function loadApiRecords(preserveSelection = true) {
  state.apiConfig = await fetchApiJson("/api/config")
  const payload = await fetchApiJson("/api/records")
  state.mode = "api"
  applyPayload(payload, preserveSelection)
}

async function loadStaticRecords(preserveSelection = true) {
  const snapshot = await fetchJson(staticDataUrl(), { cache: "no-store" })
  const snapshotRecords = Array.isArray(snapshot) ? snapshot : snapshot.records || []
  const payload = {
    records: snapshotRecords,
    stats: computeStats(snapshotRecords),
    options: {
      pitch_statuses: PITCH_STATUS_OPTIONS,
      call_outcomes: CALL_OUTCOME_OPTIONS,
      editable_fields: CRM_EDITABLE_FIELDS,
    },
    updated_at: Array.isArray(snapshot) ? "" : snapshot.updated_at || "",
    source_file: Array.isArray(snapshot) ? "" : snapshot.source_file || "",
  }
  state.mode = "static"
  applyPayload(payload, preserveSelection)
}

async function loadRecords(preserveSelection = true) {
  if (activeApiBase()) {
    try {
      await loadApiRecords(preserveSelection)
      setConnectionMessage("Connected to the live CRM API.", "success")
      return
    } catch (error) {
      console.warn("Falling back to public CRM snapshot.", error)
      setConnectionMessage("Could not connect to the live CRM API. Showing the public snapshot instead.", "error")
    }
  }

  await loadStaticRecords(preserveSelection)
  if (!activeApiBase()) {
    setConnectionMessage("Connect a live CRM API to save notes and deal updates centrally.", "")
  }
  setConnectionPanel(state.connectionPanelOpen || !activeApiBase())
}

function readFormUpdates() {
  const updates = {}
  for (const field of formFields) {
    const element = elements.recordForm.querySelector(`[name="${field}"]`)
    updates[field] = element.value
  }
  return updates
}

async function saveRecord(event) {
  event.preventDefault()
  const record = selectedRecord()
  if (!record) {
    return
  }

  if (!hasWritableApi()) {
    setSaveMessage("Connect the live CRM API to save changes centrally.", "error")
    setConnectionPanel(true)
    return
  }

  elements.saveButton.disabled = true
  setSaveMessage("Saving...", "")
  try {
    await fetchApiJson(`/api/records/${encodeURIComponent(record.record_id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(readFormUpdates()),
    })
    await loadRecords(true)
    setSaveMessage("Saved to the shared CRM.", "success")
  } catch (error) {
    setSaveMessage("Could not save the record.", "error")
  } finally {
    elements.saveButton.disabled = state.mode !== "api"
  }
}

async function syncRecords() {
  elements.syncButton.disabled = true
  setSaveMessage(state.mode === "api" ? "Syncing leads from the pipeline..." : "Refreshing the public snapshot...", "")
  try {
    if (state.mode === "api") {
      const payload = await fetchApiJson("/api/sync", { method: "POST" })
      state.mode = "api"
      applyPayload(payload, false)
      setSaveMessage("Lead sync complete.", "success")
    } else {
      await loadStaticRecords(true)
      setSaveMessage("Public snapshot refreshed.", "success")
    }
  } catch (error) {
    setSaveMessage(state.mode === "api" ? "Lead sync failed." : "Snapshot refresh failed.", "error")
  } finally {
    elements.syncButton.disabled = false
  }
}

function csvEscape(value) {
  const text = String(value ?? "")
  if (/[",\n]/.test(text)) {
    return `"${text.replaceAll('"', '""')}"`
  }
  return text
}

function buildCsv(records) {
  const rows = [CRM_CSV_FIELDS.join(",")]
  for (const record of sortRecords(records.filter((item) => item.active !== false))) {
    rows.push(CRM_CSV_FIELDS.map((field) => csvEscape(record[field])).join(","))
  }
  return rows.join("\r\n")
}

function downloadBlob(filename, body, contentType) {
  const blob = new Blob([body], { type: contentType })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

function exportCsv() {
  const stamp = new Date().toISOString().slice(0, 10)
  downloadBlob(`crm-records-${stamp}.csv`, buildCsv(state.records), "text/csv;charset=utf-8")
  setSaveMessage("CSV exported.", "success")
}

async function saveConnectionSettings() {
  const nextConnection = {
    baseUrl: normalizeApiBase(elements.apiBaseInput.value),
    token: elements.apiTokenInput.value.trim(),
  }

  if (!nextConnection.baseUrl) {
    clearSavedConnection()
    await loadRecords(false)
    setConnectionMessage("Cleared the saved CRM API connection.", "success")
    return
  }

  saveConnection(nextConnection)
  setConnectionMessage("Testing the CRM API connection...", "")
  try {
    await loadApiRecords(false)
    setConnectionMessage("Connected to the live CRM API.", "success")
    setConnectionPanel(false)
    setSaveMessage("You are connected to the shared CRM now.", "success")
  } catch (error) {
    state.mode = "loading"
    setConnectionMessage("Could not connect to that CRM API. Check the URL, token, and CORS settings.", "error")
    await loadStaticRecords(false)
    setConnectionPanel(true)
  }
}

async function clearConnectionSettings() {
  clearSavedConnection()
  elements.apiTokenInput.value = ""
  setConnectionMessage("Cleared the saved CRM API connection.", "success")
  await loadRecords(false)
}

function bindEvents() {
  elements.searchInput.addEventListener("input", (event) => {
    state.filters.search = event.target.value
    renderLeadList()
    renderDetail()
  })

  elements.pitchFilter.addEventListener("change", (event) => {
    state.filters.pitchStatus = event.target.value
    renderLeadList()
    renderDetail()
  })

  elements.outcomeFilter.addEventListener("change", (event) => {
    state.filters.callOutcome = event.target.value
    renderLeadList()
    renderDetail()
  })

  elements.showArchived.addEventListener("change", (event) => {
    state.filters.showArchived = event.target.checked
    renderLeadList()
    renderDetail()
  })

  elements.recordForm.addEventListener("submit", saveRecord)
  elements.syncButton.addEventListener("click", syncRecords)
  elements.exportCsvButton.addEventListener("click", exportCsv)
  elements.connectionToggleButton.addEventListener("click", () => setConnectionPanel(!state.connectionPanelOpen))
  elements.saveConnectionButton.addEventListener("click", saveConnectionSettings)
  elements.clearConnectionButton.addEventListener("click", clearConnectionSettings)

  window.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
      event.preventDefault()
      elements.recordForm.requestSubmit()
    }
  })
}

function bootstrapConnection() {
  const urlParams = new URLSearchParams(window.location.search)
  const queryApiBase = normalizeApiBase(urlParams.get("api") || "")
  const savedConnection = loadSavedConnection()
  if (queryApiBase) {
    state.connection = {
      baseUrl: queryApiBase,
      token: savedConnection.token,
    }
    return
  }
  state.connection = savedConnection
}

bindEvents()
bootstrapConnection()
loadRecords().catch((error) => {
  console.error(error)
  setSaveMessage("Could not load CRM records.", "error")
})
