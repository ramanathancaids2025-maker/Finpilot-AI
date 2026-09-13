/* ==========================================================================
    FINPILOT AI - MULTI-AGENT VISUAL PIPELINE FLOW MANAGER (8 STAGES)
   ========================================================================== */

const AGENT_LIST = [
    { id: "intent", name: "Intent", icon: "fa-language", desc: "NLP Matcher", num: "1" },
    { id: "analysis", name: "Financial Analysis", icon: "fa-chart-pie", desc: "SQLite Aggregator", num: "2" },
    { id: "health", name: "Health Prediction", icon: "fa-heart-pulse", desc: "Random Forest ML", num: "3" },
    { id: "budget", name: "Budget Optimization", icon: "fa-wallet", desc: "Adaptive Allocator", num: "4" },
    { id: "purchase", name: "Purchase Decision", icon: "fa-cart-shopping", desc: "Affordability ML", num: "5" },
    { id: "forecast", name: "Savings Forecast", icon: "fa-chart-line", desc: "Gradient Boosting", num: "6" },
    { id: "validation", name: "Validation", icon: "fa-shield-halved", desc: "Self-Correction AI", num: "7" },
    { id: "recommendation", name: "Recommendation", icon: "fa-lightbulb", desc: "Response Generator", num: "8" }
];

function initAgentTimeline() {
    const container = document.getElementById("agent-timeline");
    if (!container) return;

    container.innerHTML = AGENT_LIST.map(agent => `
        <div id="node-${agent.id}" class="agent-node">
            <div class="agent-node-title">
                <span class="text-muted text-xs font-mono">[${agent.num}]</span>
                <i class="fa-solid ${agent.icon} text-cyan"></i> ${agent.name}
            </div>
            <div class="agent-node-status">
                <span class="pulse-dot"></span> Ready
            </div>
            <div class="agent-node-meta">${agent.desc}</div>
        </div>
    `).join("");
}

function updateAgentTelemetry(steps) {
    if (!steps || !Array.isArray(steps)) return;

    const agentMapping = {
        "Intent Detection Agent": "intent",
        "Financial Analysis Agent": "analysis",
        "Financial Health Prediction Agent": "health",
        "Budget Optimisation Agent": "budget",
        "Purchase Decision Agent": "purchase",
        "Savings Forecast Agent": "forecast",
        "Prediction Validation Agent": "validation",
        "Recommendation Generator Agent": "recommendation"
    };

    steps.forEach((step, idx) => {
        const agentKey = agentMapping[step.agent];
        if (!agentKey) return;

        const node = document.getElementById(`node-${agentKey}`);
        if (node) {
            setTimeout(() => {
                const normalizedStatus = String(step.status || "Completed").toLowerCase();
                node.classList.remove("active-node", "error-node", "running-node");
                node.classList.add(normalizedStatus === "error" ? "error-node" : "active-node");
                if (normalizedStatus === "running") node.classList.add("running-node");
                const statusEl = node.querySelector(".agent-node-status");
                if (statusEl) {
                    const icon = normalizedStatus === "error"
                        ? "fa-circle-xmark text-rose"
                        : normalizedStatus === "running"
                            ? "fa-spinner fa-spin text-cyan"
                            : "fa-circle-check text-emerald";
                    const statusText = normalizedStatus === "completed"
                        ? `${step.latency_ms}ms`
                        : normalizedStatus;
                    statusEl.innerHTML = `<i class="fa-solid ${icon}"></i> ${statusText}`;
                }
                const metaEl = node.querySelector(".agent-node-meta");
                if (metaEl && step.details) {
                    metaEl.innerText = step.details.length > 38
                        ? `${step.details.substring(0, 38)}...`
                        : step.details;
                }
            }, idx * 100);
        }
    });
}

async function simulateAgentRun() {
    initAgentTimeline();
    const button = document.getElementById("test-pipeline-btn");
    if (button) {
        button.disabled = true;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running Pipeline';
    }

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: 'Show my financial analysis and savings forecast' })
        });
        const data = await response.json();
        if (!response.ok || !data.pipeline_steps) {
            throw new Error(data.error || 'Pipeline telemetry was not returned.');
        }
        updateAgentTelemetry(data.pipeline_steps);
    } catch (error) {
        document.querySelectorAll('.agent-node').forEach(node => {
            node.classList.remove('active-node', 'running-node');
            node.classList.add('error-node');
            const statusEl = node.querySelector('.agent-node-status');
            if (statusEl) statusEl.innerHTML = '<i class="fa-solid fa-circle-xmark text-rose"></i> Error';
        });
        console.error('Agent pipeline error:', error);
    } finally {
        if (button) {
            button.disabled = false;
            button.innerHTML = '<i class="fa-solid fa-rotate"></i> Run Real Pipeline';
        }
    }
}

document.addEventListener("DOMContentLoaded", () => {
    initAgentTimeline();
});
