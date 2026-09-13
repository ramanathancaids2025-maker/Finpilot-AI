/* ==========================================================================
   FINPILOT AI - INTERACTIVE CHATBOT & MODAL MANAGER
   ========================================================================== */

const EXPENSE_CATEGORIES = [
    "Food & Dining", "Housing & Utilities", "Transportation",
    "Shopping & Electronics", "Entertainment & Leisure",
    "Healthcare & Fitness", "Subscriptions & Misc"
];

const INCOME_CATEGORIES = [
    "Income", "Salary", "Freelance / Consulting",
    "Investments & Dividends", "Bonus & Gifts", "Side Business"
];

function onTxTypeChange() {
    const typeEl = document.getElementById("tx-type");
    const catSelect = document.getElementById("tx-category");
    if (!typeEl || !catSelect) return;

    const type = typeEl.value;
    const categories = type === 'income' ? INCOME_CATEGORIES : EXPENSE_CATEGORIES;
    catSelect.innerHTML = categories.map(c => `<option value="${c}">${c}</option>`).join("");
}

function toggleChatDrawer() {
    const drawer = document.getElementById("chat-drawer");
    drawer.classList.toggle("open");
}

function sendQuickPrompt(promptText) {
    const input = document.getElementById("chat-input");
    input.value = promptText;
    sendChatMessage();
}

async function sendChatMessage() {
    const input = document.getElementById("chat-input");
    const query = input.value.trim();
    if (!query) return;

    input.value = "";
    appendUserMessage(query);

    const loadingId = appendBotLoading();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        const data = await response.json();

        removeBotLoading(loadingId);

        if (data.pipeline_steps) {
            updateAgentTelemetry(data.pipeline_steps);
        }

        appendBotMessage(data);
        loadDashboard();

    } catch (err) {
        removeBotLoading(loadingId);
        appendErrorMessage("Failed to process request. Please check server logs.");
    }
}

function appendUserMessage(text) {
    const container = document.getElementById("chat-messages");
    const msg = document.createElement("div");
    msg.className = "chat-bubble user-bubble";
    msg.innerHTML = `
        <div class="bubble-header"><span>User</span><span>Just now</span></div>
        <div class="bubble-content">${escapeHtml(text)}</div>
    `;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
}

function appendBotLoading() {
    const container = document.getElementById("chat-messages");
    const id = "loading-" + Date.now();
    const msg = document.createElement("div");
    msg.id = id;
    msg.className = "chat-bubble bot-bubble";
    msg.innerHTML = `
        <div class="bubble-header"><span class="agent-name"><i class="fa-solid fa-spinner fa-spin text-cyan"></i> Agents Working...</span></div>
        <div class="bubble-content text-muted">Running local ML models...</div>
    `;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeBotLoading(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function appendBotMessage(data) {
    const container = document.getElementById("chat-messages");
    const msg = document.createElement("div");
    msg.className = "chat-bubble bot-bubble";

    const formattedText = formatMarkdown(data.response);
    const confidencePct = Math.round(data.intent_confidence * 100);

    msg.innerHTML = `
        <div class="bubble-header">
            <span class="agent-name"><i class="fa-solid fa-robot text-cyan"></i> FinPilot Engine</span>
            <span class="badge badge-cyan">${data.intent} (${confidencePct}%)</span>
        </div>
        <div class="bubble-content">${formattedText}</div>
        <div class="text-xs text-muted" style="margin-top:0.4rem; font-family: var(--font-mono);">
            ⚡ Pipeline Latency: ${data.total_latency_ms}ms
        </div>
    `;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
}

function appendErrorMessage(errText) {
    const container = document.getElementById("chat-messages");
    const msg = document.createElement("div");
    msg.className = "chat-bubble bot-bubble";
    msg.innerHTML = `<div class="bubble-content text-rose"><i class="fa-solid fa-triangle-exclamation"></i> ${errText}</div>`;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
}

/* MODAL MANAGERS */
function openPurchaseModal() {
    document.getElementById("purchase-modal").classList.add("open");
}
function closePurchaseModal() {
    document.getElementById("purchase-modal").classList.remove("open");
}

async function runPurchaseCheck() {
    const itemName = document.getElementById("modal-item-name").value.trim() || "Item";
    const itemPrice = parseFloat(document.getElementById("modal-item-price").value) || 50000;

    const resBox = document.getElementById("modal-purchase-result");
    resBox.classList.remove("hidden");
    resBox.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-cyan"></i> Running Purchase Decision Model...`;

    try {
        const response = await fetch('/api/predict_purchase', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_name: itemName, item_price: itemPrice })
        });
        const data = await response.json();
        const p = data.purchase_analysis;

        if (data.agent_telemetry) {
            updateAgentTelemetry(data.agent_telemetry);
        }

        resBox.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                <strong>${p.item} (₹${p.price.toLocaleString('en-IN')})</strong>
                <span class="badge badge-${p.theme_color}">${p.status}</span>
            </div>
            <div class="text-sm font-bold text-main" style="margin-bottom:0.4rem;">${p.recommendation}</div>
            <div class="text-xs text-muted">
                • Post-Purchase Savings: ₹${p.impact.post_purchase_savings.toLocaleString('en-IN')}<br>
                • Recoup Duration: ${p.impact.months_to_recoup} Months<br>
                • Maximum Safe Price Ceiling: ₹${p.impact.max_safe_budget.toLocaleString('en-IN')}
            </div>
        `;
    } catch (err) {
        resBox.innerHTML = `<span class="text-rose">Error evaluating purchase.</span>`;
    }
}

function openTxModal() {
    onTxTypeChange();
    document.getElementById("tx-modal").classList.add("open");
}
function closeTxModal() {
    document.getElementById("tx-modal").classList.remove("open");
}

async function submitTransaction() {
    const type = document.getElementById("tx-type").value;
    const title = document.getElementById("tx-title").value.trim();
    const amount = parseFloat(document.getElementById("tx-amount").value);
    const category = document.getElementById("tx-category").value;
    const date = document.getElementById("tx-date").value;

    if (!title || isNaN(amount) || amount <= 0) {
        alert("Please enter a valid title and amount.");
        return;
    }

    try {
        await fetch('/api/transactions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, amount, category, date, type })
        });

        closeTxModal();
        loadDashboard();

    } catch (err) {
        alert("Error saving transaction.");
    }
}

/* HELPER FUNCTIONS */
function escapeHtml(str) {
    return str.replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[m]);
}

function formatMarkdown(str) {
    if (!str) return '';
    let html = escapeHtml(str);
    html = html.replace(/^### (.*$)/gim, '<strong>$1</strong>');
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    html = html.replace(/\n/g, '<br>');
    return html;
}

document.addEventListener("DOMContentLoaded", () => {
    onTxTypeChange();
});
