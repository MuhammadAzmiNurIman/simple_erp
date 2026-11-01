import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Download, Search } from 'lucide-react'
import { apiRequest } from './api'

type Warehouse = { id: number; code: string; name: string }
type ReportKey = 'inventory' | 'stock-movements' | 'sales' | 'purchases' | 'receivables' | 'payables'
type ReportRow = Record<string, unknown>
type ReportResponse = { data: ReportRow[]; total: number; page?: number; pages?: number; [key: string]: unknown }
type LookupRow = { id: number; name: string; code?: string; sku?: string }

const reports: Array<{ id: ReportKey; label: string; filters: Array<'date' | 'warehouse' | 'product' | 'status' | 'customer' | 'supplier' | 'movement'> }> = [
  { id: 'inventory', label: 'Stok', filters: ['warehouse', 'product'] },
  { id: 'stock-movements', label: 'Pergerakan stok', filters: ['date', 'warehouse', 'product', 'movement'] },
  { id: 'sales', label: 'Penjualan', filters: ['date', 'warehouse', 'status', 'customer'] },
  { id: 'purchases', label: 'Pembelian', filters: ['date', 'warehouse', 'status', 'supplier'] },
  { id: 'receivables', label: 'Piutang', filters: ['date', 'warehouse', 'status', 'customer'] },
  { id: 'payables', label: 'Utang', filters: ['date', 'warehouse', 'status', 'supplier'] },
]

