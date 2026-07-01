let currentVideoInfo = null;
let presets = { builtin: [], custom: [] };
let activePresetName = null;

const $ = (id) => document.getElementById(id);

function api() {
  return window.pywebview.api;
}

async function whenReady(fn) {
  if (window.pywebview) return fn();
  window.addEventListener("pywebviewready", fn);
}

whenReady(async () => {
  await loadPresets();
  await loadSettings();
  wireEvents();
});

function wireEvents() {
  $("fetchBtn").addEventListener("click", handleFetch);
  $("urlInput").addEventListener("keydown", (e) => { if (e.key === "Enter") handleFetch(); });
  $("downloadBtn").addEventListener("click", handleDownload);
  $("cancelBtn").addEventListener("click", () => api().cancel_download());

  $("historyBtn").addEventListener("click", () => togglePanel("historyPanel", loadHistory));
  $("settingsBtn").addEventListener("click", () => togglePanel("settingsPanel", loadSettings));
  document.querySelectorAll(".close-panel").forEach((btn) => {
    btn.addEventListener("click", () => $(btn.dataset.panel).classList.add("hidden"));
  });

  $("clearHistoryBtn").addEventListener("click", async () => {
    await api().clear_history();
    loadHistory();
  });
  $("chooseFolderBtn").addEventListener("click", async () => {
    const folder = await api().choose_folder();
    if (folder) $("folderPath").textContent = folder;
  });
  $("openFolderBtn").addEventListener("click", () => api().open_downloads_folder());

  ["videoQuality", "audioQuality", "containerFormat"].forEach((id) => {
    $(id).addEventListener("change", () => { activePresetName = null; renderPresets(); });
  });
}

function togglePanel(id, onOpen) {
  const el = $(id);
  const willOpen = el.classList.contains("hidden");
  document.querySelectorAll(".panel").forEach((p) => p.classList.add("hidden"));
  if (willOpen) {
    el.classList.remove("hidden");
    if (onOpen) onOpen();
  }
}

async function loadSettings() {
  const settings = await api().get_settings();
  $("folderPath").textContent = settings.download_dir;
}

async function loadHistory() {
  const history = await api().get_history();
  const list = $("historyList");
  list.innerHTML = "";
  if (!history.length) {
    list.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">No downloads yet.</p>';
    return;
  }
  history.forEach((h) => {
    const div = document.createElement("div");
    div.className = "history-item";
    div.innerHTML = `<p class="history-title">${escapeHtml(h.title)}</p>
      <p class="history-sub">${h.container.toUpperCase()} \u00b7 ${h.timestamp}</p>`;
    list.appendChild(div);
  });
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str || "";
  return d.innerHTML;
}

async function handleFetch() {
  const url = $("urlInput").value.trim();
  if (!url) return;
  $("fetchBtn").disabled = true;
  $("fetchBtn").innerHTML = '<i class="ti ti-loader-2"></i> Fetching...';

  const info = await api().fetch_info(url);

  $("fetchBtn").disabled = false;
  $("fetchBtn").innerHTML = '<i class="ti ti-download"></i> Fetch';

  if (info.error) {
    alert("Couldn't fetch that url: " + info.error);
    return;
  }

  currentVideoInfo = info;
  renderVideoCard(info);
  renderOptions(info);
  $("videoCard").classList.remove("hidden");
  $("optionsSection").classList.remove("hidden");
  $("progressSection").classList.add("hidden");
}

function renderVideoCard(info) {
  $("videoThumb").src = info.thumbnail || "";
  if (info.is_playlist) {
    $("videoTitle").textContent = info.title;
    $("videoSub").textContent = `Playlist \u00b7 ${info.count} videos`;
  } else {
    $("videoTitle").textContent = info.title;
    const mins = info.duration ? Math.floor(info.duration / 60) + ":" + String(info.duration % 60).padStart(2, "0") : "";
    $("videoSub").textContent = `${info.uploader || ""} \u00b7 ${mins}`;
  }
}

