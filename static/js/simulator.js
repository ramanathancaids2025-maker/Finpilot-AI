const simulatorCurrency = value => `₹${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

function setSimulatorStatus(message, type = 'error') {
    const status = document.getElementById('simulator-status');
    if (!status) return;
    status.className = `form-status-msg ${type}`;
    status.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-circle-check' : 'fa-triangle-exclamation'}"></i> ${escapeHtml(message)}`;
}

function updateScenarioFields() {
    const type = document.getElementById('scenario-type').value;
    const categoryGroup = document.getElementById('scenario-category-group');
    const percentageGroup = document.getElementById('scenario-percentage-group');
    const amountGroup = document.getElementById('scenario-amount-group');
    const percentageLabel = document.querySelector('#scenario-percentage-group label');

    categoryGroup.classList.toggle('hidden', type !== 'category_reduction');
    percentageGroup.classList.toggle('hidden', type === 'income_change');
    amountGroup.classList.toggle('hidden', type !== 'income_change');
    if (percentageLabel) {
        percentageLabel.innerText = type === 'expense_cut' ? 'Expense cut percentage' : 'Reduction percentage';
    }
}

async function loadSimulatorCategories() {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();
        if (!response.ok) throw new Error('Unable to load spending categories.');
        const select = document.getElementById('scenario-category');
        const categories = Object.keys(data.category_distribution || {});
        if (categories.length) {
            select.innerHTML = categories.map(category =>
                `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`
            ).join('');
        }
    } catch (error) {
        setSimulatorStatus(error.message);
    }
}

function renderSimulation(data) {
    const result = document.getElementById('simulator-result');
    const emptyState = document.getElementById('simulator-empty-state');
    if (!result) return;

    const surplusChange = Number(data.simulated.monthly_surplus) - Number(data.current.monthly_surplus);
    const changeClass = surplusChange >= 0 ? 'text-emerald' : 'text-rose';
    const goalImpacts = data.impact.goals_acceleration || [];

    result.classList.remove('hidden');
    emptyState?.classList.add('hidden');
    result.innerHTML = `
        <div class="result-card-header">
            <div>
                <h2 class="card-heading">Scenario Result</h2>
                <p class="card-subheading">${escapeHtml(data.explanation || 'Live simulation complete.')}</p>
            </div>
            <span class="badge badge-cyan">${escapeHtml(data.scenario_type.replaceAll('_', ' '))}</span>
        </div>
        <div class="simulator-result-summary">
            <div class="simulator-stat">
                <span class="simulator-stat-label">Current surplus</span>
                <strong class="simulator-stat-value">${simulatorCurrency(data.current.monthly_surplus)}/mo</strong>
            </div>
            <div class="simulator-stat">
                <span class="simulator-stat-label">Simulated surplus</span>
                <strong class="simulator-stat-value">${simulatorCurrency(data.simulated.monthly_surplus)}/mo</strong>
            </div>
            <div class="simulator-stat">
                <span class="simulator-stat-label">Surplus change</span>
                <strong class="simulator-stat-value ${changeClass}">${surplusChange >= 0 ? '+' : ''}${simulatorCurrency(surplusChange)}/mo</strong>
            </div>
        </div>
        <div class="scenario-row" style="margin-top:1rem;">
            <span>Current savings rate</span><strong>${Number(data.current.savings_rate_pct).toFixed(1)}%</strong>
        </div>
        <div class="scenario-row">
            <span>Simulated savings rate</span><strong>${Number(data.simulated.savings_rate_pct).toFixed(1)}%</strong>
        </div>
        <div class="scenario-row">
            <span>Additional monthly savings</span><strong class="text-emerald">+${simulatorCurrency(data.impact.monthly_savings_increase)}</strong>
        </div>
        <div class="scenario-row">
            <span>Additional annual savings</span><strong class="text-emerald">+${simulatorCurrency(data.impact.annual_additional_savings)}</strong>
        </div>
        <div class="explanation-box">
            <i class="fa-solid fa-lightbulb text-amber"></i>
            ${escapeHtml(data.explanation || 'Review the simulated figures before making a change.')}
        </div>
        <div style="margin-top:1.25rem;">
            <h3 class="card-heading" style="margin-bottom:0.75rem;">Goal acceleration</h3>
            ${goalImpacts.length ? goalImpacts.map(goal => `
                <div class="goal-impact-row" style="padding:0.55rem 0;border-bottom:1px solid var(--border-color);">
                    <span>${escapeHtml(goal.title)}</span>
                    <span class="text-emerald">${Number(goal.months_faster).toFixed(1)} months faster</span>
                </div>
            `).join('') : '<p class="text-muted text-sm">No active goals have remaining amounts to compare.</p>'}
        </div>
    `;
}

async function runSimulation(event) {
    event.preventDefault();
    const type = document.getElementById('scenario-type').value;
    const percentage = Number(document.getElementById('scenario-percentage').value);
    const amount = Number(document.getElementById('scenario-amount').value);
    const payload = { scenario_type: type };

    if (type === 'category_reduction') {
        payload.category = document.getElementById('scenario-category').value;
        payload.percentage = percentage;
    } else if (type === 'expense_cut') {
        payload.percentage = percentage;
    } else {
        payload.amount = amount;
    }

    if ((type !== 'income_change' && (!Number.isFinite(percentage) || percentage < 0 || percentage > 100)) ||
        (type === 'income_change' && !Number.isFinite(amount))) {
        setSimulatorStatus('Enter a valid scenario value.');
        return;
    }

    const button = document.getElementById('simulate-btn');
    button.disabled = true;
    setSimulatorStatus('Running live simulation...', 'success');
    try {
        const response = await fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || 'Simulation failed.');
        setSimulatorStatus('Simulation complete.', 'success');
        renderSimulation(data);
    } catch (error) {
        setSimulatorStatus(error.message);
    } finally {
        button.disabled = false;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('scenario-type')?.addEventListener('change', updateScenarioFields);
    document.getElementById('simulator-form')?.addEventListener('submit', runSimulation);
    updateScenarioFields();
    loadSimulatorCategories();
});
