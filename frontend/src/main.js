// ====== Config / state ======
let token = null;
const API_BASE = "http://127.0.0.1:8000";
let messages = [];

// ====== UI helpers ======
function showLogin() {
  document.getElementById("loginSection").style.display = "block";
  document.getElementById("noAccessSection").style.display = "none";
  document.getElementById("appSection").style.display = "none";
  document.getElementById("chatSection").style.display = "none";
}

function showNoAccess() {
  document.getElementById("loginSection").style.display = "none";
  document.getElementById("noAccessSection").style.display = "block";
  document.getElementById("appSection").style.display = "none";
  document.getElementById("chatSection").style.display = "none";
}

function showApp() {
  document.getElementById("loginSection").style.display = "none";
  document.getElementById("noAccessSection").style.display = "none";
  document.getElementById("appSection").style.display = "block";
  document.getElementById("chatSection").style.display = "none";
}

function showChat() {
  document.getElementById("loginSection").style.display = "none";
  document.getElementById("noAccessSection").style.display = "none";
  document.getElementById("appSection").style.display = "none";
  document.getElementById("chatSection").style.display = "block";
}

// ====== API ======
async function api(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    ...options,
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
      ...(options.headers || {}),
    }
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw { status: res.status, data };
  return data;
}

// ====== Report rendering ======
function renderReport(report) {
  const container = document.getElementById("report");
  container.innerHTML = "";

  if (!report) {
    container.innerHTML = '<p class="muted">No report content available.</p>';
    return;
  }

  const topics = report.topics || [];
  const execSummary = report.executive_summary || [];
  const overall = report.overall_takeaway || "";

  const themesHtml = topics.map((t) => `
    <div class="accordion">
      <button class="accordion-header">
        <span>${t.topic}</span>
        <span class="arrow">▾</span>
      </button>

      <div class="accordion-body">
        <p><strong>Observation</strong><br>${t.observation}</p>
        <p><strong>Implication</strong><br>${t.implication}</p>
        <p><strong>Strategic Alignment</strong><br>
          ${t.strategic_alignment.objective} – ${t.strategic_alignment.status}
        </p>
        <p><strong>Recommendation</strong><br>${t.recommendation.action}</p>
        <p><strong>Decision Required</strong><br>${t.decision_required}</p>
      </div>
    </div>
  `).join("");

  const summaryHtml = execSummary.map(s => `
    <div class="topic-card">
      <div class="topic-section-title">Executive summary</div>
      <p class="topic-text"><strong>Objective:</strong> ${s.objective}</p>
      <p class="topic-text">
        <strong>Status:</strong>
        <span class="badge-status">
          <span class="badge-status-dot"></span>
          ${s.status}
        </span>
      </p>
      <p class="topic-text"><strong>Key decision needed:</strong> ${s.key_decision_needed}</p>
    </div>
  `).join("");

  const takeawayHtml = overall ? `
    <div class="takeaway-box">
      <div class="takeaway-icon">💡</div>
      <div>${overall}</div>
    </div>
  ` : "";

  container.innerHTML = `
    <div class="section-heading"><span>THEMES</span></div>
    ${themesHtml || '<p class="muted">No themes available.</p>'}

    <div class="section-heading" style="margin-top:18px;"><span>EXECUTIVE SUMMARY</span></div>
    ${summaryHtml || '<p class="muted">No executive summary available.</p>'}

    <div class="section-heading" style="margin-top:18px;"><span>OVERALL TAKEAWAY</span></div>
    ${takeawayHtml || '<p class="muted">No overall takeaway available.</p>'}
  `;
}

// ====== Products / report loading ======
function populateProducts(products) {
  const select = document.getElementById("products");
  select.innerHTML = "";
  products.forEach(p => {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.name;
    select.appendChild(opt);
  });
}

async function loadReport() {
  const tp = document.getElementById("products").value;
  const type = document.getElementById("reportType").value;
  const date = document.getElementById("reportDate").value;

  let url = `/reports?report_type=${type}&report_date=${date}`;
  if (type !== "aggregated") url += `&talking_product_id=${tp}`;

  const data = await api(url);
  renderReport(data.report);
}

