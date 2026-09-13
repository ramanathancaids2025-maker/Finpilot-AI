/* ==========================================================================
   FINPILOT AI - DASHBOARD DATA & CHARTS MANAGER (RUPEES ₹ FORMAT)
   ========================================================================== */

let expenseChartInstance = null;
let forecastChartInstance = null;

/* ==========================================================================
   HEALTH GAUGE UPDATER
   ========================================================================== */
function updateHealthGauge(score, tier, risk, breakdown) {
    // Update gauge arc fill (circumference = 2π×40 ≈ 251.2)
    const circumference = 251.2;
    const offset = circumference - (score / 100) * circumference;
    const gaugeFill = document.getElementById('gauge-fill');
    if (gaugeFill) {
        gaugeFill.style.strokeDashoffset = offset;
        // Color by tier
        const color = score >= 80 ? '#10b981' : score >= 65 ? '#06b6d4' : score >= 50 ? '#f59e0b' : '#ef4444';
        gaugeFill.style.stroke = color;
    }

    const scoreEl = document.getElementById('gauge-score-val');
    if (scoreEl) scoreEl.innerText = Math.round(score);

    const badgeEl = document.getElementById('health-tier-badge');
    if (badgeEl) {
        badgeEl.innerText = tier;
        badgeEl.className = 'badge ' + (score >= 80 ? 'badge-emerald' : score >= 65 ? 'badge-cyan' : score >= 50 ? 'badge-amber' : 'badge-red');
    }

    const riskEl = document.getElementById('risk-level-val');
    if (riskEl) riskEl.innerText = risk;

    const runwayEl = document.getElementById('runway-val');
    if (runwayEl && breakdown) {
        runwayEl.innerText = `${breakdown.savings_runway_months} Months`;
    }
}

/* ==========================================================================
   EXPENSE DISTRIBUTION PIE CHART
   ========================================================================== */
function renderExpenseChart(categoryDistribution) {
    const canvas = document.getElementById('expenseChart');
    if (!canvas) return;

    const labels = Object.keys(categoryDistribution);
    const values = Object.values(categoryDistribution);

    const PALETTE = [
        '#06b6d4', '#10b981', '#f59e0b', '#8b5cf6',
        '#ef4444', '#ec4899', '#3b82f6', '#14b8a6'
    ];

    if (expenseChartInstance) expenseChartInstance.destroy();

    expenseChartInstance = new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: PALETTE.slice(0, labels.length),
                borderColor: '#0f172a',
                borderWidth: 3,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#94a3b8',
                        padding: 12,
                        font: { size: 11, family: 'Plus Jakarta Sans' },
                        boxWidth: 12
                    }
                },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ₹${parseFloat(ctx.parsed).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                    }
                }
            },
            cutout: '65%'
        }
    });
}

/* ==========================================================================
   SAVINGS FORECAST LINE CHART
   ========================================================================== */
function renderForecastChart(trajectory) {
    const canvas = document.getElementById('forecastChart');
    if (!canvas || !trajectory || !trajectory.length) return;

    const labels = trajectory.map(p => p.month);
    const values = trajectory.map(p => p.projected_savings);

    if (forecastChartInstance) forecastChartInstance.destroy();

    forecastChartInstance = new Chart(canvas, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Projected Savings (₹)',
                data: values,
                borderColor: '#8b5cf6',
                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                borderWidth: 2.5,
                pointBackgroundColor: '#8b5cf6',
                pointRadius: 4,
                pointHoverRadius: 6,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ₹${parseFloat(ctx.parsed.y).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#64748b', font: { size: 10 } },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y: {
                    ticks: {
                        color: '#64748b',
                        font: { size: 10 },
                        callback: v => `₹${(v / 100000).toFixed(1)}L`
                    },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                }
            }
        }
    });
}

/* ==========================================================================
   BUDGET OPTIMIZATION LIST
   ========================================================================== */