function renderOptions(info) {
  const vSel = $("videoQuality");
  const aSel = $("audioQuality");
  vSel.innerHTML = "";
  aSel.innerHTML = "";

  const vQualities = info.is_playlist ? ["best", "1080p", "720p", "480p"] : (info.video_qualities || ["best"]);
  const aQualities = info.is_playlist ? ["best", "320", "192", "128"] : (info.audio_qualities || ["best"]);

  vQualities.forEach((q) => vSel.appendChild(new Option(q, q)));
  aSel.appendChild(new Option("best", "best"));
  aQualities.forEach((q) => { if (q !== "best") aSel.appendChild(new Option(q + " kbps", q)); });

  activePresetName = null;
  renderPresets();
}

async function loadPresets() {
  presets = await api().get_presets();
  renderPresets();
}

function renderPresets() {
  const row = $("presetRow");
  row.innerHTML = "";
  const all = [...presets.builtin, ...presets.custom];

  all.forEach((p) => {
    const pill = document.createElement("div");
    pill.className = "preset-pill" + (p.name === activePresetName ? " active" : "");
    pill.innerHTML = `${p.builtin ? '<i class="ti ti-bolt"></i>' : ""}<span>${escapeHtml(p.name)}</span>`;
    pill.title = p.description || "";
    pill.addEventListener("click", () => applyPreset(p));
    if (!p.builtin) {
      const del = document.createElement("i");
      del.className = "ti ti-x del";
      del.addEventListener("click", async (e) => {
        e.stopPropagation();
        presets = await api().delete_preset(p.name);
        renderPresets();
      });
      pill.appendChild(del);
    }
    row.appendChild(pill);
  });

  const addPill = document.createElement("div");
  addPill.className = "preset-pill add";
  addPill.innerHTML = '<i class="ti ti-plus"></i><span>Save current as preset</span>';
  addPill.addEventListener("click", () => $("savePresetRow").classList.remove("hidden"));
  row.appendChild(addPill);
}

function applyPreset(p) {
  activePresetName = p.name;
  if ([...$("videoQuality").options].some((o) => o.value === p.video_quality)) {
    $("videoQuality").value = p.video_quality;
  }
  if ([...$("audioQuality").options].some((o) => o.value === p.audio_quality)) {
    $("audioQuality").value = p.audio_quality;
  }
  $("containerFormat").value = p.container;
  renderPresets();
}

$("confirmSavePreset")?.addEventListener("click", async () => {
  const name = $("presetNameInput").value.trim();
  if (!name) return;
  const preset = {
    name,
    video_quality: $("videoQuality").value,
    audio_quality: $("audioQuality").value,
    container: $("containerFormat").value,
    fast_mode: false,
    description: "Custom preset",
  };
  presets = await api().save_preset(preset);
  $("presetNameInput").value = "";
  $("savePresetRow").classList.add("hidden");
  activePresetName = name;
  renderPresets();
});

$("cancelSavePreset")?.addEventListener("click", () => {
  $("savePresetRow").classList.add("hidden");
});

async function handleDownload() {
  if (!currentVideoInfo) return;
  const activePreset = [...presets.builtin, ...presets.custom].find((p) => p.name === activePresetName);

  const payload = {
    url: currentVideoInfo.url,
    video_quality: $("videoQuality").value,
    audio_quality: $("audioQuality").value,
    container: $("containerFormat").value,
    fast_mode: activePreset ? !!activePreset.fast_mode : false,
    is_playlist: currentVideoInfo.is_playlist,
  };

  $("progressSection").classList.remove("hidden");
  $("progressFill").style.width = "0%";
  $("progressStatus").textContent = "Starting";
  $("progressStats").textContent = "";
  $("downloadBtn").disabled = true;

  await api().start_download(payload);
}

window.onBackendEvent = function (event, data) {
  if (event !== "progress") return;

  if (data.status === "downloading") {
    $("progressStatus").textContent = "Downloading";
    $("progressStats").textContent = `${data.percent}% \u00b7 ${data.speed}`;
    $("progressFill").style.width = data.percent + "%";
  } else if (data.status === "merging") {
    $("progressStatus").textContent = "Merging";
    $("progressFill").style.width = "99%";
  } else if (data.status === "done") {
    $("progressStatus").textContent = "Done";
    $("progressStats").textContent = data.title || "";
    $("progressFill").style.width = "100%";
    $("downloadBtn").disabled = false;
  } else if (data.status === "error") {
    $("progressStatus").textContent = "Error";
    $("progressStats").textContent = data.message || "";
    $("downloadBtn").disabled = false;
  }
};
