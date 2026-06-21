(function () {
  "use strict";

  const screen = document.querySelector(".capture-screen");
  const preview = document.getElementById("preview");
  const processedCanvas = document.getElementById("processedCanvas");
  const processedCtx = processedCanvas.getContext("2d", { willReadFrequently: true });
  const snapshotCanvas = document.getElementById("snapshotCanvas");
  const snapshotCtx = snapshotCanvas.getContext("2d");
  const permissionOverlay = document.getElementById("permissionOverlay");
  const toast = document.getElementById("toast");
  const filterCarousel = document.getElementById("filterCarousel");
  const parameterPanel = document.getElementById("parameterPanel");
  const debugPanel = document.getElementById("debugPanel");
  const modeTitle = document.getElementById("modeTitle");
  const moreSheet = document.getElementById("moreSheet");
  const download = document.getElementById("download");

  const startCamBtn = document.getElementById("startCam");
  const flipCamBtn = document.getElementById("flipCam");
  const recordBtn = document.getElementById("record");
  const recordScreenBtn = document.getElementById("recordScreen");
  const stopBtn = document.getElementById("stop");

  let stream = null;
  let recorder = null;
  let chunks = [];
  let facingMode = "user";
  let activeFilterId = "cartoon";
  let activeParams = {};
  let canvasFilterLoop = null;
  let lastCaptureBlob = null;
  let lastRecordingBlob = null;
  let toastTimer = null;
  let teamSocket = null;
  const timeline = [];

  const carouselFilters = [
    { id: "cartoon", label: "Cartoon", pluginId: "real-cartoon", colors: ["#22d3ee", "#facc15"] },
    { id: "anime", label: "Anime", pluginId: "anime-cartoon", colors: ["#a78bfa", "#fb7185"] },
    { id: "sparkle", label: "Sparkle", pluginId: "color", params: { saturation: 2.4, hue: 22 }, colors: ["#f9a8d4", "#fef08a"] },
    { id: "comic", label: "Comic", pluginId: "edge-detection", params: { strength: 1.35, threshold: 22, invert: 1 }, colors: ["#111827", "#f97316"] },
    { id: "glow", label: "Glow", pluginId: "color", params: { saturation: 2.7, hue: -32 }, colors: ["#67e8f9", "#c084fc"] },
    { id: "monster", label: "Monster", pluginId: "glitch", colors: ["#4ade80", "#7c3aed"] },
    { id: "dream", label: "Dream", pluginId: "dream", colors: ["#38bdf8", "#f0abfc"] },
    { id: "baller", label: "Baller", pluginId: "cinema", params: { levels: 5, saturation: 1.85, contrast: 1.32 }, colors: ["#facc15", "#fb7185"] }
  ];

  function registry() {
    return window.MeTuberFilterRegistry;
  }

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 2300);
  }

  function logDebug(message, data) {
    if (!debugPanel) return;
    const line = `[${new Date().toISOString()}] ${message}` + (data ? `\n${JSON.stringify(data, null, 2)}` : "");
    debugPanel.textContent = `${line}\n\n${debugPanel.textContent || ""}`;
  }

  function setPermissionVisible(visible) {
    permissionOverlay.classList.toggle("is-hidden", !visible);
  }

  function setMoreSheet(open) {
    moreSheet.classList.toggle("is-open", open);
    moreSheet.setAttribute("aria-hidden", open ? "false" : "true");
  }

  function isCameraReady() {
    return Boolean(stream && stream.getVideoTracks().some(track => track.readyState === "live"));
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      stream = null;
    }

    stopCanvasFilter();
    preview.srcObject = null;
    startCamBtn.textContent = "Start Camera";
    setPermissionVisible(true);
    showToast("Camera stopped.");
  }

  async function startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setPermissionVisible(true);
      showToast("Camera is not supported in this browser.");
      logDebug("CAMERA_UNSUPPORTED", { userAgent: navigator.userAgent });
      return;
    }

    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode,
          width: { ideal: 1080 },
          height: { ideal: 1920 }
        },
        audio: true
      });

      preview.srcObject = stream;
      await preview.play().catch(() => {});
      startCamBtn.textContent = "Stop Camera";
      setPermissionVisible(false);
      applyActiveFilter();
      showToast("Camera ready.");
      logDebug("CAMERA_READY", { facingMode });
    } catch (err) {
      setPermissionVisible(true);
      showToast("Enable camera access to capture.");
      logDebug("CAMERA_ERROR", { error: err.message, facingMode });
    }
  }

  async function flipCamera() {
    facingMode = facingMode === "user" ? "environment" : "user";
    showToast(facingMode === "user" ? "Front camera." : "Back camera.");
    await startCamera();
  }

  function stopCanvasFilter() {
    if (canvasFilterLoop) cancelAnimationFrame(canvasFilterLoop);
    canvasFilterLoop = null;
    processedCanvas.classList.remove("is-visible");
    preview.style.opacity = "1";
    preview.style.pointerEvents = "";
  }

  function getActiveCarouselFilter() {
    return carouselFilters.find(filter => filter.id === activeFilterId) || carouselFilters[0];
  }

  function pluginDefaults(plugin) {
    const defaults = {};
    Object.entries(plugin?.parameters || {}).forEach(([key, spec]) => {
      defaults[key] = spec.default;
    });
    return defaults;
  }

  function renderFilterCarousel() {
    filterCarousel.innerHTML = "";

    carouselFilters.forEach(filter => {
      const button = document.createElement("button");
      button.className = "filter-chip";
      button.type = "button";
      button.dataset.filter = filter.id;
      button.setAttribute("aria-label", `${filter.label} filter`);
      button.style.setProperty("--a", filter.colors[0]);
      button.style.setProperty("--b", filter.colors[1]);

      const thumb = document.createElement("span");
      thumb.className = "filter-thumb";
      thumb.setAttribute("aria-hidden", "true");

      const label = document.createElement("strong");
      label.textContent = filter.label;

      button.appendChild(thumb);
      button.appendChild(label);
      button.addEventListener("click", () => {
        activeFilterId = filter.id;
        applyActiveFilter();
        renderFilterCarouselState();
      });

      filterCarousel.appendChild(button);
    });

    renderFilterCarouselState();
  }

  function renderFilterCarouselState() {
    filterCarousel.querySelectorAll(".filter-chip").forEach(button => {
      const isActive = button.dataset.filter === activeFilterId;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
  }

  function renderParameterPanel(plugin) {
    parameterPanel.innerHTML = "";

    Object.entries(plugin?.parameters || {}).forEach(([key, spec]) => {
      const label = document.createElement("label");
      const title = document.createElement("span");
      const input = document.createElement("input");
      const value = document.createElement("span");

      title.textContent = spec.label || key;
      input.type = spec.type === "range" ? "range" : "text";
      input.min = spec.min ?? "";
      input.max = spec.max ?? "";
      input.step = spec.step ?? "";
      input.value = activeParams[key] ?? spec.default ?? "";
      value.className = "parameter-value";
      value.textContent = input.value;

      input.addEventListener("input", () => {
        activeParams[key] = input.type === "range" ? Number(input.value) : input.value;
        value.textContent = input.value;
        applyFilterToPreview(plugin);
      });

      label.appendChild(title);
      label.appendChild(input);
      label.appendChild(value);
      parameterPanel.appendChild(label);
    });
  }

  function applyActiveFilter() {
    const selected = getActiveCarouselFilter();
    const plugin = registry()?.get(selected.pluginId);

    if (!plugin) {
      stopCanvasFilter();
      preview.style.filter = "none";
      modeTitle.textContent = `MeTuber ${selected.label} Mode`;
      showToast(`${selected.label} filter unavailable.`);
      logDebug("FILTER_MISSING", selected);
      return;
    }

    activeParams = { ...pluginDefaults(plugin), ...(selected.params || {}) };
    renderParameterPanel(plugin);
    modeTitle.textContent = `MeTuber ${selected.label} Mode`;
    applyFilterToPreview(plugin);
    showToast(`${selected.label} filter selected.`);
  }

  function applyFilterToPreview(plugin) {
    try {
      if (plugin.canvasFilter) {
        preview.style.filter = "none";
        startCanvasFilter(plugin);
        logDebug("CANVAS_FILTER_APPLIED", { filter: plugin.id, params: activeParams });
        return;
      }

      stopCanvasFilter();
      preview.style.filter = registry().getFilter(plugin.id, activeParams);
      logDebug("FILTER_APPLIED", { filter: plugin.id, params: activeParams, cssFilter: preview.style.filter });
    } catch (err) {
      stopCanvasFilter();
      preview.style.filter = "none";
      showToast("Filter could not be applied.");
      logDebug("FILTER_ERROR", { filter: plugin?.id, error: err.message });
    }
  }

  function startCanvasFilter(plugin) {
    if (canvasFilterLoop) cancelAnimationFrame(canvasFilterLoop);

    preview.style.opacity = "0.01";
    preview.style.pointerEvents = "none";
    processedCanvas.classList.add("is-visible");

    const draw = () => {
      if (!preview.videoWidth || !preview.videoHeight) {
        canvasFilterLoop = requestAnimationFrame(draw);
        return;
      }

      if (processedCanvas.width !== preview.videoWidth || processedCanvas.height !== preview.videoHeight) {
        processedCanvas.width = preview.videoWidth;
        processedCanvas.height = preview.videoHeight;
      }

      try {
        processedCtx.drawImage(preview, 0, 0, processedCanvas.width, processedCanvas.height);
        let imageData = processedCtx.getImageData(0, 0, processedCanvas.width, processedCanvas.height);

        if (window.MeTuberPreprocess?.apply) {
          imageData = window.MeTuberPreprocess.apply(imageData);
        }

        const filterFn = window.MeTuberCanvasFilters?.[plugin.canvasFilter];
        if (typeof filterFn === "function") {
          imageData = filterFn(imageData, activeParams);
        }

        if (window.MeTuberAI?.processFrame) {
          const aiImageData = window.MeTuberAI.processFrame(imageData, {
            filterId: activeFilterId,
            pluginId: plugin.id,
            params: activeParams
          });
          if (aiImageData && aiImageData.data) imageData = aiImageData;
        }

        processedCtx.putImageData(imageData, 0, 0);
      } catch (err) {
        logDebug("CANVAS_FILTER_FRAME_ERROR", { filter: plugin.id, error: err.message });
      }

      canvasFilterLoop = requestAnimationFrame(draw);
    };

    draw();
  }

  function drawCurrentFrameToSnapshot() {
    const source = processedCanvas.classList.contains("is-visible") ? processedCanvas : preview;
    const width = source.videoWidth || source.width || preview.videoWidth || 1080;
    const height = source.videoHeight || source.height || preview.videoHeight || 1920;

    snapshotCanvas.width = width;
    snapshotCanvas.height = height;
    snapshotCtx.drawImage(source, 0, 0, width, height);
  }

  function capturePhoto() {
    if (!isCameraReady() && !processedCanvas.classList.contains("is-visible")) {
      showToast("Start the camera before capturing.");
      setPermissionVisible(true);
      return;
    }

    try {
      drawCurrentFrameToSnapshot();
      snapshotCanvas.toBlob(blob => {
        if (!blob) {
          showToast("Capture failed.");
          return;
        }
        lastCaptureBlob = blob;
        screen.classList.add("camera-flash");
        setTimeout(() => screen.classList.remove("camera-flash"), 340);
        showToast("Cartoon snap captured.");
        logDebug("PHOTO_CAPTURED", { size: blob.size, type: blob.type, filter: activeFilterId });
      }, "image/png");
    } catch (err) {
      showToast("Capture failed.");
      logDebug("PHOTO_CAPTURE_ERROR", { error: err.message });
    }
  }

  function saveLatestCapture() {
    const blob = lastCaptureBlob || lastRecordingBlob;
    if (!blob) {
      capturePhoto();
      setTimeout(saveLatestCapture, 180);
      return;
    }

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = blob.type.includes("png") ? "metuber-cartoon-snap.png" : "metuber-recording.webm";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    showToast("Saved to downloads.");
  }

  async function postLatestCapture() {
    const blob = lastCaptureBlob || lastRecordingBlob;
    if (!blob) {
      showToast("Capture something first.");
      return;
    }

    try {
      const ext = blob.type.includes("png") ? "png" : "webm";
      const result = await uploadBlob(blob, ext);
      showToast(result?.ok === false ? "Post failed." : "Sent to MeTuber.");
      logDebug("POST_CAPTURE_RESULT", result);

      if (teamSocket && teamSocket.readyState === WebSocket.OPEN) {
        teamSocket.send(JSON.stringify({ type: "clip-uploaded", clip: result }));
      }
    } catch (err) {
      showToast("Post endpoint unavailable.");
      logDebug("POST_CAPTURE_ERROR", { error: err.message });
    }
  }

  function getRecordingMimeType() {
    const types = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"];
    return types.find(type => window.MediaRecorder?.isTypeSupported(type)) || "";
  }

  async function startRecordingFromStream(sourceStream, label = "camera") {
    if (!window.MediaRecorder) {
      showToast("Recording is not supported here.");
      logDebug("RECORD_UNSUPPORTED", { userAgent: navigator.userAgent });
      return;
    }

    chunks = [];
    const activeCarouselFilter = getActiveCarouselFilter();
    const plugin = registry()?.get(activeCarouselFilter.pluginId);
    const shouldRecordCanvas = plugin?.canvasFilter && processedCanvas.captureStream;
    const recordStream = shouldRecordCanvas ? processedCanvas.captureStream(30) : sourceStream;

    if (shouldRecordCanvas && sourceStream) {
      sourceStream.getAudioTracks().forEach(track => recordStream.addTrack(track));
    }

    const mimeType = getRecordingMimeType();
    recorder = new MediaRecorder(recordStream, mimeType ? { mimeType } : undefined);

    recorder.ondataavailable = event => {
      if (event.data.size) chunks.push(event.data);
    };

    recorder.onstop = () => {
      lastRecordingBlob = new Blob(chunks, { type: "video/webm" });
      download.href = URL.createObjectURL(lastRecordingBlob);
      download.classList.add("is-visible");
      recordBtn.disabled = false;
      recordScreenBtn.disabled = false;
      stopBtn.disabled = true;
      stopBtn.classList.add("muted");
      showToast("Recording ready.");
      logDebug("RECORDING_READY", { size: lastRecordingBlob.size, label });
    };

    recorder.start();
    recordBtn.disabled = true;
    recordScreenBtn.disabled = true;
    stopBtn.disabled = false;
    stopBtn.classList.remove("muted");
    showToast(`Recording ${label}...`);
  }

  async function startCameraRecording() {
    if (!stream) await startCamera();
    if (!stream) return;
    await startRecordingFromStream(stream, "camera");
  }

  async function startScreenRecording() {
    try {
      if (!navigator.mediaDevices?.getDisplayMedia) {
        showToast("Screen recording is not supported here.");
        return;
      }

      const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
      await startRecordingFromStream(screenStream, "screen");
      screenStream.getVideoTracks()[0].onended = () => {
        if (recorder && recorder.state !== "inactive") recorder.stop();
      };
    } catch (err) {
      showToast("Screen recording cancelled.");
      logDebug("SCREEN_RECORD_ERROR", { error: err.message });
    }
  }

  function stopRecording() {
    if (recorder && recorder.state !== "inactive") recorder.stop();
  }

  function bindBeautyControls() {
    const smooth = document.getElementById("beautySmooth");
    const softness = document.getElementById("beautySoftness");
    const brightness = document.getElementById("beautyBrightness");
    if (!smooth || !softness || !brightness || !window.MeTuberPreprocess) return;

    const sync = () => {
      window.MeTuberPreprocess.settings.smooth = Number(smooth.value);
      window.MeTuberPreprocess.settings.softness = Number(softness.value);
      window.MeTuberPreprocess.settings.brightness = Number(brightness.value);
      logDebug("BEAUTY_PREPROCESS_UPDATED", window.MeTuberPreprocess.settings);
    };

    smooth.addEventListener("input", sync);
    softness.addEventListener("input", sync);
    brightness.addEventListener("input", sync);
    sync();
  }

  async function uploadBlob(blob, ext = "webm") {
    const room = document.getElementById("roomName")?.value || "main-room";
    const user = document.getElementById("userName")?.value || "creator";
    const response = await fetch(`/api/upload?ext=${encodeURIComponent(ext)}&room=${encodeURIComponent(room)}&user=${encodeURIComponent(user)}`, {
      method: "POST",
      body: blob
    });
    return response.json();
  }

  async function refreshLibrary() {
    const box = document.getElementById("videoLibrary");
    if (!box) return;

    try {
      box.textContent = "Loading...";
      const response = await fetch("/api/videos");
      const data = await response.json();
      box.innerHTML = "";

      (data.videos || []).forEach(video => {
        const card = document.createElement("article");
        const title = document.createElement("strong");
        const media = document.createElement("video");
        const add = document.createElement("button");

        title.textContent = video.name;
        media.src = video.url;
        media.controls = true;
        add.className = "sheet-action";
        add.type = "button";
        add.textContent = "Add to Timeline";
        add.addEventListener("click", () => {
          timeline.push({ type: "video", name: video.name, url: video.url, start: 0, end: null });
          renderTimeline();
          document.getElementById("editorPreview").src = video.url;
        });

        card.appendChild(title);
        card.appendChild(media);
        card.appendChild(add);
        box.appendChild(card);
      });
    } catch (err) {
      box.textContent = "Media library endpoint unavailable.";
      logDebug("LIBRARY_REFRESH_ERROR", { error: err.message });
    }
  }

  function renderTimeline() {
    const box = document.getElementById("timeline");
    if (!box) return;
    box.innerHTML = "";

    timeline.forEach((clip, index) => {
      const row = document.createElement("div");
      row.textContent = `${index + 1}. ${clip.name}`;
      box.appendChild(row);
    });
  }

  function bindTeamAndEditorControls() {
    document.getElementById("uploadVideo").addEventListener("change", async event => {
      const file = event.target.files[0];
      if (!file) return;
      const ext = file.name.split(".").pop() || "webm";
      try {
        const result = await uploadBlob(file, ext);
        logDebug("UPLOAD_RESULT", result);
        await refreshLibrary();
      } catch (err) {
        showToast("Upload endpoint unavailable.");
        logDebug("UPLOAD_ERROR", { error: err.message });
      }
    });

    document.getElementById("refreshLibrary").addEventListener("click", refreshLibrary);

    document.getElementById("saveProject").addEventListener("click", async () => {
      try {
        const response = await fetch("/api/project", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            name: "MeTuber Project",
            createdAt: new Date().toISOString(),
            timeline
          })
        });
        const data = await response.json();
        showToast(data.ok ? "Project saved." : "Project save failed.");
        logDebug("PROJECT_SAVED", data);
      } catch (err) {
        showToast("Project endpoint unavailable.");
        logDebug("PROJECT_SAVE_ERROR", { error: err.message });
      }
    });

    document.getElementById("joinRoom").addEventListener("click", () => {
      const room = document.getElementById("roomName").value || "main-room";
      const user = document.getElementById("userName").value || "creator";
      const proto = location.protocol === "https:" ? "wss:" : "ws:";
      teamSocket = new WebSocket(`${proto}//${location.host}`);

      teamSocket.onopen = () => teamSocket.send(JSON.stringify({ type: "join", room, user }));
      teamSocket.onmessage = event => {
        const feed = document.getElementById("roomFeed");
        feed.textContent = `${event.data}\n${feed.textContent}`;
      };
      teamSocket.onerror = () => showToast("Team socket unavailable.");
    });
  }

  function bindControls() {
    document.getElementById("enableCamera").addEventListener("click", startCamera);
    document.getElementById("useDemoPreview").addEventListener("click", () => {
      setPermissionVisible(false);
      showToast("Demo preview active.");
    });

    startCamBtn.addEventListener("click", () => {
      if (isCameraReady()) stopCamera();
      else startCamera();
    });
    flipCamBtn.addEventListener("click", flipCamera);
    recordBtn.addEventListener("click", startCameraRecording);
    recordScreenBtn.addEventListener("click", startScreenRecording);
    stopBtn.addEventListener("click", stopRecording);

    document.getElementById("captureButton").addEventListener("click", capturePhoto);
    document.getElementById("saveCapture").addEventListener("click", saveLatestCapture);
    document.getElementById("postCapture").addEventListener("click", postLatestCapture);
    document.getElementById("closeCapture").addEventListener("click", stopCamera);
    document.getElementById("textToolTop").addEventListener("click", () => showToast("Text tool ready."));

    document.querySelectorAll(".rail-tool").forEach(button => {
      button.addEventListener("click", () => {
        if (button.id === "moreTools") {
          setMoreSheet(true);
          return;
        }
        showToast(`${button.dataset.tool} tool selected.`);
      });
    });

    document.getElementById("closeMoreSheet").addEventListener("click", () => setMoreSheet(false));
    moreSheet.addEventListener("click", event => {
      if (event.target === moreSheet) setMoreSheet(false);
    });

    document.getElementById("toggleDebug").addEventListener("click", () => {
      const debug = screen.dataset.debug !== "true";
      screen.dataset.debug = debug ? "true" : "false";
      showToast(debug ? "Debug controls visible." : "Debug controls hidden.");
    });

    window.addEventListener("keydown", event => {
      if (event.key === "Escape") setMoreSheet(false);
      if (event.code === "Space" && !event.target.matches("input, textarea")) {
        event.preventDefault();
        capturePhoto();
      }
    });

    window.addEventListener("beforeunload", () => {
      if (stream) stream.getTracks().forEach(track => track.stop());
    });
  }

  function enableDebugFromQuery() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("debug") === "1" || params.get("debug") === "true") {
      screen.dataset.debug = "true";
    }
  }

  function boot() {
    if (!registry()) {
      showToast("Filter registry unavailable.");
      logDebug("FILTER_REGISTRY_MISSING");
      return;
    }

    const validation = registry().validate?.();
    logDebug("PLUGIN_REGISTRY_VALIDATE", validation);
    if (validation && !validation.ok) showToast("Some filters need attention.");

    enableDebugFromQuery();
    bindControls();
    bindBeautyControls();
    bindTeamAndEditorControls();
    renderFilterCarousel();
    applyActiveFilter();
    startCamera();
  }

  boot();
})();
