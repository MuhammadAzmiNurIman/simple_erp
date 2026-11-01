import { useEffect, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { ArrowRightLeft } from 'lucide-react'
import { apiRequest } from './api'

type Warehouse = { id: number; code: string; name: string }
type Product = { id: number; sku: string; name: string }
type Balance = { id: number; product_id: number; warehouse_id: number; quantity_on_hand: number; available: number; product_name?: string; warehouse_code?: string }
type Transfer = { id: number; transfer_number: string; source_warehouse_id: number; destination_warehouse_id: number; status: string; reason: string; approved_by?: number | null; approved_by_username?: string | null; approved_at?: string | null; rejected_by?: number | null; rejected_by_username?: string | null; rejected_at?: string | null; items: Array<{ product_id: number; quantity: number }> }
type Adjustment = { id: number; code: string; product_id: number; warehouse_id: number; adjustment_type: 'ADD' | 'REDUCE'; quantity: number; status: string; description: string | null }
type ShipmentItem = { id: number; product_id: number; product_name: string; quantity: number }
type Shipment = { id: number; code: string; customer_name?: string; items: ShipmentItem[] }
type SalesReturn = { id: number; return_number: string; shipment_code: string; status: string; reason: string; items: Array<{ product_name: string; quantity: number; condition: string }> }
type QuarantineAction = { id: number; action: 'RELEASE' | 'SCRAP'; status: string; reason: string; created_by_username?: string | null; reviewed_by_username?: string | null; posted_by_username?: string | null }
type Quarantine = { id: number; return_number: string; product_id: number; product_name: string; warehouse_id: number; warehouse_code: string; quantity: number; reason: string; status: 'QUARANTINED' | 'RELEASED' | 'SCRAPPED'; actions: QuarantineAction[] }

const number = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 4 })

