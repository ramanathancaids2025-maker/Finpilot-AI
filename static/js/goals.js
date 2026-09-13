const goalCurrency = value => `₹${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

function setGoalStatus(message, type = 'error') {
    const status = document.getElementById('goal-form-status');
    if (!status) return;
    status.className = `form-status-msg ${type}`;
    status.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-circle-check' : 'fa-triangle-exclamation'}"></i> ${escapeHtml(message)}`;
}

function clearGoalStatus() {
    const status = document.getElementById('goal-form-status');
    if (status) status.className = 'form-status-msg hidden';
}

function validateGoal(title, target, current) {
    if (!title) return 'Please enter a goal name.';
    if (!Number.isFinite(target) || target <= 0) return 'Target amount must be greater than zero.';
    if (!Number.isFinite(current) || current < 0) return 'Current amount cannot be negative.';
    if (current > target) return 'Current amount cannot exceed the target amount.';
    return '';
}

async function parseGoalResponse(response) {
    const data = await response.json();
    if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Goal request failed.');
    }
    return data;
}

function renderGoals(goals) {
    const list = document.getElementById('goals-list-content');
    const count = document.getElementById('goal-count');
    if (!list) return;

    if (count) count.innerText = `${goals.length} goal${goals.length === 1 ? '' : 's'}`;
    if (!goals.length) {
        list.innerHTML = '<p class="text-muted text-sm">No goals yet. Create your first savings target.</p>';
        return;
    }

    list.innerHTML = goals.map(goal => `
        <article class="goal-card" data-goal-id="${goal.id}">
            <div class="goal-card-header">
                <div>
                    <h3 class="card-heading">${escapeHtml(goal.title)}</h3>
                    <span class="text-muted text-xs">${goal.target_date ? `Target: ${escapeHtml(goal.target_date)}` : 'No target date'}</span>
                </div>
                <span class="badge ${goal.status === 'COMPLETED' ? 'badge-emerald' : goal.status === 'ON TRACK' ? 'badge-cyan' : 'badge-amber'}">${escapeHtml(goal.status)}</span>
            </div>
            <div class="progress-bar-container">
                <div class="bar-lbl">
                    <span>Progress</span>
                    <strong>${Number(goal.progress_pct).toFixed(1)}%</strong>
                </div>
                <div class="progress-track">
                    <div class="progress-fill fill-emerald" style="width:${Math.min(100, Number(goal.progress_pct))}%"></div>
                </div>
            </div>
            <div class="goal-card-meta">
                <span>Saved: <strong>${goalCurrency(goal.current_amount)}</strong></span>
                <span>Target: <strong>${goalCurrency(goal.target_amount)}</strong></span>
                <span>Remaining: <strong>${goalCurrency(goal.remaining_amount)}</strong></span>
            </div>
            <div class="goal-card-actions">
                <div class="form-group">
                    <label for="goal-current-${goal.id}">Update saved amount</label>
                    <input type="number" id="goal-current-${goal.id}" min="0" max="${goal.target_amount}" step="1" value="${goal.current_amount}">
                </div>
                <button class="btn btn-secondary" type="button" onclick="updateGoal(${goal.id})" title="Save current amount">
                    <i class="fa-solid fa-floppy-disk"></i> Update
                </button>
                <button class="btn btn-icon delete-btn" type="button" onclick="deleteGoal(${goal.id})" title="Delete goal" aria-label="Delete ${escapeHtml(goal.title)}">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        </article>
    `).join('');
}

async function loadGoals() {
    const list = document.getElementById('goals-list-content');
    try {
        const response = await fetch('/api/goals');
        const goals = await response.json();
        if (!response.ok) throw new Error(goals.message || 'Unable to load goals.');
        renderGoals(goals);
    } catch (error) {
        if (list) list.innerHTML = `<p class="text-rose text-sm">${escapeHtml(error.message)}</p>`;
    }
}

async function createGoal(event) {
    event.preventDefault();
    clearGoalStatus();

    const title = document.getElementById('goal-title').value.trim();
    const target = Number(document.getElementById('goal-target').value);
    const current = Number(document.getElementById('goal-current').value);
    const targetDate = document.getElementById('goal-date').value;
    const validationMessage = validateGoal(title, target, current);
    if (validationMessage) {
        setGoalStatus(validationMessage);
        return;
    }

    const button = document.getElementById('goal-submit-btn');
    button.disabled = true;
    try {
        const response = await fetch('/api/goals', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, target_amount: target, current_amount: current, target_date: targetDate })
        });
        const data = await parseGoalResponse(response);
        setGoalStatus(data.message || 'Goal created successfully.', 'success');
        document.getElementById('goal-form').reset();
        document.getElementById('goal-current').value = '0';
        await loadGoals();
    } catch (error) {
        setGoalStatus(error.message);
    } finally {
        button.disabled = false;
    }
}

async function updateGoal(goalId) {
    const input = document.getElementById(`goal-current-${goalId}`);
    const current = Number(input.value);
    const target = Number(input.max);
    const validationMessage = validateGoal('Existing goal', target, current);
    if (validationMessage) {
        setGoalStatus(validationMessage);
        return;
    }

    try {
        const response = await fetch(`/api/goals/${goalId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ current_amount: current })
        });
        const data = await parseGoalResponse(response);
        setGoalStatus(data.message || 'Goal updated successfully.', 'success');
        await loadGoals();
    } catch (error) {
        setGoalStatus(error.message);
    }
}

async function deleteGoal(goalId) {
    if (!window.confirm('Delete this savings goal?')) return;
    try {
        const response = await fetch(`/api/goals/${goalId}`, { method: 'DELETE' });
        const data = await parseGoalResponse(response);
        setGoalStatus(data.message || 'Goal deleted successfully.', 'success');
        await loadGoals();
    } catch (error) {
        setGoalStatus(error.message);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('goal-form')?.addEventListener('submit', createGoal);
    document.getElementById('goal-reset-btn')?.addEventListener('click', clearGoalStatus);
    loadGoals();
});
