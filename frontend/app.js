const el = (id) => document.getElementById(id);
let latestDecisions = [];

function setStatus(text, cls) {
  const pill = el('statusPill');
  pill.textContent = text;
  pill.className = `status-pill ${cls}`;
}

function formatINR(value) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(value || 0);
}

function renderMetrics(data) {
  const metrics = [
    ['Recommended payable', formatINR(data.recommended_payable)],
    ['Claimed invoice', formatINR(data.claimed_invoice_amount)],
    ['Withheld amount', formatINR(data.withheld_amount)],
    ['Eligible shipments', data.eligible_shipments],
    ['Held shipments', data.held_shipments],
    ['Confidence', data.confidence],
  ];
  el('metricsGrid').innerHTML = metrics.map(([label, value]) => `
    <div class="metric-card">
      <div class="label">${label}</div>
      <div class="value">${value}</div>
    </div>
  `).join('');
}

function renderRationale(data) {
  el('rationaleList').innerHTML = data.rationale_summary.map(item => `<li>${item}</li>`).join('');
  el('clausesList').innerHTML = data.contract_clauses.map(item => `
    <div class="clause-card">
      <div class="title">${item.title}</div>
      <div>${item.snippet}</div>
    </div>
  `).join('');

  const reasons = Object.entries(data.held_reasons_breakdown || {});
  el('heldReasons').innerHTML = reasons.length
    ? reasons.map(([k, v]) => `<div class="kv"><div>${k}</div><strong>${v}</strong></div>`).join('')
    : '<div class="muted">No held reasons found.</div>';

  el('diagnosticsBox').textContent = JSON.stringify(data.diagnostics, null, 2);
}

function renderDecisionTable(decisions) {
  latestDecisions = decisions;
  const tbody = document.querySelector('#decisionTable tbody');
  tbody.innerHTML = decisions.map(item => `
    <tr>
      <td>${item.shipment_id}</td>
      <td><span class="badge ${item.decision}">${item.decision}</span></td>
      <td>${formatINR(item.invoice_amount)}</td>
      <td>${item.erp_status || '-'}</td>
      <td>${item.reasons.map(r => `<span class="reason-pill">${r}</span>`).join('')}</td>
    </tr>
  `).join('');
}

function applyFilter() {
  const q = el('decisionFilter').value.trim().toLowerCase();
  if (!q) return renderDecisionTable(latestDecisions);
  const filtered = latestDecisions.filter(item => {
    const blob = [item.shipment_id, item.decision, item.erp_status, ...(item.reasons || [])].join(' ').toLowerCase();
    return blob.includes(q);
  });
  const tbody = document.querySelector('#decisionTable tbody');
  tbody.innerHTML = filtered.map(item => `
    <tr>
      <td>${item.shipment_id}</td>
      <td><span class="badge ${item.decision}">${item.decision}</span></td>
      <td>${formatINR(item.invoice_amount)}</td>
      <td>${item.erp_status || '-'}</td>
      <td>${item.reasons.map(r => `<span class="reason-pill">${r}</span>`).join('')}</td>
    </tr>
  `).join('');
}

async function analyzeWithFiles(contractFile, erpFile, invoiceFile) {
  const apiBase = el('apiBase').value.trim().replace(/\/$/, '');
  const form = new FormData();
  form.append('contract_file', contractFile);
  form.append('erp_file', erpFile);
  form.append('invoice_file', invoiceFile);
  setStatus('Analyzing', 'loading');
  try {
    const response = await fetch(`${apiBase}/analyze`, { method: 'POST', body: form });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || 'Request failed');
    }
    const data = await response.json();
    renderMetrics(data);
    renderRationale(data);
    renderDecisionTable(data.decisions || []);
    el('resultsSection').classList.remove('hidden');
    setStatus('Analysis complete', 'done');
  } catch (err) {
    console.error(err);
    setStatus('Error', 'error');
    alert(`Analysis failed: ${err.message}`);
  }
}

el('analyzeBtn').addEventListener('click', () => {
  const contract = el('contractFile').files[0];
  const erp = el('erpFile').files[0];
  const invoice = el('invoiceFile').files[0];
  if (!contract || !erp || !invoice) {
    alert('Please upload all three files first.');
    return;
  }
  analyzeWithFiles(contract, erp, invoice);
});

el('decisionFilter').addEventListener('input', applyFilter);

el('demoBtn').addEventListener('click', async () => {
  const paths = [
    '../sample_data/3PL_Aggregator_Carrier_Master_Transportation_Agreement.docx',
    '../sample_data/Carrier_ERP_Raw_Performance_March_2026.xlsx',
    '../sample_data/Carrier_Service_Invoice_March_2026.xlsx',
  ];
  try {
    const files = await Promise.all(paths.map(async (path) => {
      const res = await fetch(path);
      const blob = await res.blob();
      const name = path.split('/').pop();
      return new File([blob], name, { type: blob.type || 'application/octet-stream' });
    }));
    analyzeWithFiles(files[0], files[1], files[2]);
  } catch (e) {
    alert('Demo files are available when the sample_data folder is served with the repo.');
  }
});
