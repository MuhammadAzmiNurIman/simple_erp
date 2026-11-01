import { apiRequest } from './api'

export interface PrintableDocument {
  title: string
  code: string
  subtitle?: string
  details: Array<[string, string]>
  columns: string[]
  rows: string[][]
  totals?: Array<[string, string]>
  note?: string
  signatures?: string[]
}

function escapeHtml(value: string | null | undefined): string {
  return (value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function buildPrintableHtml(document: PrintableDocument): string {
  const details = document.details
    .map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value || '—')}</dd></div>`)
    .join('')
  const headers = document.columns.map((column) => `<th>${escapeHtml(column)}</th>`).join('')
  const rows = document.rows.length
    ? document.rows.map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join('')}</tr>`).join('')
    : `<tr><td colspan="${Math.max(document.columns.length, 1)}" class="empty">Tidak ada rincian.</td></tr>`
  const totals = document.totals?.length
    ? `<dl class="totals">${document.totals.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join('')}</dl>`
    : ''
  const note = document.note ? `<p class="note">${escapeHtml(document.note)}</p>` : ''
  const signatures = document.signatures?.length
    ? `<section class="signatures">${document.signatures.map((label) => `<div><span>${escapeHtml(label)}</span><i></i><small>Nama & tanda tangan</small></div>`).join('')}</section>`
    : ''

  return `<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(document.title)} ${escapeHtml(document.code)}</title>
  <style>
    :root{font-family:Arial,Helvetica,sans-serif;color:#17202a;font-size:12px}
    *{box-sizing:border-box}
    body{margin:0;background:#f1f5f9;padding:28px}
    main{max-width:850px;margin:auto;background:white;padding:44px}
    .toolbar{display:flex;justify-content:flex-end;margin:0 auto 12px;max-width:850px}
    button{border:0;border-radius:6px;background:#087e63;color:white;padding:10px 16px;font-weight:700;cursor:pointer}
    header{display:flex;justify-content:space-between;gap:24px;border-bottom:2px solid #087e63;padding-bottom:20px}
    .brand{font-size:20px;font-weight:800;color:#087e63;letter-spacing:.02em}
    .tagline{margin-top:5px;color:#64748b;font-size:10px}
    .document-title{text-align:right}
    h1{margin:0;font-size:22px;text-transform:uppercase}
    .code{margin-top:7px;color:#475569;font-size:13px;font-weight:700}
    .subtitle{margin:8px 0 0;color:#64748b;font-size:11px}
    dl{margin:0}
    .details{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px 30px;padding:22px 0}
    dt{color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:.06em}
    dd{margin:4px 0 0;font-size:12px;font-weight:600;white-space:pre-wrap}
    table{width:100%;border-collapse:collapse;margin-top:8px}
    th{background:#f1f5f9;text-align:left;font-size:10px;text-transform:uppercase;color:#475569}
    th,td{border-bottom:1px solid #e2e8f0;padding:10px 8px;vertical-align:top}
    td{font-size:11px}
    .empty{text-align:center;color:#64748b}
    .totals{margin:18px 0 0 auto;max-width:320px}
    .totals div{display:flex;justify-content:space-between;gap:16px;padding:6px 0}
    .totals dd{margin:0;text-align:right}
    .totals div:last-child{border-top:1px solid #cbd5e1;margin-top:4px;padding-top:10px;font-size:14px}
    .note{margin-top:22px;border-top:1px solid #e2e8f0;padding-top:12px;color:#475569;white-space:pre-wrap}
    .signatures{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:30px;margin-top:54px;page-break-inside:avoid}
    .signatures div{display:flex;flex-direction:column;min-height:90px}
    .signatures span{font-size:11px;font-weight:700}
    .signatures i{flex:1}
    .signatures small{border-top:1px solid #94a3b8;padding-top:6px;color:#64748b}
    footer{margin-top:28px;border-top:1px solid #e2e8f0;padding-top:9px;color:#94a3b8;font-size:9px}
    @page{size:A4;margin:14mm}
    @media print{body{background:white;padding:0}main{max-width:none;padding:0}.toolbar{display:none}header,table,.totals,.details,.signatures{break-inside:avoid}tr{break-inside:avoid}}
    @media(max-width:600px){body{padding:10px}main{padding:22px}header{flex-direction:column}.document-title{text-align:left}.details{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <div class="toolbar"><button onclick="window.print()">Cetak / Simpan PDF</button></div>
  <main>
    <header>
      <div><div class="brand">DistribuFlow ERP</div><div class="tagline">Dokumen operasional</div></div>
      <div class="document-title"><h1>${escapeHtml(document.title)}</h1><div class="code">${escapeHtml(document.code)}</div>${document.subtitle ? `<p class="subtitle">${escapeHtml(document.subtitle)}</p>` : ''}</div>
    </header>
    <dl class="details">${details}</dl>
    <table><thead><tr>${headers}</tr></thead><tbody>${rows}</tbody></table>
    ${totals}${note}${signatures}
    <footer>Dicetak dari DistribuFlow ERP pada ${escapeHtml(new Intl.DateTimeFormat('id-ID', { dateStyle: 'long', timeStyle: 'short' }).format(new Date()))}. Dokumen ini dibuat dari data yang tercatat pada sistem.</footer>
  </main>
</body>
</html>`
}

export async function printApiDocument<T>(
  path: string,
  title: string,
  buildDocument: (data: T) => PrintableDocument,
): Promise<void> {
  const printWindow = window.open('', '_blank')
  if (!printWindow) {
    throw new Error('Jendela cetak diblokir browser. Izinkan pop-up untuk aplikasi ini lalu coba lagi.')
  }

  printWindow.document.write(
    `<!doctype html><html lang="id"><head><title>${escapeHtml(title)}</title></head><body>Memuat dokumen…</body></html>`,
  )
  printWindow.document.close()
  printWindow.opener = null

  try {
    const response = await apiRequest<{ data: T }>(path)
    const html = buildPrintableHtml(buildDocument(response.data))
    printWindow.document.open()
    printWindow.document.write(html)
    printWindow.document.close()
  } catch (error) {
    printWindow.close()
    throw error
  }
}

export function printDocument(document: PrintableDocument): void {
  const html = buildPrintableHtml(document)
  const printWindow = window.open('', '_blank')
  if (!printWindow) {
    throw new Error('Jendela cetak diblokir browser. Izinkan pop-up untuk aplikasi ini lalu coba lagi.')
  }
  printWindow.document.write(html)
  printWindow.document.close()
  printWindow.opener = null
}