function renderBudgetOptimization(budgetData) {
    if (!budgetData) return;

    const strategyEl = document.getElementById('budget-strategy-lbl');
    if (strategyEl) strategyEl.innerText = budgetData.strategy || '50/30/20 Strategy';

    const savingsBadge = document.getElementById('potential-savings-badge');
    if (savingsBadge) {
        const pot = budgetData.potential_monthly_savings || 0;
        savingsBadge.innerText = `+₹${pot.toLocaleString('en-IN')}/mo Savings Potential`;
    }

    const listEl = document.getElementById('budget-items-list');
    if (!listEl) return;

    const alloc = budgetData.target_allocation || {};
    const actual = budgetData.actual_spending || {};
    const overCats = budgetData.over_budget_categories || [];

    let html = `
        <div class="budget-summary-row">
            <div class="budget-summary-pill needs">
                <span class="pill-lbl">Needs Budget</span>
                <span class="pill-amt">₹${(alloc.needs_budget || 0).toLocaleString('en-IN')}</span>
                <span class="pill-actual text-muted">Actual: ₹${(actual.needs || 0).toLocaleString('en-IN')}</span>
            </div>
            <div class="budget-summary-pill wants">
                <span class="pill-lbl">Wants Budget</span>
                <span class="pill-amt">₹${(alloc.wants_budget || 0).toLocaleString('en-IN')}</span>
                <span class="pill-actual text-muted">Actual: ₹${(actual.wants || 0).toLocaleString('en-IN')}</span>
            </div>
            <div class="budget-summary-pill savings">
                <span class="pill-lbl">Savings Target</span>
                <span class="pill-amt text-emerald">₹${(alloc.savings_target || 0).toLocaleString('en-IN')}</span>
            </div>
        </div>
    `;

    if (overCats.length > 0) {
        html += `<div class="over-budget-heading"><i class="fa-solid fa-triangle-exclamation text-amber"></i> Over-Budget Categories</div>`;
        html += overCats.map(item => `
            <div class="budget-item">
                <div class="budget-item-left">
                    <span class="budget-cat-name">${item.category}</span>
                    <span class="budget-cat-meta text-muted">Recommended limit: ₹${item.recommended_limit.toLocaleString('en-IN')}</span>
                </div>
                <div class="budget-item-right">
                    <span class="budget-over text-amber">₹${item.current_spending.toLocaleString('en-IN')}</span>
                    <span class="badge badge-emerald">Save ₹${item.potential_monthly_savings.toLocaleString('en-IN')}/mo</span>
                </div>
            </div>
        `).join('');
    } else {
        html += `<div class="budget-on-track"><i class="fa-solid fa-circle-check text-emerald"></i> All categories within recommended limits. Great work!</div>`;
    }

    listEl.innerHTML = html;
}

function renderDashboardGoals(goals) {
    const listEl = document.getElementById('dashboard-goals-list');
    if (!listEl) return;

    if (!goals || goals.length === 0) {
        listEl.innerHTML = '<span class="text-muted text-sm">No savings goals yet.</span>';
        return;
    }

    listEl.innerHTML = goals.slice(0, 3).map(goal => `
        <div class="dashboard-goal-row">
            <div class="dashboard-goal-heading">
                <strong>${escapeHtml(goal.title)}</strong>
                <span class="text-muted text-xs">${Number(goal.progress_pct).toFixed(1)}%</span>
            </div>
            <div class="progress-track">
                <div class="progress-fill fill-emerald" style="width:${Math.min(100, goal.progress_pct)}%"></div>
            </div>
            <div class="dashboard-goal-meta">
                <span>₹${Number(goal.current_amount).toLocaleString('en-IN')} saved</span>
                <span class="text-muted">₹${Number(goal.remaining_amount).toLocaleString('en-IN')} remaining</span>
            </div>
        </div>
    `).join('');
}

/* ==========================================================================
   MAIN DASHBOARD LOADER
   ========================================================================== */
