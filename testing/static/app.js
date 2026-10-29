"use strict";

const API = "/testing/api";
const view = document.getElementById("view");
const modal = document.getElementById("modal");
const backdrop = document.getElementById("modal-backdrop");

let pollTimer = null;

/* ---------------------------------- helpers ---------------------------------- */

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value !== null && value !== undefined) node.setAttribute(key, value);
  }
  for (const child of [].concat(children)) {
    if (child) node.append(child);
  }
  return node;
}

function clearView() {
  stopPolling();
  view.replaceChildren();
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function api(method, path, body) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(API + path, options);
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data && data.detail ? data.detail : `HTTP ${response.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

function fmtDate(value) {
  if (!value) return "—";
  const date = new Date(value.includes("T") ? value : value + "Z");
  return isNaN(date) ? value : date.toLocaleString();
}

function statusBadge(status) {
  return el("span", { class: `badge ${status}` }, [status]);
}

function errorBox(message) {
  return el("div", { class: "error-box" }, [String(message)]);
}

function progressBar(done, total) {
  const percent = total > 0 ? Math.round((done / total) * 100) : 0;
  return el("div", { class: "progress-outer" }, [
    el("div", { class: "progress-inner", style: `width:${percent}%` }),
  ]);
}

/* ---------------------------------- routing ---------------------------------- */

const routes = {
  manual: renderManual,
  automatic: renderAutomatic,
  browse: renderBrowse,
};

function router() {
  clearView();
  const hash = location.hash.replace(/^#\/?/, "");
  const [route, param] = hash.split("/");
  document.querySelectorAll("nav a").forEach((link) => {
    link.classList.toggle("active", link.dataset.nav === route);
  });

  if (route === "group" && param) return renderGroup(Number(param));
  if (route === "run" && param) return renderRun(Number(param));
  (routes[route] || renderManual)();
}

window.addEventListener("hashchange", router);

/* ------------------------------ modal (run detail) ---------------------------- */

function openRunDetail(runId) {
  api("GET", `/runs/${runId}`)
    .then((run) => {
      modal.replaceChildren();
      modal.append(
        el("button", { class: "close", text: "×", onclick: closeModal }),
        el("h2", { text: `Run #${run.id}` }),
        el("div", { class: "chips" }, [
          el("span", { class: "chip", text: `mode: ${run.mode}` }),
          el("span", { class: "chip", text: `length: ${run.length}s` }),
          el("span", { class: "chip", text: `email: ${run.email}` }),
          run.target_audience && el("span", { class: "chip", text: `audience: ${run.target_audience}` }),
          run.call_to_action && el("span", { class: "chip", text: `CTA: ${run.call_to_action}` }),
          el("span", { class: "chip", text: `created: ${fmtDate(run.created_at)}` }),
        ]),
        statusBadge(run.status),
      );
      if (run.error) modal.append(errorBox(`Pipeline error: ${run.error}`));
      if (run.fix_error) modal.append(errorBox(`Fixer error: ${run.fix_error}`));

      modal.append(el("h3", { text: "Original script" }));
      modal.append(el("div", { class: "script-box" }, [run.script]));

      if (run.fixed_script) {
        modal.append(el("h3", { text: "Fixed script" }));
        modal.append(el("div", { class: "script-box" }, [run.fixed_script]));
        if (run.fix_info) modal.append(el("div", { class: "info-box" }, [run.fix_info]));
        if (run.changes.length) {
          modal.append(el("h3", { text: `Changes (${run.changes.length})` }));
          modal.append(
            el("ul", { class: "changes-list" },
              run.changes.map((c) =>
                el("li", {}, [
                  el("span", { class: "range", text: `[${c.start_char}:${c.end_char}] ` }),
                  c.reason,
                ])
              )
            )
          );
        }
      }

      modal.append(el("h3", { text: "Judge verdict" }));
      modal.append(
        el("div", { class: "verdict-box" }, [run.verdict || "(no verdict — run is pending or fixer failed)"])
      );

      openModal();
    })
    .catch((error) => alert(`Failed to load run: ${error.message}`));
}

