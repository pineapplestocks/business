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

const PUBLIC_STORE_KEY = `business-crm-public:${new URL(".", window.location.href).pathname.replace(/\/+$/, "") || "/"}`

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
  publicStore: {
    version: 1,
    updated_at: "",
    source_updated_at: "",
    overrides: {},
  },
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
  exportBackupButton: document.querySelector("#exportBackupButton"),
  importBackupButton: document.querySelector("#importBackupButton"),
  resetBrowserButton: document.querySelector("#resetBrowserButton"),
  importBackupInput: document.querySelector("#importBackupInput"),
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

function nowIso() {
  return new Date().toISOString()
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

function emptyPublicStore() {
  return {
    version: 1,
    updated_at: "",
    source_updated_at: "",
    overrides: {},
  }
}

function normalizePublicStore(store) {
  if (!store || typeof store !== "object") {
    return emptyPublicStore()
  }

  return {
    version: Number(store.version) || 1,
    updated_at: typeof store.updated_at === "string" ? store.updated_at : "",
    source_updated_at: typeof store.source_updated_at === "string" ? store.source_updated_at : "",
    overrides: store.overrides && typeof store.overrides === "object" ? store.overrides : {},
  }
}

function loadPublicStore() {
  try {
    return normalizePublicStore(JSON.parse(window.localStorage.getItem(PUBLIC_STORE_KEY) || "null"))
  } catch (error) {
    return emptyPublicStore()
  }
}

function savePublicStore(store) {
  const normalized = normalizePublicStore(store)
  normalized.updated_at = nowIso()
  window.localStorage.setItem(PUBLIC_STORE_KEY, JSON.stringify(normalized))
  state.publicStore = normalized
}

function mergePublicOverrides(records, store) {
  const overrides = normalizePublicStore(store).overrides
  return (records || []).map((record) => {
    const override = overrides[record.record_id]
    if (!override || typeof override !== "object") {
      return record
    }

    const merged = { ...record, has_local_changes: true }
    for (const field of CRM_EDITABLE_FIELDS) {
      if (field in override) {
        merged[field] = override[field]
      }
    }
    if (override.updated_at) {
      merged.updated_at = override.updated_at
    }
    return merged
  })
}

function setModeUi() {
  if (state.mode === "api") {
    elements.modeBadge.textContent = "Live API"
    elements.modeBadge.className = "mode-badge mode-api"
    elements.modeNotice.textContent = state.sourceFile
      ? `Connected to the live local CRM. Changes save immediately to the shared store. Lead source: ${state.sourceFile}`
      : "Connected to the live local CRM. Changes save immediately to the shared store."
    elements.modeNotice.classList.remove("hidden")
    elements.syncButton.textContent = "Sync Leads"
    elements.exportBackupButton.classList.add("hidden")
    elements.importBackupButton.classList.add("hidden")
    elements.resetBrowserButton.classList.add("hidden")
    return
  }

  elements.modeBadge.textContent = "Public CRM"
  elements.modeBadge.className = "mode-badge mode-static"
  elements.modeNotice.textContent = state.publishedUpdatedAt
    ? `Loaded the published CRM snapshot from ${formatDateTime(state.publishedUpdatedAt)}. Changes save in this browser on this device, so export a backup if you want to move them somewhere else.`
    : "Loaded the published CRM snapshot. Changes save in this browser on this device, so export a backup if you want to move them somewhere else."
  elements.modeNotice.classList.remove("hidden")
  elements.syncButton.textContent = "Refresh Snapshot"
  elements.exportBackupButton.classList.remove("hidden")
  elements.importBackupButton.classList.remove("hidden")
  elements.resetBrowserButton.classList.remove("hidden")
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

      const secondaryPills = [
        `<span class="pill">${escapeHtml(labelize(record.pitch_status || "new"))}</span>`,
        `<span class="pill">${escapeHtml(labelize(record.call_outcome || "not_called"))}</span>`,
      ]
      if (record.has_local_changes) {
        secondaryPills.push('<span class="pill pill-local">Browser Saved</span>')
      }

      return `
        <button class="${classes.join(" ")}" data-record-id="${escapeHtml(record.record_id)}" type="button">
          <div class="lead-name">${escapeHtml(record.business_name)}</div>
          <div class="lead-meta">${escapeHtml(location || "Location unknown")} · ${escapeHtml(record.phone || "No phone")}</div>
          <div class="lead-submeta">
            ${secondaryPills.join("")}
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
  if (record.has_local_changes) {
    return record.updated_at ? `Saved in this browser ${formatDateTime(record.updated_at)}` : "Saved in this browser"
  }
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

function setSaveMessage(message, tone = "") {
  elements.saveMessage.textContent = message
  elements.saveMessage.className = `save-message${tone ? ` ${tone}` : ""}`
}

async function fetchJson(endpoint, options = {}) {
  const response = await fetch(endpoint, options)
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`)
  }
  return response.json()
}

function staticDataUrl() {
  return new URL("../data/crm_records.json", window.location.href).toString()
}

function shouldPreferApiMode() {
  const isLocalHost = ["127.0.0.1", "localhost"].includes(window.location.hostname) || window.location.port === "8765"
  const isNestedStaticPath = window.location.pathname.includes("/crm/")
  return isLocalHost && !isNestedStaticPath
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
  const payload = await fetchJson("/api/records")
  state.mode = "api"
  applyPayload(payload, preserveSelection)
}

