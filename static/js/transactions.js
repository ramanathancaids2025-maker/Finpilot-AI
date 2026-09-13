/* ==========================================================================
   FINPILOT AI - TRANSACTIONS PAGE MANAGER
   ========================================================================== */

const TX_PAGE_SIZE = 15;
let allTxData = [];
let currentPage = 1;

const CATEGORIES_MAP = {
    expense: [
        "Housing & Utilities", "Food & Dining", "Transportation",
        "Shopping & Electronics", "Entertainment & Leisure",
        "Healthcare & Fitness", "Subscriptions & Misc"
    ],
    income: [
        "Income", "Freelance", "Investment Return", "Bonus & Gifts", "Other Credit"
    ]
};

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, m =>
        ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m])
    );
}

async function loadTransactions() {
    try {
        const res = await fetch('/api/transactions');
        allTxData = await res.json();
        populateCategoryFilter();
        renderPage(1);
        renderSummary();
    } catch (err) {
        console.error('Failed to load transactions:', err);
        document.getElementById('transactions-tbody').innerHTML =
            '<tr><td colspan="6" class="text-center text-muted" style="padding:2rem;">Failed to load transactions. Check server logs.</td></tr>';
    }
}

function renderSummary() {
    const income  = allTxData.filter(t => t.type === 'income').reduce((s, t) => s + parseFloat(t.amount), 0);
    const expense = allTxData.filter(t => t.type === 'expense').reduce((s, t) => s + parseFloat(t.amount), 0);
    const net     = income - expense;

    const fmt = v => '₹' + Math.abs(v).toLocaleString('en-IN', { minimumFractionDigits: 2 });

    const si = document.getElementById('sum-income');
    const se = document.getElementById('sum-expense');
    const sn = document.getElementById('sum-net');
    const sc = document.getElementById('sum-count');

    if (si) si.innerText = fmt(income);
    if (se) se.innerText = fmt(expense);
    if (sn) {
        sn.innerText = (net >= 0 ? '+' : '-') + fmt(net);
        sn.style.color = net >= 0 ? 'var(--emerald)' : 'var(--rose)';
    }
    if (sc) sc.innerText = allTxData.length;
}

function populateCategoryFilter() {
    const sel = document.getElementById('tx-filter-category');
    if (!sel) return;
    const cats = [...new Set(allTxData.map(t => t.category))].sort();
    sel.innerHTML = '<option value="all">All Categories</option>' +
        cats.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
}

function getFiltered() {
    const query    = (document.getElementById('tx-search-input')?.value || '').toLowerCase().trim();
    const typeF    = document.getElementById('tx-filter-type')?.value || 'all';
    const catF     = document.getElementById('tx-filter-category')?.value || 'all';

    return allTxData.filter(tx => {
        const matchType = typeF === 'all' || tx.type === typeF;
        const matchCat  = catF  === 'all' || tx.category === catF;
        const matchQ    = !query ||
            tx.title.toLowerCase().includes(query) ||
            tx.category.toLowerCase().includes(query) ||
            tx.date.includes(query) ||
            String(tx.amount).includes(query);
        return matchType && matchCat && matchQ;
    });
}

function filterTransactions() {
    renderPage(1);
}

function renderPage(page) {
    currentPage = page;
    const filtered = getFiltered();
    const totalPages = Math.max(1, Math.ceil(filtered.length / TX_PAGE_SIZE));
    if (page > totalPages) page = currentPage = totalPages;

    const slice = filtered.slice((page - 1) * TX_PAGE_SIZE, page * TX_PAGE_SIZE);
    renderTable(slice);
    renderPagination(totalPages);

    const countEl = document.getElementById('tx-count-label');
    if (countEl) countEl.innerText = `${filtered.length} record${filtered.length !== 1 ? 's' : ''}`;
}