function openModal() {
  backdrop.classList.remove("hidden");
  modal.classList.remove("hidden");
}

function closeModal() {
  backdrop.classList.add("hidden");
  modal.classList.add("hidden");
  modal.replaceChildren();
}

backdrop.addEventListener("click", closeModal);

/* ---------------------------------- manual ----------------------------------- */

function renderManual() {
  const email = el("input", { type: "email", placeholder: "subscriber email (must exist)", value: localStorage.getItem("test-email") || "" });
  const mode = el("select", {}, ["watch", "sell"].map((m) => el("option", { value: m, text: m })));
  const length = el("select", {}, [30, 60, 90].map((n) => el("option", { value: String(n), text: `${n} seconds` })));
  const script = el("textarea", { class: "script-input", placeholder: "Paste the script to fix…" });
  const audience = el("input", { type: "text", placeholder: "who the video is for" });
  const cta = el("input", { type: "text", placeholder: "the call to action" });

  const audienceField = el("div", { class: "field grow hidden" }, [el("label", { text: "Target audience (sell mode)" }), audience]);
  const ctaField = el("div", { class: "field grow hidden" }, [el("label", { text: "Call to action (sell mode)" }), cta]);

  mode.addEventListener("change", () => {
    const sell = mode.value === "sell";
    audienceField.classList.toggle("hidden", !sell);
    ctaField.classList.toggle("hidden", !sell);
  });

  const result = el("div", {});
  const runBtn = el("button", { class: "primary", text: "Run test" });
  const form = el("div", { class: "panel" }, [
    el("h2", { text: "Manual test" }),
    el("div", { class: "row" }, [
      el("div", { class: "field" }, [el("label", { text: "Email" }), email]),
      el("div", { class: "field" }, [el("label", { text: "Mode" }), mode]),
      el("div", { class: "field" }, [el("label", { text: "Length" }), length]),
    ]),
    el("div", { class: "field" }, [el("label", { text: "Script" }), script]),
    el("div", { class: "row" }, [audienceField, ctaField]),
    runBtn,
  ]);

  runBtn.addEventListener("click", async () => {
    const payload = {
      email: email.value.trim(),
      mode: mode.value,
      length: Number(length.value),
      script: script.value,
    };
    if (!payload.email) return alert("Email is required.");
    if (!payload.script.trim()) return alert("Script is required.");
    if (mode.value === "sell") {
      payload.target_audience = audience.value.trim() || null;
      payload.call_to_action = cta.value.trim() || null;
      if (!payload.target_audience || !payload.call_to_action) {
        return alert("Sell mode requires target audience and call to action.");
      }
    }
    localStorage.setItem("test-email", payload.email);

    runBtn.disabled = true;
    runBtn.replaceChildren(el("span", { class: "spinner" }), "Running fix + judge…");
    result.replaceChildren();
    try {
      const data = await api("POST", "/runs", payload);
      result.replaceChildren(buildManualResult(data));
      result.scrollIntoView({ behavior: "smooth" });
    } catch (error) {
      result.replaceChildren(errorBox(error.message));
    } finally {
      runBtn.disabled = false;
      runBtn.replaceChildren("Run test");
    }
  });

  view.replaceChildren(form, result);
}

