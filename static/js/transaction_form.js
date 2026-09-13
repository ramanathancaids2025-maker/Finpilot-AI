/* ==========================================================================
   FINPILOT AI - ADD TRANSACTION FORM HANDLER
   ========================================================================== */

const EXPENSE_CATEGORIES = [
    "Housing & Utilities", "Food & Dining", "Transportation",
    "Shopping & Electronics", "Entertainment & Leisure",
    "Healthcare & Fitness", "Subscriptions & Misc"
];

const INCOME_CATEGORIES = [
    "Income", "Salary", "Freelance / Consulting",
    "Investments & Dividends", "Bonus & Gifts", "Side Business"
];

function onTxTypeChange() {
    const type = document.getElementById('tx-type')?.value || 'expense';
    const catSelect = document.getElementById('tx-category');
    const catChips = document.getElementById('cat-preview-chips');
    const cats = type === 'income' ? INCOME_CATEGORIES : EXPENSE_CATEGORIES;

    if (catSelect) {
        catSelect.innerHTML = cats.map(c => `<option value="${c}">${c}</option>`).join('');
    }
    if (catChips) {
        catChips.innerHTML = cats.map(c =>
            `<span style="background:rgba(255,255,255,0.05); border:1px solid var(--border-color); border-radius:6px; padding:0.2rem 0.55rem; font-size:0.7rem; color:var(--text-muted);">${c}</span>`
        ).join('');
    }
}

async function submitAddTransaction() {
    const btn = document.getElementById('tx-submit-btn');
    const statusEl = document.getElementById('form-status');

    const type     = document.getElementById('tx-type').value;
    const title    = document.getElementById('tx-title').value.trim();
    const amount   = parseFloat(document.getElementById('tx-amount').value);
    const category = document.getElementById('tx-category').value;
    const date     = document.getElementById('tx-date').value;

    statusEl.className = 'form-status-msg hidden';

    if (!title) {
        statusEl.className = 'form-status-msg error';
        statusEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Please enter a title/description.';
        return;
    }
    if (isNaN(amount) || amount <= 0) {
        statusEl.className = 'form-status-msg error';
        statusEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Please enter a valid positive amount.';
        return;
    }
    if (!date) {
        statusEl.className = 'form-status-msg error';
        statusEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Please select a date.';
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';

    try {
        const res = await fetch('/api/transactions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, title, amount, category, date })
        });
        const data = await res.json();

        if (res.ok && data.status === 'success') {
            statusEl.className = 'form-status-msg success';
            statusEl.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${data.message || 'Transaction saved!'} Redirecting...`;
            setTimeout(() => { window.location.href = '/transactions'; }, 1200);
        } else {
            statusEl.className = 'form-status-msg error';
            statusEl.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${data.message || 'Failed to save transaction.'}`;
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Transaction';
        }
    } catch (err) {
        statusEl.className = 'form-status-msg error';
        statusEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Network error. Please check server logs.';
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Transaction';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    onTxTypeChange();
    const dateEl = document.getElementById('tx-date');
    if (dateEl && !dateEl.value) {
        dateEl.value = new Date().toISOString().split('T')[0];
    }
});