function renderTable(txs) {
    const tbody = document.getElementById('transactions-tbody');
    if (!tbody) return;
    if (!txs || txs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted" style="padding:2rem;">No transactions match your filters.</td></tr>';
        return;
    }
    tbody.innerHTML = txs.map(tx => `
        <tr>
            <td class="text-muted text-xs">${escapeHtml(tx.date)}</td>
            <td><strong>${escapeHtml(tx.title)}</strong></td>
            <td><span class="badge badge-neutral">${escapeHtml(tx.category)}</span></td>
            <td>
                <span class="badge ${tx.type === 'income' ? 'badge-emerald' : 'badge-neutral'}">
                    ${tx.type === 'income' ? '📈 Incoming' : '📉 Expense'}
                </span>
            </td>
            <td class="${tx.type === 'income' ? 'text-emerald font-bold' : 'text-main'}">
                ${tx.type === 'income' ? '+' : '-'}₹${parseFloat(tx.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </td>
            <td class="actions-cell">
                <button class="action-btn edit-btn" title="Edit" onclick="openEditModal(${tx.id})">
                    <i class="fa-solid fa-pen-to-square"></i>
                </button>
                <button class="action-btn delete-btn" title="Delete" onclick="deleteTx(${tx.id})">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function renderPagination(totalPages) {
    const row = document.getElementById('pagination-row');
    if (!row || totalPages <= 1) { if (row) row.innerHTML = ''; return; }

    let html = '';
    for (let i = 1; i <= totalPages; i++) {
        html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="renderPage(${i})">${i}</button>`;
    }
    row.innerHTML = html;
}

/* --- EDIT MODAL (inline) --- */
let editingTxId = null;

function openEditModal(txId) {
    const tx = allTxData.find(t => t.id === txId);
    if (!tx) return;
    editingTxId = txId;

    document.getElementById('em-type').value = tx.type;
    populateEditCatOptions(tx.type);
    document.getElementById('em-title').value = tx.title;
    document.getElementById('em-amount').value = tx.amount;
    document.getElementById('em-category').value = tx.category;
    document.getElementById('em-date').value = tx.date;

    document.getElementById('edit-modal').classList.add('active');
}

function populateEditCatOptions(type) {
    const sel = document.getElementById('em-category');
    const opts = CATEGORIES_MAP[type] || CATEGORIES_MAP.expense;
    sel.innerHTML = opts.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
}

function closeEditModal() {
    document.getElementById('edit-modal').classList.remove('active');
    editingTxId = null;
}

async function submitEdit() {
    if (!editingTxId) return;
    const payload = {
        type:     document.getElementById('em-type').value,
        title:    document.getElementById('em-title').value.trim(),
        amount:   parseFloat(document.getElementById('em-amount').value),
        category: document.getElementById('em-category').value,
        date:     document.getElementById('em-date').value
    };
    if (!payload.title || isNaN(payload.amount) || payload.amount <= 0) {
        showToast('Please fill in all fields correctly.', 'error');
        return;
    }
    try {
        const res = await fetch(`/api/transactions/${editingTxId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'success') {
            closeEditModal();
            showToast('Transaction updated successfully.');
            loadTransactions();
        } else {
            showToast(data.message || 'Update failed.', 'error');
        }
    } catch (err) {
        showToast('Network error.', 'error');
    }
}

async function deleteTx(txId) {
    const tx = allTxData.find(t => t.id === txId);
    const label = tx ? `"${tx.title}"` : 'this transaction';
    if (!confirm(`Delete ${label}? This will recalculate your savings balance.`)) return;
    try {
        const res = await fetch(`/api/transactions/${txId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.status === 'success') {
            showToast('Transaction deleted.');
            loadTransactions();
        } else {
            showToast(data.message || 'Delete failed.', 'error');
        }
    } catch (err) {
        showToast('Network error.', 'error');
    }
}

function showToast(msg, type = 'success') {
    const c = document.getElementById('toast-container');
    if (!c) return;
    const t = document.createElement('div');
    t.className = `toast toast-${type}`;
    const icon = type === 'success'
        ? '<i class="fa-solid fa-circle-check text-emerald"></i>'
        : '<i class="fa-solid fa-triangle-exclamation text-rose"></i>';
    t.innerHTML = icon + ' ' + msg;
    c.appendChild(t);
    setTimeout(() => t.remove(), 3500);
}

document.addEventListener('DOMContentLoaded', loadTransactions);