function buildManualResult(data) {
  const out = data.output;
  const parts = [
    el("div", { class: "panel" }, [
      el("h2", { text: "Result" }),
      el("h3", { text: "Fixed script" }),
      el("div", { class: "script-box" }, [out.script || "(empty)"]),
    ]),
  ];

  if (out.error) parts.push(errorBox(`Fixer error: ${out.error}`));
  if (out.info) parts.push(el("div", { class: "info-box" }, [out.info]));
  if (out.changes.length) {
    parts.push(
      el("div", { class: "panel" }, [
        el("h3", { text: `Changes (${out.changes.length})` }),
        el("ul", { class: "changes-list" },
          out.changes.map((c) =>
            el("li", {}, [el("span", { class: "range", text: `[${c.start_char}:${c.end_char}] ` }), c.reason])
          )
        ),
      ])
    );
  }

  const verdictPanel = el("div", { class: "panel" }, [
    el("h3", { text: "Judge verdict" }),
    el("div", { class: "verdict-box" }, [data.verdict || "(no verdict — fixer returned an error)"]),
  ]);

  if (data.verdict) {
    const saveBtn = el("button", { class: "primary", text: "Save to database" });
    saveBtn.addEventListener("click", async () => {
      saveBtn.disabled = true;
      try {
        const saved = await api("POST", "/runs/save", data);
        saveBtn.replaceChildren(`Saved ✓ (run #${saved.id})`);
      } catch (error) {
        alert(`Save failed: ${error.message}`);
        saveBtn.disabled = false;
      }
    });
    verdictPanel.append(saveBtn);
  }
  parts.push(verdictPanel);
  return parts;
}

/* --------------------------------- automatic --------------------------------- */

function renderAutomatic() {
  const name = el("input", { type: "text", placeholder: "e.g. hooks-v2-batch-1" });
  const email = el("input", { type: "email", placeholder: "subscriber email for every test", value: localStorage.getItem("test-email") || "" });
  const fileInput = el("input", { type: "file", accept: ".json,application/json" });
  const createBtn = el("button", { class: "primary", text: "Create group" });
  const groupPanel = el("div", {});

  const form = el("div", { class: "panel" }, [
    el("h2", { text: "Automatic test" }),
    el("p", { class: "muted small", text: "Upload a JSON file containing an array of test inputs. Each item: {mode, script, length, target_audience, call_to_action}. One email is used for the whole group." }),
    el("div", { class: "row" }, [
      el("div", { class: "field grow" }, [el("label", { text: "Group name" }), name]),
      el("div", { class: "field grow" }, [el("label", { text: "Email (whole group)" }), email]),
    ]),
    el("div", { class: "field" }, [el("label", { text: "Inputs JSON file" }), fileInput]),
    createBtn,
  ]);

  createBtn.addEventListener("click", () => {
    if (!name.value.trim()) return alert("Group name is required.");
    if (!email.value.trim()) return alert("Email is required.");
    const file = fileInput.files[0];
    if (!file) return alert("Choose a JSON file first.");
    localStorage.setItem("test-email", email.value.trim());

    const reader = new FileReader();
    reader.onload = async () => {
      let items;
      try {
        items = JSON.parse(reader.result);
      } catch (error) {
        return alert(`Invalid JSON: ${error.message}`);
      }
      if (!Array.isArray(items) || items.length === 0) return alert("The JSON must be a non-empty array.");
      createBtn.disabled = true;
      try {
        const group = await api("POST", "/groups", { name: name.value.trim(), email: email.value.trim(), items });
        groupPanel.replaceChildren(buildGroupPanel(group));
      } catch (error) {
        alert(`Failed to create group: ${error.message}`);
      } finally {
        createBtn.disabled = false;
      }
    };
    reader.onerror = () => alert("Failed to read the file.");
    reader.readAsText(file);
  });

  view.replaceChildren(form, groupPanel);
}

