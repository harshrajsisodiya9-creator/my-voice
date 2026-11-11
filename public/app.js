(() => {
  const micBtn = document.getElementById("mic-btn");
  const stopSpeechBtn = document.getElementById("stop-speech-btn");
  const statusEl = document.getElementById("status");
  const chat = document.getElementById("chat");
  const textForm = document.getElementById("text-form");
  const textInput = document.getElementById("text-input");

  const MAX_RECORD_SEC = 30;
  const MAX_HISTORY = 6;

  let history = [];
  let mediaRecorder = null;
  let audioChunks = [];
  let recording = false;
  let recordTimeout = null;
  let ttsQueue = [];
  let speaking = false;

  // --- TTS setup ---
  let voices = [];
  function loadVoices() {
    voices = speechSynthesis.getVoices();
  }
  loadVoices();
  if (speechSynthesis.onvoiceschanged !== undefined) {
    speechSynthesis.onvoiceschanged = loadVoices;
  }

  function pickVoice() {
    if (!voices.length) voices = speechSynthesis.getVoices();
    const inMale = voices.find(
      (v) => v.lang.startsWith("en") && v.lang.includes("IN") && /male/i.test(v.name) && !/female/i.test(v.name)
    );
    if (inMale) return inMale;
    const inAny = voices.find((v) => v.lang.startsWith("en") && v.lang.includes("IN"));
    if (inAny) return inAny;
    const enAny = voices.find((v) => v.lang.startsWith("en"));
    return enAny || voices[0] || null;
  }

  function splitSentences(text) {
    return text
      .split(/(?<=[.!?])\s+/)
      .map((s) => s.trim())
      .filter(Boolean);
  }

  function speakText(text) {
    if (!("speechSynthesis" in window)) return;
    speechSynthesis.cancel();
    ttsQueue = splitSentences(text);
    speaking = true;
    stopSpeechBtn.classList.remove("hidden");
    setStatus("speaking");
    speakNext();
  }

  function speakNext() {
    if (!ttsQueue.length) {
      speaking = false;
      stopSpeechBtn.classList.add("hidden");
      setStatus("ready");
      return;
    }
    const sentence = ttsQueue.shift();
    const utter = new SpeechSynthesisUtterance(sentence);
    const voice = pickVoice();
    if (voice) utter.voice = voice;
    utter.rate = 1;
    utter.pitch = 1;
    utter.onend = speakNext;
    utter.onerror = speakNext;
    speechSynthesis.speak(utter);
  }

  function stopSpeaking() {
    speechSynthesis.cancel();
    ttsQueue = [];
    speaking = false;
    stopSpeechBtn.classList.add("hidden");
    setStatus("ready");
  }

  stopSpeechBtn.addEventListener("click", stopSpeaking);

  // --- Status ---
  function setStatus(state, msg) {
    statusEl.className = "status " + state;
    const labels = { ready: "Ready", listening: "Listening...", thinking: "Thinking...", speaking: "Speaking...", error: "Error" };
    statusEl.textContent = msg || labels[state] || state;
  }

  // --- Chat ---
  function addMessage(role, text) {
    const div = document.createElement("div");
    div.className = "msg " + (role === "user" ? "user" : "bot");
    div.textContent = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
  }

  function pushHistory(role, content) {
    history.push({ role, content });
    if (history.length > MAX_HISTORY) {
      history = history.slice(-MAX_HISTORY);
    }
  }

  // --- API ---
  async function sendAudio(blob) {
    setStatus("thinking");
    const form = new FormData();
    const ext = blob.type.includes("mp4") ? ".mp4" : ".webm";
    form.append("audio", blob, "recording" + ext);
    form.append("history", JSON.stringify(history));

    try {
      const res = await fetch("/api/talk", { method: "POST", body: form });
      let data;
      try { data = await res.json(); } catch { data = {}; }
      if (!res.ok) {
        setStatus("error", data.error || "Something went wrong. Please try again.");
        return;
      }
      if (data.transcript) {
        addMessage("user", data.transcript);
        pushHistory("user", data.transcript);
      }
      addMessage("bot", data.reply);
      pushHistory("assistant", data.reply);
      speakText(data.reply);
    } catch (e) {
      setStatus("error", "Could not reach the server. Please check your connection.");
    }
  }

  async function sendText(text) {
    addMessage("user", text);
    pushHistory("user", text);
    setStatus("thinking");

    const form = new FormData();
    form.append("text", text);
    form.append("history", JSON.stringify(history));

    try {
      const res = await fetch("/api/talk", { method: "POST", body: form });
      let data;
      try { data = await res.json(); } catch { data = {}; }
      if (!res.ok) {
        setStatus("error", data.error || "Something went wrong. Please try again.");
        return;
      }
      addMessage("bot", data.reply);
      pushHistory("assistant", data.reply);
      speakText(data.reply);
    } catch (e) {
      setStatus("error", "Could not reach the server. Please check your connection.");
    }
  }

  // --- Recording ---
  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/mp4";
      mediaRecorder = new MediaRecorder(stream, { mimeType });
      audioChunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        if (audioChunks.length) {
          const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
          sendAudio(blob);
        }
      };

      mediaRecorder.start();
      recording = true;
      micBtn.classList.add("recording");
      setStatus("listening");

      recordTimeout = setTimeout(() => {
        if (recording) stopRecording();
      }, MAX_RECORD_SEC * 1000);
    } catch (err) {
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        showMicDenied();
      } else {
        setStatus("error", "Could not access microphone.");
      }
    }
  }

  function stopRecording() {
    if (mediaRecorder && recording) {
      clearTimeout(recordTimeout);
      mediaRecorder.stop();
      recording = false;
      micBtn.classList.remove("recording");
    }
  }

  micBtn.addEventListener("click", () => {
    if (speaking) stopSpeaking();
    if (recording) {
      stopRecording();
    } else {
      startRecording();
    }
  });

  // --- Text fallback ---
  textForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const val = textInput.value.trim();
    if (!val) return;
    if (speaking) stopSpeaking();
    textInput.value = "";
    sendText(val);
  });

  // --- Sample chips ---
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const q = chip.getAttribute("data-q");
      if (!q) return;
      if (speaking) stopSpeaking();
      sendText(q);
    });
  });

  // --- Mic denied ---
  function showMicDenied() {
    if (document.querySelector(".mic-denied")) return;
    const div = document.createElement("div");
    div.className = "mic-denied";
    div.textContent =
      "Microphone access was denied. You can still ask questions by typing in the text box below.";
    const container = document.querySelector(".container");
    container.insertBefore(div, chat);
  }
})();