export default function OperationsPage({
  permissions,
  warehouses,
  selectedWarehouseId,
  onNotice,
}: {
  permissions: string[]
  warehouses: Warehouse[]
  selectedWarehouseId: string
  onNotice: (message: string) => void
}) {
  const can = (permission: string) => permissions.includes(permission)
  const tabs = [
    ...(can('inventory.transfer.read') || can('inventory.transfer.create') || can('inventory.transfer.submit') || can('inventory.transfer.approve') || can('inventory.transfer.post') ? [{ id: 'transfers', label: 'Transfer gudang' }] : []),
    ...(can('inventory.adjust.read') || can('inventory.adjust.create') || can('inventory.adjust.approve') || can('inventory.adjust.post') ? [{ id: 'adjustments', label: 'Penyesuaian stok' }] : []),
    ...(can('inventory.quarantine.read') || can('inventory.quarantine.action.create') || can('inventory.quarantine.action.approve') || can('inventory.quarantine.action.post') ? [{ id: 'quarantine', label: 'Karantina & barang rusak' }] : []),
    ...(can('sales_returns.create') || can('sales_returns.post') || can('sales_returns.read') ? [{ id: 'returns', label: 'Retur penjualan' }] : []),
  ]
  const [tab, setTab] = useState(tabs[0]?.id ?? 'transfers')
  const [products, setProducts] = useState<Product[]>([])
  const [balances, setBalances] = useState<Balance[]>([])
  const [transfers, setTransfers] = useState<Transfer[]>([])
  const [adjustments, setAdjustments] = useState<Adjustment[]>([])
  const [returns, setReturns] = useState<SalesReturn[]>([])
  const [quarantines, setQuarantines] = useState<Quarantine[]>([])
  const [quarantinedQuantity, setQuarantinedQuantity] = useState(0)
  const [shipments, setShipments] = useState<Shipment[]>([])
  const [selectedShipment, setSelectedShipment] = useState<Shipment | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [sourceWarehouseId, setSourceWarehouseId] = useState(selectedWarehouseId)
  const [destinationWarehouseId, setDestinationWarehouseId] = useState('')
  const [productId, setProductId] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [items, setItems] = useState<Array<{ product_id: number; quantity: number }>>([])
  const [balanceId, setBalanceId] = useState('')
  const [adjustmentType, setAdjustmentType] = useState<'ADD' | 'REDUCE'>('ADD')
  const [description, setDescription] = useState('')
  const [shipmentId, setShipmentId] = useState('')
  const [shipmentItemId, setShipmentItemId] = useState('')
  const [returnCondition, setReturnCondition] = useState<'RESTOCK' | 'DAMAGED'>('RESTOCK')
  const [returnReason, setReturnReason] = useState('')

  async function reload() {
    setError('')
    const tasks: Promise<void>[] = []
    if (can('master_data.read')) {
      tasks.push(apiRequest<{ data: Product[] }>('/products?per_page=100').then((res) => setProducts(res.data)))
    }
    if (can('inventory.read') && selectedWarehouseId) {
      tasks.push(apiRequest<{ data: Balance[] }>(`/inventory/summary?warehouse_id=${selectedWarehouseId}`).then((res) => {
        // The summary endpoint is for display; balance IDs are fetched separately for adjustment creation.
        setBalances(res.data as unknown as Balance[])
      }))
      tasks.push(apiRequest<{ data: Array<{ id: number; product_id: number; warehouse_id: number; quantity_on_hand: number; quantity_available: number }> }>(`/inventory/balances?warehouse_id=${selectedWarehouseId}&per_page=100`).then((res) => {
        setBalances(res.data.map((balance) => ({ ...balance, available: balance.quantity_available })))
      }))
    }
    if (can('inventory.transfer.read') || can('inventory.transfer.create') || can('inventory.transfer.submit') || can('inventory.transfer.approve') || can('inventory.transfer.post')) {
      tasks.push(apiRequest<{ data: Transfer[] }>(`/inventory/transfers?per_page=100${selectedWarehouseId ? `&warehouse_id=${selectedWarehouseId}` : ''}`).then((res) => setTransfers(res.data)))
    }
    if (can('inventory.adjust.read') || can('inventory.adjust.create') || can('inventory.adjust.approve') || can('inventory.adjust.post')) {
      tasks.push(apiRequest<{ data: Adjustment[] }>(`/inventory/adjustments?per_page=100${selectedWarehouseId ? `&warehouse_id=${selectedWarehouseId}` : ''}`).then((res) => setAdjustments(res.data)))
    }
    if (can('sales_returns.read') || can('sales_returns.create') || can('sales_returns.post')) {
      tasks.push(apiRequest<{ data: SalesReturn[] }>(`/sales-returns?per_page=100${selectedWarehouseId ? `&warehouse_id=${selectedWarehouseId}` : ''}`).then((res) => setReturns(res.data)))
    }
    if (can('sales_returns.create') && can('shipments.read')) {
      tasks.push(apiRequest<{ data: Shipment[] }>(`/shipments?status=POSTED&per_page=100${selectedWarehouseId ? `&warehouse_id=${selectedWarehouseId}` : ''}`).then((res) => setShipments(res.data)))
    }
    if (can('inventory.quarantine.read')) {
      tasks.push(apiRequest<{ data: Quarantine[]; quarantined_quantity: number }>(`/inventory/quarantines?per_page=100${selectedWarehouseId ? `&warehouse_id=${selectedWarehouseId}` : ''}`).then((res) => {
        setQuarantines(res.data)
        setQuarantinedQuantity(res.quarantined_quantity)
      }))
    }
    try { await Promise.all(tasks) } catch (failure) { setError(failure instanceof Error ? failure.message : 'Data workflow gagal dimuat.') }
  }

  useEffect(() => { void reload() }, [selectedWarehouseId, permissions.join('|')])
  useEffect(() => { setSourceWarehouseId(selectedWarehouseId) }, [selectedWarehouseId])

  useEffect(() => {
    if (!shipmentId) { setSelectedShipment(null); return }
    apiRequest<{ data: Shipment }>(`/shipments/${shipmentId}`)
      .then((response) => setSelectedShipment(response.data))
      .catch((failure: unknown) => setError(failure instanceof Error ? failure.message : 'Detail shipment gagal dimuat.'))
  }, [shipmentId])

  async function runAction(path: string, successMessage: string) {
    setBusy(true)
    setError('')
    try {
      await apiRequest(path, { method: 'POST' })
      onNotice(successMessage)
      await reload()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Tindakan gagal diproses.')
    } finally { setBusy(false) }
  }

  function addTransferItem() {
    const parsedProductId = Number(productId)
    const parsedQuantity = Number(quantity)
    if (!parsedProductId || !Number.isFinite(parsedQuantity) || parsedQuantity <= 0 || items.some((item) => item.product_id === parsedProductId)) {
      setError('Pilih produk unik dan masukkan jumlah yang valid.')
      return
    }
    setItems((current) => [...current, { product_id: parsedProductId, quantity: parsedQuantity }])
    setProductId('')
    setQuantity('1')
    setError('')
  }

  async function createTransfer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await apiRequest('/inventory/transfers', { method: 'POST', body: JSON.stringify({
        source_warehouse_id: Number(sourceWarehouseId),
        destination_warehouse_id: Number(destinationWarehouseId),
        reason: description,
        items,
      }) })
      setItems([]); setDescription(''); setDestinationWarehouseId('')
      onNotice('Draft transfer gudang berhasil dibuat.')
      await reload()
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Transfer gagal dibuat.') }
    finally { setBusy(false) }
  }

  async function createAdjustment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      await apiRequest('/inventory/adjustments', { method: 'POST', body: JSON.stringify({
        inventory_balance_id: Number(balanceId), adjustment_type: adjustmentType,
        quantity: Number(quantity), description,
      }) })
      setDescription(''); setQuantity('1')
      onNotice('Penyesuaian stok menunggu persetujuan.')
      await reload()
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Penyesuaian gagal dibuat.') }
    finally { setBusy(false) }
  }

  async function createReturn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      await apiRequest('/sales-returns', { method: 'POST', body: JSON.stringify({
        shipment_id: Number(shipmentId), reason: returnReason,
        items: [{ shipment_item_id: Number(shipmentItemId), quantity: Number(quantity), condition: returnCondition }],
      }) })
      setReturnReason(''); setQuantity('1'); setShipmentItemId('')
      onNotice('Draft retur penjualan berhasil dibuat.')
      await reload()
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Retur gagal dibuat.') }
    finally { setBusy(false) }
  }

  async function requestQuarantineDisposition(
    quarantineId: number,
    action: 'RELEASE' | 'SCRAP',
    reason: string,
  ): Promise<boolean> {
    setBusy(true)
    setError('')
    try {
      await apiRequest(`/inventory/quarantines/${quarantineId}/actions`, {
        method: 'POST',
        body: JSON.stringify({ action, reason }),
      })
      onNotice(action === 'RELEASE'
        ? 'Pengajuan pelepasan stok karantina dikirim untuk persetujuan.'
        : 'Pengajuan scrap stok karantina dikirim untuk persetujuan.')
      await reload()
      return true
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Pengajuan disposisi gagal dibuat.')
      return false
    } finally {
      setBusy(false)
    }
  }

  const productName = (id: number) => products.find((product) => product.id === id)?.name ?? `Produk #${id}`
  const warehouseName = (id: number) => warehouses.find((warehouse) => warehouse.id === id)?.code ?? `Gudang #${id}`
  const scopedBalances = balances.filter((balance) => balance.warehouse_id === Number(selectedWarehouseId))

  return <>
    <PageHeading eyebrow="OPERASIONAL" title="Workflow persediaan" description="Kelola transfer, penyesuaian stok, dan retur melalui tahapan transaksi yang tercatat." />
    <div className="erp-tab-strip mb-5 flex gap-2 overflow-x-auto pb-1">
      {tabs.map((item) => <button key={item.id} type="button" onClick={() => { setTab(item.id); setError('') }} className={`shrink-0 rounded-xl border px-4 py-2.5 text-sm font-semibold transition ${tab === item.id ? 'border-emerald-800 bg-emerald-800 text-white shadow-sm' : 'border-slate-200 bg-white text-slate-600 hover:border-emerald-200 hover:bg-emerald-50/60'}`}>{item.label}</button>)}
    </div>
    {error && <div role="alert" className="mb-4 rounded-lg border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}

    {tab === 'transfers' && <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
      {can('inventory.transfer.create') && <form onSubmit={(event) => void createTransfer(event)} className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-[0_2px_10px_-7px_rgba(15,23,42,0.18)] sm:p-5">
        <h2 className="font-semibold text-slate-900">Buat transfer</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <SelectField label="Gudang asal" value={sourceWarehouseId} onChange={setSourceWarehouseId} options={warehouses.map((w) => [String(w.id), `${w.code} · ${w.name}`])} />
          <SelectField label="Gudang tujuan" value={destinationWarehouseId} onChange={setDestinationWarehouseId} options={warehouses.filter((w) => String(w.id) !== sourceWarehouseId).map((w) => [String(w.id), `${w.code} · ${w.name}`])} />
          <SelectField label="Produk" value={productId} onChange={setProductId} options={products.map((p) => [String(p.id), `${p.sku} · ${p.name}`])} />
          <label className="text-xs font-semibold text-slate-600">Jumlah<input type="number" min="0.0001" step="0.0001" value={quantity} onChange={(e) => setQuantity(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
        </div>
        <button type="button" onClick={addTransferItem} className="mt-3 rounded-lg border border-emerald-200 px-3 py-2 text-xs font-semibold text-emerald-800">Tambah item</button>
        <ul className="mt-2 space-y-1 text-xs text-slate-600">{items.map((item) => <li key={item.product_id}>{productName(item.product_id)} · {number.format(item.quantity)}</li>)}</ul>
        <label className="mt-3 block text-xs font-semibold text-slate-600">Alasan<textarea required value={description} onChange={(e) => setDescription(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
        <button disabled={busy || !items.length} className="mt-4 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">Simpan draft</button>
      </form>}
      <WorkflowList title="Transfer gudang" rows={transfers.map((transfer) => <article key={transfer.id} className="flex flex-wrap items-center gap-3 border-b border-slate-100 px-5 py-4 last:border-0"><div className="min-w-[180px] flex-1"><p className="font-semibold text-slate-800">{transfer.transfer_number}</p><p className="mt-1 text-xs text-slate-500">{warehouseName(transfer.source_warehouse_id)} <ArrowRightLeft className="inline" size={13} /> {warehouseName(transfer.destination_warehouse_id)} · {transfer.items.length} item</p>{transfer.approved_by && <p className="mt-1 text-[10px] text-slate-400">Disetujui {transfer.approved_by_username ?? `#${transfer.approved_by}`} · {transfer.approved_at ? new Date(transfer.approved_at).toLocaleString('id-ID') : ''}</p>}{transfer.rejected_by && <p className="mt-1 text-[10px] text-rose-600">Ditolak {transfer.rejected_by_username ?? `#${transfer.rejected_by}`} · {transfer.rejected_at ? new Date(transfer.rejected_at).toLocaleString('id-ID') : ''}</p>}</div><StatusBadge status={transfer.status} />{transfer.status === 'DRAFT' && can('inventory.transfer.submit') && <ActionButton disabled={busy} label="Ajukan" onClick={() => void runAction(`/inventory/transfers/${transfer.id}/submit`, 'Transfer diajukan untuk persetujuan.')} />}{transfer.status === 'SUBMITTED' && can('inventory.transfer.approve') && <><ActionButton disabled={busy} label="Setujui" onClick={() => void runAction(`/inventory/transfers/${transfer.id}/approve`, 'Transfer disetujui.')} /><ActionButton disabled={busy} label="Tolak" onClick={() => void runAction(`/inventory/transfers/${transfer.id}/reject`, 'Transfer ditolak.')} /></>}{transfer.status === 'APPROVED' && can('inventory.transfer.post') && <ActionButton disabled={busy} label="Posting" onClick={() => void runAction(`/inventory/transfers/${transfer.id}/post`, 'Transfer diposting dan stok diperbarui.')} />}</article>)} />
    </div>}

    {tab === 'adjustments' && <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
      {can('inventory.adjust.create') && <form onSubmit={(event) => void createAdjustment(event)} className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-[0_2px_10px_-7px_rgba(15,23,42,0.18)] sm:p-5"><h2 className="font-semibold text-slate-900">Ajukan penyesuaian</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2"><SelectField label="Saldo produk" value={balanceId} onChange={setBalanceId} options={scopedBalances.map((b) => [String(b.id), `${productName(b.product_id)} · tersedia ${number.format(b.available)}`])} /><SelectField label="Jenis" value={adjustmentType} onChange={(v) => setAdjustmentType(v as 'ADD' | 'REDUCE')} options={[["ADD", "Tambah stok"], ["REDUCE", "Kurangi stok"]]} /><label className="text-xs font-semibold text-slate-600">Jumlah<input required type="number" min="0.0001" step="0.0001" value={quantity} onChange={(e) => setQuantity(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label></div>
        <label className="mt-3 block text-xs font-semibold text-slate-600">Keterangan<textarea required value={description} onChange={(e) => setDescription(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label><button disabled={busy || !balanceId} className="mt-4 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">Ajukan</button>
      </form>}
      <WorkflowList title="Penyesuaian stok" rows={adjustments.map((row) => <article key={row.id} className="flex flex-wrap items-center gap-3 border-b border-slate-100 px-5 py-4 last:border-0"><div className="min-w-[170px] flex-1"><p className="font-semibold text-slate-800">{row.code} · {productName(row.product_id)}</p><p className="mt-1 text-xs text-slate-500">{row.adjustment_type === 'ADD' ? '+' : '−'}{number.format(row.quantity)} · {row.description}</p></div><StatusBadge status={row.status} />{row.status === 'PENDING' && can('inventory.adjust.approve') && <><ActionButton disabled={busy} label="Setujui" onClick={() => void runAction(`/inventory/adjustments/${row.id}/approve`, 'Penyesuaian disetujui.')} /><ActionButton disabled={busy} label="Tolak" onClick={() => void runAction(`/inventory/adjustments/${row.id}/reject`, 'Penyesuaian ditolak.')} /></>}{row.status === 'APPROVED' && can('inventory.adjust.post') && <ActionButton disabled={busy} label="Posting" onClick={() => void runAction(`/inventory/adjustments/${row.id}/post`, 'Penyesuaian diposting ke stok.')} />}</article>)} />
    </div>}

    {tab === 'quarantine' && <section className="space-y-4">
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4">
        <p className="text-sm font-semibold text-amber-950">Stok karantina tidak dihitung sebagai stok tersedia.</p>
        <p className="mt-1 text-xs text-amber-900">Barang rusak dari retur menunggu keputusan. Pelepasan akan menambah stok tersedia; scrap akan menutup catatan tanpa memasukkan barang ke stok jual.</p>
        <p className="mt-2 text-xs font-semibold text-amber-950">Total kuantitas yang masih dikarantina: {number.format(quarantinedQuantity)}</p>
      </div>
      <WorkflowList title="Barang karantina" rows={quarantines.map((row) => {
        return <article key={row.id} className="border-b border-slate-100 px-5 py-4 last:border-0">
          <div className="flex flex-wrap items-start gap-3">
            <div className="min-w-[210px] flex-1">
              <p className="font-semibold text-slate-800">{row.product_name} · {number.format(row.quantity)}</p>
              <p className="mt-1 text-xs text-slate-500">{row.warehouse_code} · Retur {row.return_number} · {row.reason}</p>
            </div>
            <StatusBadge status={row.status} />
          </div>
          {row.actions.map((action) => <div key={action.id} className="mt-3 flex flex-wrap items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
            <span className="font-semibold">{action.action === 'RELEASE' ? 'Pelepasan' : 'Scrap'}</span>
            <StatusBadge status={action.status} />
            <span>{action.reason}</span>
            {action.reviewed_by_username && <span>· Ditinjau {action.reviewed_by_username}</span>}
            {action.posted_by_username && <span>· Diposting {action.posted_by_username}</span>}
            {action.status === 'PENDING' && can('inventory.quarantine.action.approve') && <>
              <ActionButton disabled={busy} label="Setujui" onClick={() => void runAction(`/inventory/quarantine-actions/${action.id}/approve`, 'Disposisi karantina disetujui.')} />
              <ActionButton disabled={busy} label="Tolak" onClick={() => void runAction(`/inventory/quarantine-actions/${action.id}/reject`, 'Disposisi karantina ditolak.')} />
            </>}
            {action.status === 'APPROVED' && can('inventory.quarantine.action.post') && <ActionButton disabled={busy} label="Posting keputusan" onClick={() => void runAction(`/inventory/quarantine-actions/${action.id}/post`, action.action === 'RELEASE' ? 'Barang dilepas ke stok tersedia.' : 'Barang dicatat sebagai scrap.')} />}
          </div>)}
          {row.status === 'QUARANTINED' && can('inventory.quarantine.action.create') && <QuarantineDispositionForm disabled={busy} onSubmit={(action, reason) => requestQuarantineDisposition(row.id, action, reason)} />}
        </article>
      })} />
    </section>}

    {tab === 'returns' && <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
      {can('sales_returns.create') && <form onSubmit={(event) => void createReturn(event)} className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-[0_2px_10px_-7px_rgba(15,23,42,0.18)] sm:p-5"><h2 className="font-semibold text-slate-900">Catat retur</h2><div className="mt-4 grid gap-3">
        <SelectField label="Shipment yang sudah diposting" value={shipmentId} onChange={(value) => { setShipmentId(value); setShipmentItemId('') }} options={shipments.map((shipment) => [String(shipment.id), `${shipment.code} · ${shipment.customer_name ?? ''}`])} />
        <SelectField label="Item shipment" value={shipmentItemId} onChange={setShipmentItemId} options={(selectedShipment?.items ?? []).map((item) => [String(item.id), `${item.product_name} · terkirim ${number.format(item.quantity)}`])} />
        <div className="grid gap-3 sm:grid-cols-2"><label className="text-xs font-semibold text-slate-600">Jumlah retur<input required type="number" min="0.0001" step="0.0001" value={quantity} onChange={(e) => setQuantity(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label><SelectField label="Kondisi" value={returnCondition} onChange={(v) => setReturnCondition(v as 'RESTOCK' | 'DAMAGED')} options={[["RESTOCK", "Layak dijual kembali"], ["DAMAGED", "Rusak"]]} /></div>
        <label className="text-xs font-semibold text-slate-600">Alasan<textarea required value={returnReason} onChange={(e) => setReturnReason(e.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
      </div><button disabled={busy || !shipmentItemId} className="mt-4 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">Simpan draft retur</button></form>}
      <WorkflowList title="Retur penjualan" rows={returns.map((row) => <article key={row.id} className="flex flex-wrap items-center gap-3 border-b border-slate-100 px-5 py-4 last:border-0"><div className="min-w-[180px] flex-1"><p className="font-semibold text-slate-800">{row.return_number} · {row.shipment_code}</p><p className="mt-1 text-xs text-slate-500">{row.items.map((item) => `${item.product_name} × ${number.format(item.quantity)} (${item.condition})`).join(', ')}</p></div><StatusBadge status={row.status} />{row.status === 'DRAFT' && can('sales_returns.post') && <ActionButton disabled={busy} label="Posting" onClick={() => void runAction(`/sales-returns/${row.id}/post`, 'Retur diposting. Barang layak jual ditambahkan kembali ke stok.')} />}</article>)} />
    </div>}
  </>
}

function QuarantineDispositionForm({
  disabled,
  onSubmit,
}: {
  disabled: boolean
  onSubmit: (action: 'RELEASE' | 'SCRAP', reason: string) => Promise<boolean>
}) {
  const [action, setAction] = useState<'RELEASE' | 'SCRAP'>('SCRAP')
  const [reason, setReason] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (await onSubmit(action, reason.trim())) setReason('')
  }

  return <form onSubmit={submit} className="mt-4 grid gap-2 rounded-lg border border-slate-200 bg-white p-3 sm:grid-cols-[180px_minmax(0,1fr)_auto]">
    <select value={action} onChange={(event) => setAction(event.target.value as 'RELEASE' | 'SCRAP')} className="rounded-lg border border-slate-200 px-3 py-2 text-xs">
      <option value="SCRAP">Ajukan scrap</option>
      <option value="RELEASE">Ajukan pelepasan ke stok</option>
    </select>
    <input required value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Alasan dan referensi pemeriksaan" className="rounded-lg border border-slate-200 px-3 py-2 text-xs" />
    <button disabled={disabled || !reason.trim()} className="rounded-lg bg-amber-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Ajukan keputusan</button>
  </form>
}

function SelectField({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[][] }) {
  return <label className="text-xs font-semibold text-slate-600">{label}<select required value={value} onChange={(event) => onChange(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal"><option value="">Pilih…</option>{options.map(([id, text]) => <option key={id} value={id}>{text}</option>)}</select></label>
}

function WorkflowList({ title, rows }: { title: string; rows: ReactNode[] }) {
  return <section className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-[0_2px_10px_-7px_rgba(15,23,42,0.18)]"><div className="border-b border-slate-100 px-4 py-4 sm:px-5"><h2 className="font-semibold text-slate-900">{title}</h2></div>{rows.length ? rows : <div className="p-6 text-sm text-slate-500">Belum ada transaksi.</div>}</section>
}

function ActionButton({ label, onClick, disabled }: { label: string; onClick: () => void; disabled: boolean }) {
  return <button type="button" disabled={disabled} onClick={onClick} className="rounded-lg border border-emerald-200 px-3 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-50 disabled:opacity-50">{label}</button>
}

function PageHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <div className="mb-5"><p className="text-[11px] font-bold tracking-[0.18em] text-emerald-700">{eyebrow}</p><h1 className="mt-1 text-2xl font-bold text-slate-900">{title}</h1><p className="mt-1 text-sm text-slate-500">{description}</p></div>
}

function StatusBadge({ status }: { status: string }) {
  const positive = ['POSTED', 'APPROVED', 'RESTOCK'].includes(status)
  const waiting = ['PENDING', 'SUBMITTED', 'DRAFT'].includes(status)
  const negative = ['REJECTED', 'CANCELLED'].includes(status)
  const labels: Record<string, string> = {
    QUARANTINED: 'Dikarantina',
    RELEASED: 'Dilepas ke stok',
    SCRAPPED: 'Di-scrap',
    PENDING: 'Menunggu persetujuan',
    APPROVED: 'Disetujui',
    REJECTED: 'Ditolak',
    POSTED: 'Diposting',
  }
  const label = labels[status] ?? status.replaceAll('_', ' ')
  return <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${positive || status === 'RELEASED' ? 'bg-emerald-50 text-emerald-700' : waiting || status === 'QUARANTINED' ? 'bg-amber-50 text-amber-700' : negative || status === 'SCRAPPED' ? 'bg-rose-50 text-rose-700' : 'bg-slate-100 text-slate-600'}`}>{label}</span>
}