function buildGroupPanel(group) {
  const panel = el("div", { class: "panel" }, [
    el("h2", { text: `Group "${group.name}"` }),
    el("div", { class: "chips" }, [
      el("span", { class: "chip", text: `#${group.id}` }),
      el("span", { class: "chip", text: group.email }),
      statusBadge(group.status),
      el("span", { class: "chip", text: `${group.total_runs} tests` }),
    ]),
    progressBar(group.completed_runs + group.failed_runs, group.total_runs),
    el("p", { class: "small muted", text: `${group.completed_runs} done, ${group.failed_runs} failed, ${group.total_runs} total` }),
  ]);

  const startBtn = el("button", { class: "primary", text: "Start run" });
  const openLink = el("a", { href: `#/group/${group.id}`, text: "Open in Browse", class: "small" });
  panel.append(startBtn, " ", openLink);

  if (group.status === "done") {
    startBtn.disabled = true;
    startBtn.textContent = "Finished";
    return panel;
  }

  startBtn.addEventListener("click", async () => {
    startBtn.disabled = true;
    try {
      await api("POST", `/groups/${group.id}/start`);
      startBtn.textContent = "Running…";
      pollGroupInto(panel, group.id);
    } catch (error) {
      alert(`Failed to start: ${error.message}`);
      startBtn.disabled = false;
    }
  });

  return panel;
}

function pollGroupInto(panel, groupId) {
  stopPolling();
  pollTimer = setInterval(async () => {
    try {
      const group = await api("GET", `/groups/${groupId}`);
      panel.replaceChildren(...buildGroupPanel(group).children);
      if (group.status === "done") stopPolling();
    } catch (error) {
      stopPolling();
    }
  }, 2500);
}

/* ---------------------------------- browse ----------------------------------- */

function renderBrowse() {
  view.replaceChildren(
    el("h2", { text: "Browse results" }),
    el("div", { id: "groups-box" }),
    el("div", { id: "manual-box" }),
  );

  const groupsBox = document.getElementById("groups-box");
  groupsBox.append(el("h3", { text: "Automatic groups" }));
  api("GET", "/groups")
    .then((data) => {
      if (!data.groups.length) {
        groupsBox.append(el("p", { class: "muted", text: "No groups yet." }));
        return;
      }
      const rows = data.groups.map((g) =>
        el("tr", { onclick: () => (location.hash = `#/group/${g.id}`) }, [
          el("td", { text: `#${g.id}` }),
          el("td", { text: g.name }),
          el("td", {}, [statusBadge(g.status)]),
          el("td", { text: `${g.completed_runs}/${g.total_runs} done` }),
          el("td", { text: g.failed_runs ? `${g.failed_runs} failed` : "0 failed" }),
          el("td", { text: fmtDate(g.created_at) }),
        ])
      );
      groupsBox.append(
        el("table", {}, [
          el("thead", {}, [
            el("tr", {}, ["id", "name", "status", "progress", "failed", "created"].map((h) => el("th", { text: h }))),
          ]),
          el("tbody", {}, rows),
        ])
      );
    })
    .catch((error) => groupsBox.append(errorBox(error.message)));

  renderRunList("manual-box", "Manual runs", null);
}

function renderRunList(containerId, title, groupId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.append(el("h3", { text: title }));
  const body = el("div", {});
  container.append(body);
  let offset = 0;
  const limit = 25;
  const listPath = groupId === null ? "/runs" : `/groups/${groupId}/runs`;

  const load = async () => {
    body.replaceChildren(el("p", { class: "muted", text: "Loading…" }));
    try {
      const data = await api("GET", `${listPath}?offset=${offset}&limit=${limit}`);
      if (!data.runs.length) {
        body.replaceChildren(el("p", { class: "muted", text: "No runs here yet." }));
        return;
      }
      const rows = data.runs.map((r) =>
        el("tr", { onclick: () => openRunDetail(r.id) }, [
          el("td", { text: `#${r.id}` }),
          el("td", { text: r.mode }),
          el("td", { text: `${r.length}s` }),
          el("td", {}, [statusBadge(r.status)]),
          el("td", { text: r.has_fix_error ? "fixer error" : r.error ? "failed" : "ok" }),
          el("td", { text: fmtDate(r.created_at) }),
        ])
      );
      const table = el("table", {}, [
        el("thead", {}, [el("tr", {}, ["id", "mode", "length", "status", "note", "created"].map((h) => el("th", { text: h })))]),
        el("tbody", {}, rows),
      ]);
      const pager = el("div", { class: "pager" }, [
        el("button", { text: "‹ Prev", disabled: offset === 0, onclick: () => { offset = Math.max(0, offset - limit); load(); } }),
        el("span", { class: "small muted", text: `${offset + 1}–${Math.min(offset + limit, data.total)} of ${data.total}` }),
        el("button", { text: "Next ›", disabled: offset + limit >= data.total, onclick: () => { offset += limit; load(); } }),
      ]);
      body.replaceChildren(table, pager);
    } catch (error) {
      body.replaceChildren(errorBox(error.message));
    }
  };

  load();
}

