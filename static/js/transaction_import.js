let importRows = [];

function setImportStatus(message, type = 'error') {
    const status = document.getElementById('import-status');
    if (!status) return;
    status.className = `form-status-msg ${type}`;
    status.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-circle-check' : 'fa-triangle-exclamation'}"></i> ${escapeHtml(message)}`;
}

function renderImportPreview(data) {
    importRows = data.rows || [];
    const preview = document.getElementById('import-preview');
    const summary = document.getElementById('import-summary');
    const body = document.getElementById('import-preview-body');
    const invalidMessage = document.getElementById('invalid-row-message');
    const confirmButton = document.getElementById('confirm-import-btn');

    preview.classList.remove('hidden');
    summary.innerHTML = `
        <span class="import-count">Valid rows: <strong>${data.valid_count}</strong></span>
        <span class="import-count">Invalid rows: <strong>${data.invalid_count}</strong></span>
        <span class="import-count">Duplicate transactions skipped: <strong>${data.duplicate_count}</strong></span>
        <span class="import-count">Total rows: <strong>${data.total_rows}</strong></span>
    `;

    if (data.invalid_rows?.length) {
        invalidMessage.innerHTML = `<ul class="import-invalid-list">${data.invalid_rows.map(item =>
            `<li>Row ${item.row}: ${escapeHtml(item.error)}</li>`
        ).join('')}</ul>`;
    } else {
        invalidMessage.innerHTML = '';
    }

    body.innerHTML = importRows.length ? importRows.map(row => `
        <tr>
            <td>${escapeHtml(row.date)}</td>
            <td>${escapeHtml(row.title)}</td>
            <td>₹${Number(row.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
            <td>${escapeHtml(row.category)}</td>
            <td><span class="badge ${row.type === 'income' ? 'badge-emerald' : 'badge-neutral'}">${escapeHtml(row.type)}</span></td>
        </tr>
    `).join('') : '<tr><td colspan="5" class="text-center text-muted">No valid rows are ready to import.</td></tr>';

    confirmButton.disabled = importRows.length === 0;
}

async function previewCsv(event) {
    event.preventDefault();
    const fileInput = document.getElementById('csv-file');
    const file = fileInput.files[0];
    if (!file) {
        setImportStatus('Please select a CSV file.');
        return;
    }
    if (!file.name.toLowerCase().endsWith('.csv')) {
        setImportStatus('Please select a file with a .csv extension.');
        return;
    }

    const button = document.getElementById('preview-csv-btn');
    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Validating...';
    try {
        const formData = new FormData();
        formData.append('file', file);
        const response = await fetch('/api/transactions/import/preview', { method: 'POST', body: formData });
        const data = await response.json();
        if (!response.ok || data.status !== 'success') {
            throw new Error(data.message || 'CSV preview failed.');
        }
        setImportStatus('Preview ready. Review the rows before importing.', 'success');
        renderImportPreview(data);
    } catch (error) {
        setImportStatus(error.message);
        document.getElementById('import-preview').classList.add('hidden');
    } finally {
        button.disabled = false;
        button.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> Preview CSV';
    }
}

async function confirmCsvImport() {
    if (!importRows.length) return;
    const button = document.getElementById('confirm-import-btn');
    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Importing...';
    try {
        const response = await fetch('/api/transactions/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rows: importRows })
        });
        const data = await response.json();
        if (!response.ok || data.status !== 'success') {
            throw new Error(data.message || 'Import failed.');
        }
        const invalidCount = Number(data.invalid_count || 0);
        const duplicateCount = Number(data.duplicate_count || 0);
        const skipped = invalidCount + duplicateCount;
        const skippedMessage = [
            duplicateCount ? `${duplicateCount} duplicate transactions skipped` : '',
            invalidCount ? `${invalidCount} invalid rows skipped` : ''
        ].filter(Boolean).join('; ');
        setImportStatus(
            `${data.imported_count} transactions imported successfully${skipped ? `; ${skippedMessage}.` : '.'}`,
            'success'
        );
        importRows = [];
        button.innerHTML = '<i class="fa-solid fa-circle-check"></i> Imported';
        setTimeout(() => { window.location.href = '/transactions'; }, 900);
    } catch (error) {
        setImportStatus(error.message);
        button.disabled = false;
        button.innerHTML = '<i class="fa-solid fa-file-import"></i> Import Transactions';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('csv-import-form')?.addEventListener('submit', previewCsv);
    document.getElementById('confirm-import-btn')?.addEventListener('click', confirmCsvImport);
});
