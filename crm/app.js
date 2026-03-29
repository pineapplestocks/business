const state = {
  records: [],
  stats: {},
  options: {
    pitch_statuses: [],
    call_outcomes: [],
  },
  selectedId: null,
  filters: {
    search: "",
    pitchStatus: "",
    callOutcome: "",
    showArchived: false,
  },
};

const elements = {
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
};

const formFields = [
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
];

function labelize(value) {
  return (value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function selectedRecord() {
  return state.records.find((record) => record.record_id === state.selectedId) || null;
}

function visibleRecords() {
  const search = state.filters.search.trim().toLowerCase();
  return state.records.filter((record) => {
    if (!state.filters.showArchived && record.active === false) {
      return false;
    }
    if (state.filters.pitchStatus && record.pitch_status !== state.filters.pitchStatus) {
      return false;
    }
    if (state.filters.callOutcome && record.call_outcome !== state.filters.callOutcome) {
      return false;
    }
    if (!search) {
      return true;
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
      .toLowerCase();
    return haystack.includes(search);
  });
}

function sortRecords(records) {
  return [...records].sort((left, right) => {
    const leftFollowUp = left.next_follow_up_on || "9999-99-99";
    const rightFollowUp = right.next_follow_up_on || "9999-99-99";
    if (left.active !== right.active) {
      return left.active === false ? 1 : -1;
    }
    if (leftFollowUp !== rightFollowUp) {
      return leftFollowUp.localeCompare(rightFollowUp);
    }
    return `${left.city} ${left.business_name}`.localeCompare(`${right.city} ${right.business_name}`);
  });
}

function renderStats() {
  const stats = state.stats || {};
  const stageCounts = stats.by_pitch_status || {};
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
  ];

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
    .join("");
}

function renderFilters() {
  const pitchOptions = ['<option value="">All stages</option>']
    .concat(
      state.options.pitch_statuses.map(
        (value) =>
          `<option value="${escapeHtml(value)}" ${value === state.filters.pitchStatus ? "selected" : ""}>${escapeHtml(labelize(value))}</option>`,
      ),
    )
    .join("");
  const outcomeOptions = ['<option value="">All outcomes</option>']
    .concat(
      state.options.call_outcomes.map(
        (value) =>
          `<option value="${escapeHtml(value)}" ${value === state.filters.callOutcome ? "selected" : ""}>${escapeHtml(labelize(value))}</option>`,
      ),
    )
    .join("");

  elements.pitchFilter.innerHTML = pitchOptions;
  elements.outcomeFilter.innerHTML = outcomeOptions;
  elements.showArchived.checked = state.filters.showArchived;
  elements.searchInput.value = state.filters.search;
}

function renderLeadList() {
  const records = sortRecords(visibleRecords());
  elements.recordCount.textContent = String(records.length);

  if (!records.length) {
    state.selectedId = null;
    elements.leadList.innerHTML = '<div class="empty-list">No leads match the current filters.</div>';
    renderDetail();
    return;
  }

  if (!records.some((record) => record.record_id === state.selectedId)) {
    state.selectedId = records[0].record_id;
  }

  elements.leadList.innerHTML = records
    .map((record) => {
      const isActive = record.record_id === state.selectedId;
      const location = [record.city, record.state].filter(Boolean).join(", ");
      const followUp = record.next_follow_up_on ? `Follow-up ${record.next_follow_up_on}` : "No follow-up date";
      const classes = ["lead-item"];
      if (isActive) classes.push("active");
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
      `;
    })
    .join("");

  elements.leadList.querySelectorAll("[data-record-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedId = button.dataset.recordId;
      renderLeadList();
      renderDetail();
    });
  });
}

function populateSelect(selectId, values, currentValue) {
  const select = document.querySelector(`#${selectId}`);
  select.innerHTML = values
    .map(
      (value) =>
        `<option value="${escapeHtml(value)}" ${value === currentValue ? "selected" : ""}>${escapeHtml(labelize(value))}</option>`,
    )
    .join("");
}

function renderDetail() {
  const record = selectedRecord();
  if (!record) {
    elements.emptyState.classList.remove("hidden");
    elements.detailPane.classList.add("hidden");
    return;
  }

  elements.emptyState.classList.add("hidden");
  elements.detailPane.classList.remove("hidden");

  elements.detailTrade.textContent = labelize(record.trade);
  elements.detailName.textContent = record.business_name;
  elements.detailLocation.textContent = [record.city, record.state].filter(Boolean).join(", ");
  elements.verificationStatus.textContent = labelize(record.website_verification_status);
  elements.verificationNotes.textContent = record.website_verification_notes || "No qualification note available.";
  elements.detailPhone.textContent = record.phone || "No phone on file";
  elements.detailCategory.textContent = record.category || "No category";
  elements.detailSourceQuery.textContent = record.source_query || "No source query";
  elements.detailUpdatedAt.textContent = record.updated_at ? `Last updated ${record.updated_at}` : "";

  elements.callLink.href = record.phone ? `tel:${record.phone.replace(/\D+/g, "")}` : "#";
  elements.siteLink.href = record.generated_site_url || "#";
  elements.siteLink.classList.toggle("hidden", !record.generated_site_url);
  elements.mapsLink.href = record.google_maps_url || "#";

  populateSelect("pitchStatus", state.options.pitch_statuses, record.pitch_status || "new");
  populateSelect("callOutcome", state.options.call_outcomes, record.call_outcome || "not_called");

  document.querySelector("#lastCalledOn").value = record.last_called_on || "";
  document.querySelector("#nextFollowUpOn").value = record.next_follow_up_on || "";
  document.querySelector("#ownerName").value = record.owner_name || "";
  document.querySelector("#ownerEmail").value = record.owner_email || "";
  document.querySelector("#quotedPrice").value = record.quoted_price || "";
  document.querySelector("#saleAmount").value = record.sale_amount || "";
  document.querySelector("#saleDate").value = record.sale_date || "";
  document.querySelector("#callSummary").value = record.call_summary || "";
  document.querySelector("#notes").value = record.notes || "";
}

function setSaveMessage(message, tone = "") {
  elements.saveMessage.textContent = message;
  elements.saveMessage.className = `save-message${tone ? ` ${tone}` : ""}`;
}

async function fetchPayload(endpoint = "/api/records", options = {}) {
  const response = await fetch(endpoint, options);
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`);
  }
  return response.json();
}

async function loadRecords(preserveSelection = true) {
  const currentSelection = preserveSelection ? state.selectedId : null;
  const payload = await fetchPayload();
  state.records = payload.records || [];
  state.stats = payload.stats || {};
  state.options = payload.options || state.options;
  if (currentSelection && state.records.some((record) => record.record_id === currentSelection)) {
    state.selectedId = currentSelection;
  } else {
    state.selectedId = state.records[0]?.record_id || null;
  }
  renderFilters();
  renderStats();
  renderLeadList();
  renderDetail();
}

async function saveRecord(event) {
  event.preventDefault();
  const record = selectedRecord();
  if (!record) {
    return;
  }

  const updates = {};
  for (const field of formFields) {
    const element = elements.recordForm.querySelector(`[name="${field}"]`);
    updates[field] = element.value;
  }

  elements.saveButton.disabled = true;
  setSaveMessage("Saving...", "");
  try {
    await fetchPayload(`/api/records/${encodeURIComponent(record.record_id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
    await loadRecords(true);
    setSaveMessage("Saved.", "success");
  } catch (error) {
    setSaveMessage("Could not save the record.", "error");
  } finally {
    elements.saveButton.disabled = false;
  }
}

async function syncRecords() {
  elements.syncButton.disabled = true;
  setSaveMessage("Syncing leads from the pipeline...", "");
  try {
    const payload = await fetchPayload("/api/sync", { method: "POST" });
    state.records = payload.records || [];
    state.stats = payload.stats || {};
    state.options = payload.options || state.options;
    state.selectedId = state.records[0]?.record_id || null;
    renderFilters();
    renderStats();
    renderLeadList();
    renderDetail();
    setSaveMessage("Lead sync complete.", "success");
  } catch (error) {
    setSaveMessage("Lead sync failed.", "error");
  } finally {
    elements.syncButton.disabled = false;
  }
}

function bindEvents() {
  elements.searchInput.addEventListener("input", (event) => {
    state.filters.search = event.target.value;
    renderLeadList();
    renderDetail();
  });

  elements.pitchFilter.addEventListener("change", (event) => {
    state.filters.pitchStatus = event.target.value;
    renderLeadList();
    renderDetail();
  });

  elements.outcomeFilter.addEventListener("change", (event) => {
    state.filters.callOutcome = event.target.value;
    renderLeadList();
    renderDetail();
  });

  elements.showArchived.addEventListener("change", (event) => {
    state.filters.showArchived = event.target.checked;
    renderLeadList();
    renderDetail();
  });

  elements.recordForm.addEventListener("submit", saveRecord);
  elements.syncButton.addEventListener("click", syncRecords);

  window.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      elements.recordForm.requestSubmit();
    }
  });
}

bindEvents();
loadRecords().catch(() => {
  setSaveMessage("Could not load CRM records.", "error");
});