/* ------------------------------- group detail -------------------------------- */

function renderGroup(groupId) {
  view.replaceChildren(el("div", { id: "group-view" }, [el("p", { class: "muted", text: "Loading…" })]));
  const target = document.getElementById("group-view");

  const load = async () => {
    let group;
    try {
      group = await api("GET", `/groups/${groupId}`);
    } catch (error) {
      target.replaceChildren(errorBox(error.message));
      return;
    }

    const summaryBtn = el("button", { class: "primary", text: group.summary ? "Regenerate summary" : "Generate group summary" });
    if (group.status === "done") {
      summaryBtn.addEventListener("click", async () => {
        summaryBtn.disabled = true;
        summaryBtn.replaceChildren(el("span", { class: "spinner" }), "Generating…");
        try {
          const data = await api("POST", `/groups/${groupId}/summary`);
          target.querySelector(".summary-box").replaceChildren(el("div", { class: "verdict-box" }, [data.summary]));
        } catch (error) {
          alert(`Failed to generate summary: ${error.message}`);
        } finally {
          summaryBtn.disabled = false;
          summaryBtn.replaceChildren("Regenerate summary");
        }
      });
    } else {
      summaryBtn.disabled = true;
      summaryBtn.textContent = "Generate group summary (available when finished)";
    }

    const doneCount = group.completed_runs + group.failed_runs;
    target.replaceChildren(
      el("p", {}, [el("a", { href: "#/browse", text: "‹ Back to Browse" })]),
      el("div", { class: "panel" }, [
        el("h2", { text: `Group ${group.name}` }),
        el("div", { class: "chips" }, [
          el("span", { class: "chip", text: `#${group.id}` }),
          el("span", { class: "chip", text: group.email }),
          statusBadge(group.status),
        ]),
        el("div", { class: "stats" }, [
          el("div", { class: "stat" }, [el("div", { class: "num", text: String(group.total_runs) }), el("div", { class: "lbl", text: "total" })]),
          el("div", { class: "stat" }, [el("div", { class: "num", text: String(group.completed_runs) }), el("div", { class: "lbl", text: "done" })]),
          el("div", { class: "stat" }, [el("div", { class: "num", text: String(group.failed_runs) }), el("div", { class: "lbl", text: "failed" })]),
        ]),
        progressBar(doneCount, group.total_runs),
        el("p", { class: "small muted", text: `created ${fmtDate(group.created_at)}` }),
      ]),
      el("div", { class: "panel" }, [
        el("h3", { text: "Group summary (what went wrong)" }),
        el("div", { class: "summary-box" }, [
          group.summary ? el("div", { class: "verdict-box" }, [group.summary]) : el("p", { class: "muted", text: "No summary generated yet." }),
        ]),
        summaryBtn,
      ]),
      el("div", { id: "group-runs", class: "panel" }),
    );

    renderRunList("group-runs", `Tests (${group.total_runs})`, groupId);

    if (group.status === "running" || group.status === "pending") {
      pollTimer = setInterval(load, 2500);
    }
  };

  load();
}

/* ------------------------------- single run view ------------------------------ */

function renderRun(runId) {
  openRunDetail(runId);
}

/* ----------------------------------- boot ------------------------------------ */

router();