async function loadStaticRecords(preserveSelection = true) {
  const snapshot = await fetchJson(staticDataUrl(), { cache: "no-store" })
  state.mode = "static"
  state.publicStore = loadPublicStore()
  const snapshotRecords = Array.isArray(snapshot) ? snapshot : snapshot.records || []
  const payload = {
    records: mergePublicOverrides(snapshotRecords, state.publicStore),
    stats: computeStats(mergePublicOverrides(snapshotRecords, state.publicStore)),
    options: {
      pitch_statuses: PITCH_STATUS_OPTIONS,
      call_outcomes: CALL_OUTCOME_OPTIONS,
      editable_fields: CRM_EDITABLE_FIELDS,
    },
    updated_at: Array.isArray(snapshot) ? "" : snapshot.updated_at || "",
    source_file: Array.isArray(snapshot) ? "" : snapshot.source_file || "",
  }
  applyPayload(payload, preserveSelection)
}

async function loadRecords(preserveSelection = true) {
  if (state.mode === "api") {
    await loadApiRecords(preserveSelection)
    return
  }

  if (state.mode === "static") {
    await loadStaticRecords(preserveSelection)
    return
  }

  if (shouldPreferApiMode()) {
    try {
      await loadApiRecords(preserveSelection)
      return
    } catch (error) {
      console.warn("Falling back to static CRM mode.", error)
    }
  }

  await loadStaticRecords(preserveSelection)
}

function readFormUpdates() {
  const updates = {}
  for (const field of formFields) {
    const element = elements.recordForm.querySelector(`[name="${field}"]`)
    updates[field] = element.value
  }
  return updates
}

function saveStaticRecord(recordId, updates) {
  const store = loadPublicStore()
  const nextOverride = {
    ...(store.overrides[recordId] || {}),
    ...updates,
    updated_at: nowIso(),
  }
  store.overrides = {
    ...store.overrides,
    [recordId]: nextOverride,
  }
  store.source_updated_at = state.publishedUpdatedAt || store.source_updated_at
  savePublicStore(store)
}

async function saveRecord(event) {
  event.preventDefault()
  const record = selectedRecord()
  if (!record) {
    return
  }

  const updates = readFormUpdates()

  elements.saveButton.disabled = true
  setSaveMessage("Saving...", "")
  try {
    if (state.mode === "api") {
      await fetchJson(`/api/records/${encodeURIComponent(record.record_id)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      })
      await loadRecords(true)
      setSaveMessage("Saved.", "success")
    } else {
      saveStaticRecord(record.record_id, updates)
      await loadRecords(true)
      setSaveMessage("Saved in this browser.", "success")
    }
  } catch (error) {
    setSaveMessage("Could not save the record.", "error")
  } finally {
    elements.saveButton.disabled = false
  }
}

async function syncRecords() {
  elements.syncButton.disabled = true
  setSaveMessage(state.mode === "api" ? "Syncing leads from the pipeline..." : "Refreshing the published snapshot...", "")
  try {
    if (state.mode === "api") {
      const payload = await fetchJson("/api/sync", { method: "POST" })
      state.mode = "api"
      applyPayload(payload, false)
      setSaveMessage("Lead sync complete.", "success")
    } else {
      await loadStaticRecords(true)
      setSaveMessage("Loaded the latest published snapshot. Browser changes were kept.", "success")
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

function exportBackup() {
  const backup = {
    version: 1,
    exported_at: nowIso(),
    source_updated_at: state.publishedUpdatedAt,
    overrides: state.publicStore.overrides || {},
  }
  const stamp = new Date().toISOString().slice(0, 10)
  downloadBlob(`crm-browser-backup-${stamp}.json`, JSON.stringify(backup, null, 2), "application/json;charset=utf-8")
  setSaveMessage("Browser backup exported.", "success")
}

async function importBackup(event) {
  const file = event.target.files?.[0]
  if (!file) {
    return
  }

  try {
    const imported = JSON.parse(await file.text())
    if (!imported || typeof imported !== "object" || !imported.overrides || typeof imported.overrides !== "object") {
      throw new Error("Invalid backup payload")
    }

    const store = loadPublicStore()
    store.overrides = {
      ...store.overrides,
      ...imported.overrides,
    }
    store.source_updated_at = state.publishedUpdatedAt || store.source_updated_at
    savePublicStore(store)
    await loadStaticRecords(true)
    setSaveMessage("Browser backup imported.", "success")
  } catch (error) {
    setSaveMessage("Could not import the backup file.", "error")
  } finally {
    elements.importBackupInput.value = ""
  }
}

async function resetBrowserChanges() {
  if (!window.confirm("Reset all browser-saved CRM changes on this device?")) {
    return
  }

  window.localStorage.removeItem(PUBLIC_STORE_KEY)
  state.publicStore = emptyPublicStore()
  try {
    await loadStaticRecords(false)
    setSaveMessage("Browser changes cleared.", "success")
  } catch (error) {
    setSaveMessage("Could not reset browser changes.", "error")
  }
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
  elements.exportBackupButton.addEventListener("click", exportBackup)
  elements.importBackupButton.addEventListener("click", () => elements.importBackupInput.click())
  elements.importBackupInput.addEventListener("change", importBackup)
  elements.resetBrowserButton.addEventListener("click", resetBrowserChanges)

  window.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
      event.preventDefault()
      elements.recordForm.requestSubmit()
    }
  })
}

bindEvents()
loadRecords().catch((error) => {
  console.error(error)
  setSaveMessage("Could not load CRM records.", "error")
})