export default function ReportsPage({ warehouses, selectedWarehouseId, permissions, canSelectAllWarehouses }: { warehouses: Warehouse[]; selectedWarehouseId: string; permissions: string[]; canSelectAllWarehouses: boolean }) {
  const [report, setReport] = useState<ReportKey>('inventory')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [warehouseId, setWarehouseId] = useState(selectedWarehouseId)
  const [productId, setProductId] = useState('')
  const [status, setStatus] = useState('')
  const [customerId, setCustomerId] = useState('')
  const [supplierId, setSupplierId] = useState('')
  const [movementType, setMovementType] = useState('')
  const [products, setProducts] = useState<LookupRow[]>([])
  const [customers, setCustomers] = useState<LookupRow[]>([])
  const [suppliers, setSuppliers] = useState<LookupRow[]>([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [rows, setRows] = useState<ReportRow[]>([])
  const [summary, setSummary] = useState('')
  const [total, setTotal] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const selectedReport = reports.find((item) => item.id === report) ?? reports[0]
  const statusOptions = report === 'receivables' || report === 'payables'
    ? ['OPEN', 'PARTIALLY_PAID']
    : ['OPEN', 'PARTIALLY_PAID', 'PAID']

  useEffect(() => {
    let active = true
    async function loadAll<T extends { id: number }>(path: string): Promise<T[]> {
      const first = await apiRequest<{ data: T[]; pages?: number }>(`${path}?page=1&per_page=100`)
      const result = [...(first.data ?? [])]
      for (let currentPage = 2; currentPage <= (first.pages ?? 1); currentPage += 1) {
        const next = await apiRequest<{ data: T[] }>(`${path}?page=${currentPage}&per_page=100`)
        result.push(...(next.data ?? []))
      }
      return result
    }
    const productRequest = permissions.includes('master_data.read')
      ? loadAll<LookupRow>('/products').catch(() => [] as LookupRow[])
      : Promise.resolve([] as LookupRow[])
    const customerRequest = permissions.includes('customers.read')
      ? loadAll<LookupRow>('/customers').catch(() => [] as LookupRow[])
      : Promise.resolve([] as LookupRow[])
    const supplierRequest = permissions.includes('suppliers.read')
      ? loadAll<LookupRow>('/suppliers').catch(() => [] as LookupRow[])
      : Promise.resolve([] as LookupRow[])
    Promise.all([productRequest, customerRequest, supplierRequest]).then(([productRows, customerRows, supplierRows]) => {
      if (active) { setProducts(productRows); setCustomers(customerRows); setSuppliers(supplierRows) }
    })
    return () => { active = false }
  }, [permissions])

  function params(requestedPage = page) {
    const query = new URLSearchParams({ page: String(requestedPage), per_page: '100' })
    if (selectedReport.filters.includes('date')) {
      if (fromDate) query.set('from_date', fromDate)
      if (toDate) query.set('to_date', toDate)
    }
    if (selectedReport.filters.includes('warehouse') && warehouseId) query.set('warehouse_id', warehouseId)
    if (selectedReport.filters.includes('product') && productId) query.set('product_id', productId)
    if (selectedReport.filters.includes('status') && status) query.set('status', status)
    if (selectedReport.filters.includes('customer') && customerId) query.set('customer_id', customerId)
    if (selectedReport.filters.includes('supplier') && supplierId) query.set('supplier_id', supplierId)
    if (selectedReport.filters.includes('movement') && movementType) query.set('movement_type', movementType)
    return query
  }

  async function load(event?: FormEvent) {
    event?.preventDefault()
    setBusy(true); setError(''); setSummary('')
    try {
      const response = await apiRequest<ReportResponse>(`/reports/${report}?${params(1).toString()}`)
      setRows(response.data ?? []); setTotal(response.total ?? 0); setPages(Math.max(response.pages ?? 1, 1)); setPage(1)
      const summaryKey = report === 'inventory' ? 'total_inventory_value' : report === 'sales' ? 'total_sales_amount' : report === 'purchases' ? 'total_purchase_amount' : ''
      if (summaryKey && response[summaryKey] !== undefined) setSummary(String(response[summaryKey]))
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Laporan gagal dimuat.') }
    finally { setBusy(false) }
  }

  async function loadPage(requestedPage: number) {
    setBusy(true); setError('')
    try {
      const response = await apiRequest<ReportResponse>(`/reports/${report}?${params(requestedPage).toString()}`)
      setRows(response.data ?? []); setTotal(response.total ?? 0); setPages(Math.max(response.pages ?? 1, 1)); setPage(requestedPage)
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Halaman laporan gagal dimuat.') }
    finally { setBusy(false) }
  }

  async function exportCsv() {
    setBusy(true); setError('')
    try {
      const first = await apiRequest<ReportResponse>(`/reports/${report}?${params(1).toString()}`)
      const allRows = [...(first.data ?? [])]
      const pages = first.pages ?? 1
      for (let page = 2; page <= pages; page += 1) {
        const next = await apiRequest<ReportResponse>(`/reports/${report}?${params(page).toString()}`)
        allRows.push(...(next.data ?? []))
      }
      const keys = Array.from(new Set(allRows.flatMap((row) => Object.keys(row))))
      const cell = (value: unknown) => {
        let text = value === null || value === undefined ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value)
        if (typeof value === 'string' && /^[=+\-@\t\r]/.test(text)) text = `'${text}`
        return `"${text.replaceAll('"', '""')}"`
      }
      const csv = [keys.map(cell).join(','), ...allRows.map((row) => keys.map((key) => cell(row[key])).join(','))].join('\r\n')
      const url = URL.createObjectURL(new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8' }))
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = `laporan-${report}-${new Date().toISOString().slice(0, 10)}.csv`; anchor.click(); URL.revokeObjectURL(url)
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Ekspor CSV gagal.') }
    finally { setBusy(false) }
  }

  const headers = Array.from(new Set(rows.flatMap((row) => Object.keys(row))))
  return <>
    <div className="mb-5"><p className="text-[11px] font-bold tracking-[0.18em] text-emerald-700">ANALISIS</p><h1 className="mt-1 text-2xl font-bold text-slate-900">Laporan</h1><p className="mt-1 text-sm text-slate-500">Gunakan filter untuk mempersempit data. Ekspor CSV dapat dibuka di Excel.</p></div>
    <div className="erp-tab-strip mb-5 flex gap-2 overflow-x-auto pb-1">{reports.map((item) => <button key={item.id} type="button" onClick={() => { setReport(item.id); setPage(1); setStatus(''); setRows([]); setSummary(''); setError('') }} className={`shrink-0 rounded-xl border px-3.5 py-2.5 text-sm font-semibold transition ${report === item.id ? 'border-emerald-800 bg-emerald-800 text-white shadow-sm' : 'border-slate-200 bg-white text-slate-600 hover:border-emerald-200 hover:bg-emerald-50/60'}`}>{item.label}</button>)}</div>
    <form onSubmit={(event) => void load(event)} className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-[0_2px_10px_-7px_rgba(15,23,42,0.18)] sm:p-5">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {selectedReport.filters.includes('date') && <><label className="text-xs font-semibold text-slate-600">Dari tanggal<input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label><label className="text-xs font-semibold text-slate-600">Sampai tanggal<input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label></>}
        {selectedReport.filters.includes('warehouse') && <label className="text-xs font-semibold text-slate-600">Gudang<select value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal">{canSelectAllWarehouses && <option value="">Semua gudang</option>}{warehouses.map((warehouse) => <option key={warehouse.id} value={warehouse.id}>{warehouse.code} · {warehouse.name}</option>)}</select></label>}
        {selectedReport.filters.includes('product') && (products.length ? <label className="text-xs font-semibold text-slate-600">Produk<select value={productId} onChange={(e) => setProductId(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal"><option value="">Semua produk</option>{products.map((item) => <option key={item.id} value={item.id}>{item.sku ? `${item.sku} · ` : ''}{item.name}</option>)}</select></label> : <IdFilter label="ID produk" value={productId} onChange={setProductId} />)}
        {selectedReport.filters.includes('movement') && <label className="text-xs font-semibold text-slate-600">Jenis pergerakan<select value={movementType} onChange={(e) => setMovementType(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal"><option value="">Semua jenis</option>{['IN', 'OUT', 'ADJUSTMENT', 'TRANSFER_IN', 'TRANSFER_OUT', 'RETURN_IN'].map((item) => <option key={item} value={item}>{item.replaceAll('_', ' ')}</option>)}</select></label>}
        {selectedReport.filters.includes('status') && <label className="text-xs font-semibold text-slate-600">Status<select value={status} onChange={(e) => setStatus(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal"><option value="">Semua status</option>{statusOptions.map((item) => <option key={item} value={item}>{item.replaceAll('_', ' ')}</option>)}</select></label>}
        {selectedReport.filters.includes('customer') && (customers.length ? <label className="text-xs font-semibold text-slate-600">Pelanggan<select value={customerId} onChange={(e) => setCustomerId(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal"><option value="">Semua pelanggan</option>{customers.map((item) => <option key={item.id} value={item.id}>{item.code ? `${item.code} · ` : ''}{item.name}</option>)}</select></label> : <IdFilter label="ID pelanggan" value={customerId} onChange={setCustomerId} />)}
        {selectedReport.filters.includes('supplier') && (suppliers.length ? <label className="text-xs font-semibold text-slate-600">Supplier<select value={supplierId} onChange={(e) => setSupplierId(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal"><option value="">Semua supplier</option>{suppliers.map((item) => <option key={item.id} value={item.id}>{item.code ? `${item.code} · ` : ''}{item.name}</option>)}</select></label> : <IdFilter label="ID supplier" value={supplierId} onChange={setSupplierId} />)}
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2"><button disabled={busy} className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"><Search size={15} />Tampilkan</button><button type="button" disabled={busy} onClick={() => void exportCsv()} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-50"><Download size={15} />Ekspor CSV</button><span className="text-xs text-slate-500">{total} baris</span>{summary && <span className="ml-auto text-sm font-semibold text-slate-700">Total: {summary}</span>}</div>
    </form>
    {error && <div role="alert" className="mt-4 rounded-lg border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
    <div className="mt-5 max-w-full overflow-auto rounded-2xl border border-slate-200/80 bg-white shadow-[0_2px_10px_-7px_rgba(15,23,42,0.18)]">{rows.length ? <table className="min-w-full text-left text-xs"><thead className="bg-slate-50 text-slate-500"><tr>{headers.map((header) => <th key={header} className="whitespace-nowrap px-4 py-3 font-semibold">{header.replaceAll('_', ' ')}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={String(row.id ?? row.product_id ?? index)} className="border-t border-slate-100 hover:bg-slate-50/70">{headers.map((header) => <td key={header} className="whitespace-nowrap px-4 py-3 text-slate-700">{row[header] === null || row[header] === undefined ? '—' : typeof row[header] === 'object' ? JSON.stringify(row[header]) : String(row[header])}</td>)}</tr>)}</tbody></table> : <div className="p-8 text-center text-sm text-slate-500">{busy ? 'Memuat laporan…' : 'Pilih filter lalu tampilkan laporan.'}</div>}{rows.length > 0 && <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3"><span className="text-xs text-slate-500">Halaman {page} dari {pages}</span><div className="flex gap-2"><button type="button" disabled={busy || page <= 1} onClick={() => { const next = page - 1; setPage(next); void loadPage(next) }} className="rounded-lg border border-slate-200 px-3 py-2 text-xs disabled:opacity-40">Sebelumnya</button><button type="button" disabled={busy || page >= pages} onClick={() => { const next = page + 1; setPage(next); void loadPage(next) }} className="rounded-lg border border-slate-200 px-3 py-2 text-xs disabled:opacity-40">Berikutnya</button></div></div>}</div>
  </>
}

function IdFilter({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="text-xs font-semibold text-slate-600">{label}<input type="number" min="1" value={value} onChange={(event) => onChange(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
}