async function loadDashboard() {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();

        // 1. Update Header Pills & Hero Stats
        document.getElementById("nav-savings-val").innerText = `₹${data.current_savings.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        document.getElementById("nav-health-val").innerText = `${data.health_score} / 100`;

        // 2. AI Insight Banner
        document.getElementById("ai-insight-text").innerHTML = data.ai_insight_of_the_day;

        // 3. Health Score Gauge
        updateHealthGauge(data.health_score, data.health_tier, data.risk_level, data.health_breakdown);

        // 4. Monthly Income & Surplus
        document.getElementById("income-val").innerText = `₹${data.monthly_income.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        document.getElementById("surplus-val").innerText = `₹${data.monthly_surplus.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        
        const expPct = Math.round(data.expense_ratio * 100);
        document.getElementById("exp-ratio-pct").innerText = `${expPct}%`;
        document.getElementById("exp-ratio-fill").style.width = `${Math.min(100, expPct)}%`;

        // 5. ML Savings Forecast Stats
        document.getElementById("forecast-6m-val").innerText = `₹${Math.round(data.forecast.forecast_6_months).toLocaleString('en-IN')}`;
        document.getElementById("forecast-3m-val").innerText = `₹${Math.round(data.forecast.forecast_3_months).toLocaleString('en-IN')}`;
        document.getElementById("forecast-12m-val").innerText = `₹${Math.round(data.forecast.forecast_12_months).toLocaleString('en-IN')}`;

        // 6. Top Expense Category
        document.getElementById("top-cat-val").innerText = data.top_category;
        const topAmt = data.category_distribution[data.top_category] || 0;
        document.getElementById("top-cat-amt").innerText = `₹${topAmt.toLocaleString('en-IN')}/month average`;
        document.getElementById("top-cat-savings").innerText = `₹${Math.round(topAmt * 0.15 * 12).toLocaleString('en-IN')}`;

        // 7. Render Charts
        renderExpenseChart(data.category_distribution);
        renderForecastChart(data.forecast.trajectory);

        // 8. Render Budget Optimization
        renderBudgetOptimization(data.budget_optimization);

        // 9. Render Savings Goals
        renderDashboardGoals(data.savings_goals);

        // 10. Render Recent Transactions
        renderTransactionsTable(data.recent_transactions);

    // Store raw transactions locally for instant search/filtering
    allTransactionsData = data.recent_transactions || [];
    filterTransactions();

    } catch (err) {
        console.error("Dashboard Load Error:", err);
    }
}

let allTransactionsData = [];

function filterTransactions() {
    const searchEl = document.getElementById("tx-search-input");
    const query = searchEl ? searchEl.value.toLowerCase().trim() : "";
    const typeFilter = document.getElementById("tx-filter-type")?.value || "all";

    const filtered = allTransactionsData.filter(tx => {
        const matchesType = typeFilter === "all" || tx.type === typeFilter;
        const matchesQuery = !query || 
            tx.title.toLowerCase().includes(query) || 
            tx.category.toLowerCase().includes(query) ||
            tx.date.includes(query) ||
            tx.amount.toString().includes(query);
        return matchesType && matchesQuery;
    });

    renderTransactionsTable(filtered);
}

function renderTransactionsTable(txs) {
    const tbody = document.getElementById("transactions-tbody");
    if (!tbody) return;

    if (!txs || txs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-muted text-center" style="padding: 1.5rem;">No transactions found.</td></tr>`;
        return;
    }

    const displayTxs = txs.slice(0, 5);
    tbody.innerHTML = displayTxs.map(tx => `
        <tr>
            <td class="text-muted text-xs">${tx.date}</td>
            <td><strong>${escapeHtml(tx.title)}</strong></td>
            <td><span class="badge badge-neutral">${escapeHtml(tx.category)}</span></td>
            <td>
                <span class="badge ${tx.type === 'income' ? 'badge-emerald' : 'badge-neutral'}">
                    ${tx.type === 'income' ? '📈 Incoming' : '📉 Expense'}
                </span>
            </td>
            <td class="${tx.type === 'income' ? 'text-emerald font-bold' : 'text-main'}">
                ${tx.type === 'income' ? '+' : '-'}₹${parseFloat(tx.amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}
            </td>
            <td class="actions-cell">
                <button class="action-btn edit-btn" title="Edit Transaction" onclick="openEditTxModal(${tx.id})">
                    <i class="fa-solid fa-pen-to-square"></i>
                </button>
                <button class="action-btn delete-btn" title="Delete Transaction" onclick="deleteTransaction(${tx.id})">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join("");
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
}

/* ==========================================================================
   TRANSACTION MODAL & CRUD API HANDLERS
   ========================================================================== */

const CATEGORIES_MAP = {
    expense: [
        "Housing & Utilities",
        "Food & Dining",
        "Transportation",
        "Shopping & Electronics",
        "Entertainment & Leisure",
        "Healthcare & Fitness",
        "Subscriptions & Misc"
    ],
    income: [
        "Income",
        "Freelance",
        "Investment Return",
        "Bonus & Gifts",
        "Other Credit"
    ]
};

function onTxTypeChange() {
    const type = document.getElementById("tx-type").value;
    const catSelect = document.getElementById("tx-category");
    const options = CATEGORIES_MAP[type] || CATEGORIES_MAP.expense;

    catSelect.innerHTML = options.map(c => `<option value="${c}">${c}</option>`).join("");
}

function openTxModal() {
    document.getElementById("tx-edit-id").value = "";
    document.getElementById("tx-modal-title").innerHTML = `<i class="fa-solid fa-plus-circle text-emerald"></i> Add New Transaction`;
    document.getElementById("tx-submit-btn").innerText = "Save Transaction";

    document.getElementById("tx-type").value = "expense";
    document.getElementById("tx-title").value = "";
    document.getElementById("tx-amount").value = "";
    document.getElementById("tx-date").value = new Date().toISOString().split('T')[0];

    onTxTypeChange();
    document.getElementById("tx-modal").classList.add("active");
}

function openEditTxModal(txId) {
    const tx = allTransactionsData.find(t => t.id === txId);
    if (!tx) return;

    document.getElementById("tx-edit-id").value = tx.id;
    document.getElementById("tx-modal-title").innerHTML = `<i class="fa-solid fa-pen-to-square text-cyan"></i> Edit Transaction`;
    document.getElementById("tx-submit-btn").innerText = "Update Transaction";

    document.getElementById("tx-type").value = tx.type;
    onTxTypeChange();

    document.getElementById("tx-title").value = tx.title;
    document.getElementById("tx-amount").value = tx.amount;
    document.getElementById("tx-category").value = tx.category;
    document.getElementById("tx-date").value = tx.date;

    document.getElementById("tx-modal").classList.add("active");
}

function closeTxModal() {
    document.getElementById("tx-modal").classList.remove("active");
}

async function submitTransaction() {
    const editId = document.getElementById("tx-edit-id").value;
    const type = document.getElementById("tx-type").value;
    const title = document.getElementById("tx-title").value.trim();
    const amount = parseFloat(document.getElementById("tx-amount").value);
    const category = document.getElementById("tx-category").value;
    const date = document.getElementById("tx-date").value;

    if (!title) {
        alert("Please enter a transaction title.");
        return;
    }
    if (isNaN(amount) || amount <= 0) {
        alert("Please enter a valid positive amount.");
        return;
    }

    const payload = { type, title, amount, category, date };

    try {
        let response;
        if (editId) {
            // PUT request (Edit)
            response = await fetch(`/api/transactions/${editId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            // POST request (Create)
            response = await fetch('/api/transactions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        const resData = await response.json();
        if (response.ok && resData.status === 'success') {
            closeTxModal();
            loadDashboard(); // Refresh full dashboard analytics & charts
        } else {
            alert(resData.message || "Failed to save transaction.");
        }
    } catch (err) {
        console.error("Save Transaction Error:", err);
        alert("Network error while saving transaction.");
    }
}

async function deleteTransaction(txId) {
    const tx = allTransactionsData.find(t => t.id === txId);
    const label = tx ? `"${tx.title}" (₹${parseFloat(tx.amount).toLocaleString('en-IN')})` : "this transaction";

    if (!confirm(`Are you sure you want to delete ${label}? This will recalculate your savings and AI models.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/transactions/${txId}`, {
            method: 'DELETE'
        });

        const resData = await response.json();
        if (response.ok && resData.status === 'success') {
            loadDashboard(); // Refresh full dashboard analytics & charts
        } else {
            alert(resData.message || "Failed to delete transaction.");
        }
    } catch (err) {
        console.error("Delete Transaction Error:", err);
        alert("Network error while deleting transaction.");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadDashboard();
});