async function loadLatestReport() {
  const tp = document.getElementById("products").value;
  const type = document.getElementById("reportType").value;

  let url = `/reports/latest?report_type=${type}`;
  if (type !== "aggregated") url += `&talking_product_id=${tp}`;

  try {
    const data = await api(url);
    document.getElementById("reportDate").value = data.date;
    renderReport(data.report);
  } catch (err) {
    console.log("loadLatestReport error:", err);

    if (err.status === 404) {
      document.getElementById("reportDate").value = "";
      document.getElementById("report").innerHTML = "<p class='muted'>No reports found for this selection.</p>";
      return;
    }

    throw err;
  }
}

// ====== Chat ======
async function sendChat() {
  const inputEl = document.getElementById("chatInput");
  const text = inputEl.value.trim();
  if (!text) return;

  inputEl.value = "";

  const tp = document.getElementById("products").value || null;

  messages.push({ role: "user", content: text });
  renderChat();

  try {
    const data = await api("/ask", {
      method: "POST",
      body: JSON.stringify({
        question: text,
        talking_product_id: tp || null
      })
    });

    messages.push({
      role: "assistant",
      content: data.answer,
      citations: data.citations || []
    });

    renderChat();
  } catch (err) {
    console.log("Error calling /ask:", err);
    messages.push({
      role: "assistant",
      content: "There was an error calling the assistant. Please try again."
    });
    renderChat();
  }
}

function renderChat() {
  const chatWindow = document.getElementById("chatWindow");
  chatWindow.innerHTML = "";

  messages.forEach(msg => {
    const div = document.createElement("div");
    div.className = "msg " + msg.role;

    const content = document.createElement("div");
    content.className = "msg-content";

    if (msg.role === "assistant") {
      const html = window.DOMPurify.sanitize(window.marked.parse(msg.content || ""));
      content.innerHTML = html;
    } else {
      content.textContent = msg.content || "";
    }

    div.appendChild(content);

    if (msg.citations && msg.citations.length) {
      const small = document.createElement("small");
      small.textContent = "Sources: " + msg.citations.map(c => c.i).join(", ");
      div.appendChild(small);
    }

    chatWindow.appendChild(div);
  });

  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ====== Tabs ======
function setActiveTab(type) {
  const tabs = document.querySelectorAll(".pill-tab");
  tabs.forEach(tab => tab.classList.toggle("active", tab.dataset.type === type));
  document.getElementById("reportType").value = type;
}

// ====== Google login callback (must be global for GSI) ======
window.onGoogleLogin = async function onGoogleLogin(response) {
  token = response.credential;

  try {
    const products = await api("/me/talking-products");
    populateProducts(products);

    document.getElementById("reportType").value = "daily";
    setActiveTab("daily");
    showApp();

    if (products.length > 0) {
      try {
        await loadLatestReport();
      } catch (err) {
        console.log("Error loading latest report on login:", err);
        document.getElementById("report").innerHTML =
          "<p class='muted'>Could not load latest report. Please pick another date or type.</p>";
      }
    }
  } catch (err) {
    console.log("Login/backend error:", err);

    if (err.status === 403 && String(err.data?.detail || "").includes("User not linked")) {
      showNoAccess();
    } else {
      alert("Unexpected login error. Check the console.");
      showLogin();
    }
  }
};

// ====== Wire listeners on load ======
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("products").addEventListener("change", () => loadLatestReport());
  document.getElementById("reportDate").addEventListener("change", () => loadReport());

  document.addEventListener("click", e => {
    if (!e.target.closest(".accordion-header")) return;
    const acc = e.target.closest(".accordion");
    acc.classList.toggle("open");
  });

  document.querySelectorAll(".pill-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      const type = tab.dataset.type;
      setActiveTab(type);
      loadLatestReport();
    });
  });

  document.getElementById("openChatBtn").addEventListener("click", () => showChat());
  document.getElementById("backToReportsBtn").addEventListener("click", () => showApp());

  document.getElementById("sendChatBtn").addEventListener("click", () => sendChat());
  document.getElementById("chatInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendChat();
    }
  });

  showLogin();
});
