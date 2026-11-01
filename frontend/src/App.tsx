import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import {
  Activity,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Boxes,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  ClipboardList,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  Package,
  Pencil,
  Plus,
  Printer,
  Search,
  ShieldCheck,
  ShoppingCart,
  Truck,
  Users,
  Warehouse as WarehouseIcon,
  X,
} from 'lucide-react'
import {
  apiRequest,
  clearSession,
  getApiData,
  readSession,
  saveSession,
  type AuthSession,
} from './api'
import { printApiDocument, printDocument } from './print'
import type { PrintableDocument } from './print'
import OperationsPage from './OperationsPage'
import ReportsPage from './ReportsPage'

type PageId = 'dashboard' | 'sales' | 'inventory' | 'operations' | 'reports' | 'purchasing' | 'finance' | 'master' | 'audit' | 'access' | 'account'

interface WarehouseRecord {
  id: number
  code: string
  name: string
  is_active?: boolean
}

interface ManagedUser {
  id: number
  username: string
  email: string
  role: string
  is_active: boolean
  all_warehouses: boolean
  warehouse_ids: number[]
  last_login: string | null
  created_at: string | null
}

interface RoleRecord {
  code: string
  name: string
  description: string | null
  is_system: boolean
  permissions: string[]
}

interface PermissionRecord {
  code: string
  name: string
  module: string
  action: string
  warehouse_scoped: boolean
}

interface ProductRecord {
  id: number
  sku: string
  name: string
  category_id?: number | null
  unit_id?: number | null
  sales_price?: number | null
  min_stock: number
  is_active?: boolean
}

interface CategoryOption {
  id: number
  name: string
}

interface UnitOption {
  id: number
  name: string
  symbol?: string | null
}

interface PartnerRecord {
  id: number
  code: string
  name: string
  email?: string | null
  phone?: string | null
  address?: string | null
  is_active?: boolean
}

interface SalesOrderRecord {
  id: number
  code: string
  customer_id: number
  warehouse_id: number
  due_date: string
  status: string
  total_amount: number
  total_qty: number
  remaining_qty: number
  created_at: string | null
  created_by: number | null
  approved_by: number | null
  approved_by_username?: string | null
  approved_at: string | null
  rejected_by: number | null
  rejected_by_username?: string | null
  rejected_at: string | null
  items?: Array<{ id: number; product_id: number; quantity: number; unit_price: number; shipped_qty?: number; remaining_qty?: number }>
}

interface InventoryRecord {
  warehouse_code: string
  product_name: string
  on_hand: number
  reserved: number
  available: number
  average_cost: number
  total_value: number
}

interface PurchaseOrderRecord {
  id: number
  code: string
  supplier_id: number
  warehouse_id: number
  status: string
  total_amount: number
  order_date: string
  remaining_qty?: number
  supplier_name?: string
  notes?: string | null
  created_by?: number | null
  approved_by?: number | null
  approved_by_username?: string | null
  approved_at?: string | null
  rejected_by?: number | null
  rejected_by_username?: string | null
  rejected_at?: string | null
}

interface InvoiceRecord {
  id: number
  customer_id?: number
  warehouse_id?: number
  code: string
  customer_name: string
  due_date: string
  total_amount: number
  balance_due: number
  overdue_days?: number
  status?: string
  created_at?: string | null
}

interface VendorBillRecord {
  id: number
  code: string
  supplier_id: number
  total_amount: number
  amount_paid: number
  balance_due: number
  status: string
  created_at?: string | null
}

interface PrintableLine {
  id?: number
  product_id?: number
  sku?: string
  product_name?: string
  unit?: string | null
  quantity: number
  unit_price?: number
  total_price?: number
  unit_cost?: number
  received_qty?: number
  remaining_qty?: number
}

interface PrintableInvoice extends InvoiceRecord {
  status?: string
  created_at?: string | null
  shipment_code?: string
  sales_order_code?: string
  customer_code?: string
  customer_email?: string | null
  customer_phone?: string | null
  customer_address?: string | null
  warehouse_name?: string
  amount_paid: number
  items?: PrintableLine[]
}

interface ShipmentRecord {
  id: number
  code: string
  sales_order_id: number
  invoice_id?: number | null
  sales_order_code?: string
  customer_name?: string
  customer_phone?: string | null
  customer_address?: string | null
  warehouse_name?: string
  warehouse_code?: string
  status: string
  shipped_at: string | null
  items: PrintableLine[]
}

interface PurchaseOrderDetail extends PurchaseOrderRecord {
  supplier_code?: string
  supplier_email?: string | null
  supplier_phone?: string | null
  supplier_address?: string | null
  warehouse_name?: string
  warehouse_code?: string
  total_qty: number
  notes: string | null
  items: PrintableLine[]
}

interface GoodsReceiptRecord {
  id: number
  purchase_order_id?: number
  code: string
  purchase_order_code?: string
  supplier_name?: string
  supplier_code?: string
  supplier_address: string | null
  warehouse_name?: string
  warehouse_code?: string
  received_date: string
  status: string
  notes: string | null
  items: PrintableLine[]
}

interface CustomerPaymentRecord {
  id: number
  customer_id: number
  customer_code?: string
  customer_name?: string
  customer_email?: string | null
  customer_phone?: string | null
  customer_address?: string | null
  invoice_code?: string | null
  amount: number
  payment_method: string
  payment_date: string | null
  status: string
  allocations?: Array<{ invoice_code?: string; invoice_id?: number; amount: number }>
}

interface SupplierPaymentRecord {
  id: number
  code: string
  supplier_id: number
  supplier_code?: string
  supplier_name?: string
  supplier_email?: string | null
  supplier_phone?: string | null
  supplier_address?: string | null
  amount: number
  allocated_amount: number
  unallocated_amount: number
  payment_method: string
  payment_date: string | null
  status: string
  allocations?: Array<{ vendor_bill_code?: string; vendor_bill_id?: number; amount: number }>
}

interface PageResult<T> {
  data: T[]
  total: number
  page: number
  pages: number
}

interface Statistics {
  total_products: number
  total_warehouses: number
  total_customers: number
  total_sales_orders: number
  total_inventory_value: number | null
  low_stock_count: number
  recent_sales: Array<{
    id: number
    code: string
    status: string
    total_amount: number | null
    created_at: string | null
  }>
}

interface DashboardSummary {
  period: { from_date: string; to_date: string }
  total_sales_amount: number
  total_purchase_amount: number
  inventory_value: number
  low_stock_balance_count: number
  receivables_outstanding: number
  payables_outstanding: number
  cash_incoming: number
  cash_outgoing: number
  cash_net: number
  stock_distribution: Array<{ warehouse_id: number; warehouse_name: string; warehouse_code: string; quantity_on_hand: number; quantity_reserved: number; quantity_available: number; inventory_value: number }>
}

type CustomerRecord = PartnerRecord

const navigation: Array<{
  id: PageId
  label: string
  group: string
  icon: typeof LayoutDashboard
}> = [
  { id: 'dashboard', label: 'Ringkasan', group: 'WORKSPACE', icon: LayoutDashboard },
  { id: 'sales', label: 'Pesanan penjualan', group: 'OPERASIONAL', icon: ShoppingCart },
  { id: 'inventory', label: 'Persediaan', group: 'OPERASIONAL', icon: Boxes },
  { id: 'operations', label: 'Workflow operasional', group: 'OPERASIONAL', icon: ClipboardList },
  { id: 'reports', label: 'Laporan', group: 'ANALISIS', icon: FileText },
  { id: 'purchasing', label: 'Pembelian', group: 'OPERASIONAL', icon: Truck },
  { id: 'finance', label: 'Tagihan & pembayaran', group: 'FINANCE', icon: FileText },
  { id: 'master', label: 'Data master', group: 'DATA & REFERENSI', icon: Package },
  { id: 'audit', label: 'Audit log', group: 'PENGATURAN', icon: ClipboardList },
  { id: 'access', label: 'Pengguna & role', group: 'PENGATURAN', icon: ShieldCheck },
  { id: 'account', label: 'Akun & keamanan', group: 'AKUN', icon: Users },
]

const pagePermissions: Record<PageId, { codes: string[]; requireAll?: boolean }> = {
  dashboard: { codes: ['dashboard.read', 'reports.read'] },
  sales: { codes: ['sales_orders.read'] },
  inventory: { codes: ['inventory.read'] },
  operations: { codes: ['inventory.transfer.read', 'inventory.transfer.create', 'inventory.transfer.submit', 'inventory.transfer.approve', 'inventory.transfer.post', 'inventory.adjust.read', 'inventory.adjust.create', 'inventory.adjust.approve', 'inventory.adjust.post', 'inventory.quarantine.read', 'inventory.quarantine.action.create', 'inventory.quarantine.action.approve', 'inventory.quarantine.action.post', 'sales_returns.create', 'sales_returns.post', 'sales_returns.read'] },
  reports: { codes: ['reports.read'] },
  purchasing: { codes: ['purchase_orders.read'] },
  finance: { codes: ['finance.read', 'sales_invoices.read', 'customer_payments.read', 'supplier_payments.read'] },
  master: { codes: ['master_data.read', 'customers.read', 'suppliers.read'] },
  audit: { codes: ['audit_logs.read'] },
  access: { codes: ['users.manage', 'roles.manage'], requireAll: true },
  account: { codes: ['profile.read'] },
}

const roleNames: Record<string, string> = {
  admin: 'Admin',
  operator: 'Operator',
  viewer: 'Viewer',
  purchasing: 'Purchasing',
  warehouse: 'Warehouse',
  sales: 'Sales',
  finance: 'Finance',
  manager: 'Manager',
}

const currency = new Intl.NumberFormat('id-ID', {
  style: 'currency',
  currency: 'IDR',
  maximumFractionDigits: 0,
})

const numberFormat = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 2 })
const currentYear = new Date().getFullYear()

function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  return new Intl.DateTimeFormat('id-ID', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(value))
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Terjadi kesalahan yang tidak diketahui.'
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  return new Intl.DateTimeFormat('id-ID', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function requestPrint<T>(
  path: string,
  title: string,
  createDocument: (data: T) => PrintableDocument,
  onNotice: (message: string) => void,
) {
  void printApiDocument(path, title, createDocument)
    .catch((error: unknown) => onNotice(getErrorMessage(error)))
}

function printLines(items: PrintableLine[] | undefined, showPrice: boolean): string[][] {
  return (items ?? []).map((item, index) => [
    String(index + 1),
    [item.sku, item.product_name].filter(Boolean).join(' · ') || `Produk #${index + 1}`,
    numberFormat.format(item.quantity),
    item.unit ?? '—',
    ...(showPrice
      ? [
          currency.format(item.unit_price ?? item.unit_cost ?? 0),
          currency.format(item.total_price ?? (item.quantity * (item.unit_cost ?? 0))),
        ]
      : []),
  ])
}

function canAccessPage(page: PageId, permissions: string[] = []): boolean {
  const requirement = pagePermissions[page]
  return requirement.requireAll
    ? requirement.codes.every((code) => permissions.includes(code))
    : requirement.codes.some((code) => permissions.includes(code))
}

function firstAccessiblePage(permissions: string[] = []): PageId {
  return navigation.find((item) => canAccessPage(item.id, permissions))?.id ?? 'dashboard'
}

function App() {
  const [session, setSession] = useState<AuthSession | null>(() => readSession())
  const [showLogin, setShowLogin] = useState(false)
  const [page, setPage] = useState<PageId>(() => {
    const current = readSession()
    return firstAccessiblePage(current?.permissions)
  })
  const [warehouses, setWarehouses] = useState<WarehouseRecord[]>([])
  const [warehouseId, setWarehouseId] = useState(() => {
    const current = readSession()
    return current && !current.all_warehouses
      ? String(current.warehouse_ids[0] ?? '')
      : ''
  })
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [toast, setToast] = useState('')
  const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking')
  const [permissionSyncError, setPermissionSyncError] = useState('')

  const visibleNavigation = navigation.filter(
    (item) => session && canAccessPage(item.id, session.permissions),
  )

  useEffect(() => {
    const sessionId = session?.id
    if (!sessionId) return
    let active = true
    getApiData<Pick<AuthSession, 'id' | 'username' | 'email' | 'role' | 'permissions' | 'all_warehouses' | 'warehouse_ids'>>('/auth/me')
      .then(({ data }) => {
        if (!active) return
        if (
          !Array.isArray(data.permissions) ||
          typeof data.all_warehouses !== 'boolean' ||
          !Array.isArray(data.warehouse_ids) ||
          data.warehouse_ids.some((id) => typeof id !== 'number')
        ) {
          setPermissionSyncError(
            'Profil dan cakupan gudang tidak dapat disinkronkan. Restart backend, lalu muat ulang aplikasi.',
          )
          return
        }
        setPermissionSyncError('')
        setSession((current) => {
          if (!current || current.id !== sessionId) return current
          const updated = {
            ...current,
            id: data.id,
            username: data.username,
            email: data.email,
            role: data.role,
            permissions: data.permissions,
            all_warehouses: data.all_warehouses,
            warehouse_ids: data.warehouse_ids,
          }
          saveSession(updated)
          return updated
        })
        setWarehouseId((currentWarehouseId) => {
          if (data.all_warehouses) return currentWarehouseId
          if (data.warehouse_ids.includes(Number(currentWarehouseId))) {
            return currentWarehouseId
          }
          return String(data.warehouse_ids[0] ?? '')
        })
      })
      .catch((error: unknown) => {
        if (active && !Array.isArray(readSession()?.permissions)) {
          setPermissionSyncError(`Permission sesi tidak dapat dimuat. ${getErrorMessage(error)}`)
        }
      })
    return () => {
      active = false
    }
  }, [session?.id])

  useEffect(() => {
    if (!session) return
    let active = true
    getApiData<WarehouseRecord[]>('/warehouses?per_page=100')
      .then(({ data }) => {
        if (!active) return
        const permitted = session.all_warehouses
          ? data
          : data.filter((warehouse) => session.warehouse_ids.includes(warehouse.id))
        setWarehouses(permitted)
        const currentWarehouseIsPermitted = permitted.some(
          (warehouse) => String(warehouse.id) === warehouseId,
        )
        if (!currentWarehouseIsPermitted) {
          setWarehouseId(permitted.length > 0 ? String(permitted[0].id) : '')
        }
      })
      .catch((error: unknown) => {
        if (active) setToast(getErrorMessage(error))
      })
    return () => {
      active = false
    }
  }, [session, warehouseId])

  useEffect(() => {
    let active = true
    apiRequest<{ status: string }>('/health')
      .then(() => { if (active) setApiStatus('connected') })
      .catch(() => { if (active) setApiStatus('disconnected') })
    return () => { active = false }
  }, [session])

  useEffect(() => {
    if (!toast) return
    const timeout = window.setTimeout(() => setToast(''), 4500)
    return () => window.clearTimeout(timeout)
  }, [toast])

  async function signOut() {
    try {
      await apiRequest('/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: readSession()?.refresh_token }),
      })
    } catch (error) {
      setToast(`Sesi dihapus dari perangkat. ${getErrorMessage(error)}`)
    } finally {
      clearSession()
      setSession(null)
      setWarehouses([])
    }
  }

  if (!session) {
    if (!showLogin) {
      return <LandingPage onLogin={() => setShowLogin(true)} />
    }
    return (
      <LoginScreen
        onBack={() => setShowLogin(false)}
        onLogin={(value) => {
          saveSession(value)
          setSession(value)
          setWarehouseId(value.all_warehouses ? '' : String(value.warehouse_ids[0] ?? ''))
          setPage(firstAccessiblePage(value.permissions))
        }}
      />
    )
  }

  const activePage = visibleNavigation.some((item) => item.id === page)
    ? page
    : visibleNavigation[0]?.id ?? 'dashboard'
  const currentPage = navigation.find((item) => item.id === activePage)
  const selectedWarehouse = warehouses.find((warehouse) => String(warehouse.id) === warehouseId)
  const canSelectAll = session.all_warehouses

  return (
    <div className="app-shell min-h-screen bg-[#f5f7f6] text-slate-800">
      {sidebarOpen && (
        <button
          aria-label="Tutup navigasi"
          className="app-sidebar-overlay fixed inset-0 z-30 bg-slate-950/45 backdrop-blur-[2px] lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <aside
        id="main-navigation"
        aria-label="Navigasi utama"
        className={`app-sidebar fixed inset-y-0 left-0 z-40 flex w-[270px] flex-col text-slate-300 transition-transform lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="app-brand flex h-[76px] items-center gap-3 border-b border-white/10 px-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-300 text-[#102a21] shadow-[0_8px_22px_-10px_rgba(110,231,183,0.9)]">
            <Boxes size={22} strokeWidth={2.5} />
          </div>
          <div>
            <p className="text-[15px] font-bold tracking-wide text-white">DistribuFlow</p>
            <p className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.18em] text-slate-400">Enterprise Suite</p>
          </div>
          <button
            className="ml-auto rounded-lg p-2 text-slate-400 hover:bg-white/10 lg:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-label="Tutup menu"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-4 pt-6">
          <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-400/15 text-sm font-bold text-indigo-200">
                {session.username.slice(0, 1).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-white">{session.username}</p>
                <p className="mt-0.5 text-xs text-slate-400">{roleNames[session.role] ?? session.role}</p>
              </div>
              <ShieldCheck size={16} className="text-emerald-300" />
            </div>
          </div>
        </div>

        <nav className="mt-7 flex-1 space-y-6 overflow-y-auto px-3 pb-5">
          {Array.from(new Set(visibleNavigation.map((item) => item.group))).map((group) => (
            <div key={group}>
              <p className="mb-2 px-3 text-[10px] font-bold tracking-[0.17em] text-slate-500">{group}</p>
              <div className="space-y-1">
                {visibleNavigation.filter((item) => item.group === group).map((item) => {
                  const Icon = item.icon
                  const active = activePage === item.id
                  return (
                    <button
                      key={item.id}
                      onClick={() => {
                        setPage(item.id)
                        setSidebarOpen(false)
                      }}
                      className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium transition ${
                        active
                          ? 'bg-emerald-400 text-[#102a21] shadow-sm'
                          : 'text-slate-400 hover:bg-white/[0.06] hover:text-white'
                      }`}
                    >
                      <Icon size={17} strokeWidth={active ? 2.5 : 1.9} />
                      <span className="flex-1">{item.label}</span>
                      {item.id === 'sales' && (
                        <span className={`rounded-md px-1.5 py-0.5 text-[10px] ${active ? 'bg-black/10 text-[#102a21]' : 'bg-white/10 text-slate-400'}`}>SO</span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-white/10 p-4">
          <div className="mb-3 flex items-center gap-2 rounded-lg bg-white/[0.04] px-3 py-2.5 text-xs text-slate-400">
            <Activity size={15} className="text-emerald-300" />
            <span>ERP API</span>
            <span className={`ml-auto flex items-center gap-1.5 ${apiStatus === 'connected' ? 'text-emerald-300' : apiStatus === 'checking' ? 'text-amber-300' : 'text-rose-300'}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${apiStatus === 'connected' ? 'bg-emerald-400' : apiStatus === 'checking' ? 'bg-amber-400' : 'bg-rose-400'}`} />
              {apiStatus === 'connected' ? 'Terhubung' : apiStatus === 'checking' ? 'Memeriksa' : 'Terputus'}
            </span>
          </div>
          <button
            onClick={() => void signOut()}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-slate-400 transition hover:bg-white/[0.06] hover:text-white"
          >
            <LogOut size={17} />
            Keluar
          </button>
          <p className="mt-4 px-3 text-[10px] text-slate-600">DistribuFlow ERP · API v1</p>
        </div>
      </aside>

      <div className="app-main min-h-screen lg:pl-[270px]">
        <header className="app-topbar sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
          <div className="flex h-[70px] items-center gap-3 px-4 sm:px-7 lg:px-9">
            <button
              className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
              onClick={() => setSidebarOpen(true)}
              aria-label="Buka navigasi"
              aria-controls="main-navigation"
              aria-expanded={sidebarOpen}
            >
              <Menu size={20} />
            </button>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <span>Workspace</span>
                <ChevronRight size={13} />
                <span className="truncate font-medium text-slate-700">{currentPage?.label ?? 'DistribuFlow'}</span>
              </div>
            </div>
            <label className="hidden items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 md:flex">
              <WarehouseIcon size={15} className="shrink-0 text-slate-400" />
              <select
                value={warehouseId}
                onChange={(event) => setWarehouseId(event.target.value)}
                className="max-w-[190px] bg-transparent text-xs font-medium text-slate-700 outline-none"
                aria-label="Pilih gudang"
              >
                {canSelectAll && <option value="">Semua gudang</option>}
                {!canSelectAll && !warehouseId && <option value="">Pilih gudang</option>}
                {warehouses.map((warehouse) => (
                  <option key={warehouse.id} value={warehouse.id}>{warehouse.code} · {warehouse.name}</option>
                ))}
              </select>
              <ChevronDown size={14} className="text-slate-400" />
            </label>
            <button className="hidden rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 sm:block" aria-label="Bantuan">
              <CircleHelp size={18} />
            </button>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-50 text-sm font-bold text-indigo-700">
              {session.username.slice(0, 1).toUpperCase()}
            </div>
          </div>
          <div className="border-t border-slate-100 px-4 py-2 md:hidden">
            <label className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2">
              <WarehouseIcon size={15} className="text-slate-400" />
              <select
                value={warehouseId}
                onChange={(event) => setWarehouseId(event.target.value)}
                className="w-full bg-transparent text-xs text-slate-700 outline-none"
                aria-label="Pilih gudang"
              >
                {canSelectAll && <option value="">Semua gudang</option>}
                {!canSelectAll && !warehouseId && <option value="">Pilih gudang</option>}
                {warehouses.map((warehouse) => (
                  <option key={warehouse.id} value={warehouse.id}>{warehouse.code} · {warehouse.name}</option>
                ))}
              </select>
            </label>
          </div>
        </header>

        <main className="app-content mx-auto max-w-[1560px] px-4 py-5 sm:px-7 sm:py-7 xl:px-10">
          {permissionSyncError ? (
            <ErrorPanel message={permissionSyncError} />
          ) : session.permissions === undefined ? (
            <LoadingBar />
          ) : visibleNavigation.length === 0 ? (
            <EmptyState title="Belum ada akses" description="Akun ini belum memiliki permission untuk membuka modul. Hubungi administrator untuk meminta akses." />
          ) : null}
          {activePage === 'dashboard' && canAccessPage('dashboard', session.permissions) && <DashboardPage key={warehouseId} warehouseId={warehouseId} selectedWarehouse={selectedWarehouse} canSelectAllWarehouses={canSelectAll} canViewFinancialMetrics={session.permissions?.includes('finance.read') ?? false} permissions={session.permissions ?? []} onNavigate={setPage} />}
          {activePage === 'sales' && canAccessPage('sales', session.permissions) && (
            <SalesOrdersPage
              key={warehouseId}
              warehouseId={warehouseId}
              warehouses={warehouses}
              canViewShipments={session.permissions?.includes('shipments.read') ?? false}
              canCreate={session.permissions?.includes('sales_orders.create') ?? false}
              canSubmit={session.permissions?.includes('sales_orders.submit') ?? false}
              canReview={session.permissions?.includes('sales_orders.approve') ?? false}
              canCancel={session.permissions?.includes('sales_orders.cancel') ?? false}
              canCreateShipment={session.permissions?.includes('shipments.create') ?? false}
              canPostShipment={session.permissions?.includes('shipments.post') ?? false}
              onNotice={setToast}
            />
          )}
          {activePage === 'inventory' && canAccessPage('inventory', session.permissions) && (
            <InventoryPage key={warehouseId} warehouseId={warehouseId} selectedWarehouse={selectedWarehouse} />
          )}
          {activePage === 'operations' && canAccessPage('operations', session.permissions) && (
            <OperationsPage key={warehouseId} permissions={session.permissions ?? []} warehouses={warehouses} selectedWarehouseId={warehouseId} onNotice={setToast} />
          )}
          {activePage === 'reports' && canAccessPage('reports', session.permissions) && (
            <ReportsPage key={warehouseId} warehouses={warehouses} selectedWarehouseId={warehouseId} permissions={session.permissions ?? []} canSelectAllWarehouses={canSelectAll} />
          )}
          {activePage === 'purchasing' && canAccessPage('purchasing', session.permissions) && (
            <PurchasingPage
              key={warehouseId}
              warehouseId={warehouseId}
              warehouses={warehouses}
              canCreateOrders={session.permissions?.includes('purchase_orders.create') ?? false}
              canCancelOrders={session.permissions?.includes('purchase_orders.cancel') ?? false}
              canCreateReceipts={session.permissions?.includes('goods_receipts.create') ?? false}
              canPostReceipts={session.permissions?.includes('goods_receipts.post') ?? false}
              canViewReceipts={session.permissions?.includes('goods_receipts.read') ?? false}
              canViewPayments={session.permissions?.includes('supplier_payments.read') ?? false}
              canSubmit={session.permissions?.includes('purchase_orders.submit') ?? false}
              canReview={session.permissions?.includes('purchase_orders.approve') ?? false}
              onNotice={setToast}
            />
          )}
          {activePage === 'finance' && canAccessPage('finance', session.permissions) && (
            <FinancePage
              warehouseId={warehouseId}
              warehouses={warehouses}
              canSelectAllWarehouses={canSelectAll}
              onWarehouseChange={setWarehouseId}
              canViewFinancialMetrics={session.permissions?.includes('finance.read') ?? false}
              canViewInvoices={session.permissions?.includes('sales_invoices.read') ?? false}
              canCreateInvoices={session.permissions?.includes('sales_invoices.create') ?? false}
              canViewShipments={session.permissions?.includes('shipments.read') ?? false}
              canViewVendorBills={session.permissions?.includes('vendor_bills.read') ?? false}
              canViewPayments={session.permissions?.includes('customer_payments.read') ?? false}
              canViewSupplierPayments={session.permissions?.includes('supplier_payments.read') ?? false}
              canCreateCustomerPayments={session.permissions?.includes('customer_payments.create') ?? false}
              canPostCustomerPayments={session.permissions?.includes('customer_payments.post') ?? false}
              canAllocateCustomerPayments={session.permissions?.includes('customer_payments.allocate') ?? false}
              canCreateSupplierPayments={session.permissions?.includes('supplier_payments.create') ?? false}
              canPostSupplierPayments={session.permissions?.includes('supplier_payments.post') ?? false}
              canAllocateSupplierPayments={session.permissions?.includes('supplier_payments.allocate') ?? false}
              onNotice={setToast}
            />
          )}
          {activePage === 'master' && canAccessPage('master', session.permissions) && (
            <MasterDataPage
              permissions={session.permissions ?? []}
            />
          )}
          {activePage === 'access' && canAccessPage('access', session.permissions) && (
            <AccessManagementPage
              onNotice={setToast}
              onRolePermissionsSaved={(roleCode, permissions) => {
                if (session.role !== roleCode) return
                const updated = { ...session, permissions }
                saveSession(updated)
                setSession(updated)
                setPage(firstAccessiblePage(permissions))
              }}
            />
          )}
          {activePage === 'audit' && canAccessPage('audit', session.permissions) && <AuditLogsPage />}
          {activePage === 'account' && canAccessPage('account', session.permissions) && (
            <AccountSettingsPage
              session={session}
              warehouses={warehouses}
              onProfileUpdated={(updatedSession) => {
                saveSession(updatedSession)
                setSession(updatedSession)
                setToast('Pengaturan akun berhasil diperbarui.')
              }}
            />
          )}
        </main>
      </div>

      {toast && (
        <div role="status" className="fixed bottom-5 right-5 z-50 flex max-w-sm items-start gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-xl">
          <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-rose-500" />
          <span className="flex-1 text-slate-700">{toast}</span>
          <button onClick={() => setToast('')} aria-label="Tutup notifikasi" className="text-slate-400 hover:text-slate-700"><X size={16} /></button>
        </div>
      )}
    </div>
  )
}

function LandingPage({ onLogin }: { onLogin: () => void }) {
  const features = [
    {
      icon: ShoppingCart,
      number: '01',
      title: 'Pesanan penjualan',
      description: 'Catat pesanan pelanggan beserta produk dan jumlahnya. Stok yang dipesan dapat direservasi, lalu pesanan dipantau melalui proses persetujuan, pengiriman, pembuatan faktur, hingga penyelesaian.',
      tone: 'bg-emerald-50 text-emerald-700',
    },
    {
      icon: Boxes,
      number: '02',
      title: 'Persediaan terpantau',
      description: 'Pantau jumlah stok fisik, jumlah yang sudah dicadangkan, dan stok yang masih tersedia. Ringkasan persediaan, nilai barang, serta indikator stok minimum membantu tim mengetahui kondisi barang per gudang.',
      tone: 'bg-blue-50 text-blue-700',
    },
    {
      icon: Truck,
      number: '03',
      title: 'Alur pembelian',
      description: 'Susun pesanan pembelian kepada supplier, catat penerimaan barang ke gudang, dan lanjutkan pencatatan ke tagihan serta pembayaran supplier.',
      tone: 'bg-amber-50 text-amber-700',
    },
    {
      icon: FileText,
      number: '04',
      title: 'Keuangan & piutang',
      description: 'Tinjau faktur penjualan, sisa saldo yang perlu dibayar, dan tanggal jatuh tempo. Informasi ini membantu tim memantau piutang serta pembayaran pelanggan.',
      tone: 'bg-violet-50 text-violet-700',
    },
    {
      icon: WarehouseIcon,
      number: '05',
      title: 'Multi-gudang',
      description: 'Kelola persediaan pada beberapa gudang dan pilih lokasi yang ingin ditinjau. Data yang ditampilkan mengikuti cakupan gudang yang diberikan kepada pengguna.',
      tone: 'bg-cyan-50 text-cyan-700',
    },
    {
      icon: ShieldCheck,
      number: '06',
      title: 'Akses berbasis role',
      description: 'Pengguna masuk melalui autentikasi, lalu menu yang tersedia disesuaikan dengan perannya. Pembatasan cakupan gudang juga diterapkan agar akses data operasional lebih terarah.',
      tone: 'bg-rose-50 text-rose-700',
    },
  ]

  return (
    <div className="landing-page min-h-screen overflow-hidden bg-[#fbfcfa] text-slate-800">
      <header className="landing-nav sticky top-0 z-20 border-b border-white/70 bg-[#fbfcfa]/85 backdrop-blur-xl">
        <nav className="mx-auto flex h-[76px] max-w-7xl items-center justify-between px-5 sm:px-8">
          <a href="#home" className="flex items-center gap-2.5" aria-label="DistribuFlow beranda">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-700 text-white">
              <Boxes size={21} />
            </span>
            <span>
              <span className="block text-sm font-bold tracking-tight text-slate-900">DistribuFlow</span>
              <span className="block text-[9px] font-semibold uppercase tracking-[0.18em] text-slate-400">ERP · Enterprise Suite</span>
            </span>
          </a>
          <div className="hidden items-center gap-8 text-sm font-medium text-slate-500 md:flex">
            <a href="#fitur" className="transition hover:text-emerald-700">Fitur</a>
            <a href="#alur-kerja" className="transition hover:text-emerald-700">Alur kerja</a>
            <a href="#tentang" className="transition hover:text-emerald-700">Tentang proyek</a>
          </div>
          <button onClick={onLogin} className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-800">
            Masuk aplikasi <ArrowRight size={15} />
          </button>
        </nav>
      </header>

      <main>
        <section id="home" className="relative mx-auto grid max-w-7xl items-center gap-12 px-5 pb-20 pt-12 sm:px-8 sm:pb-24 sm:pt-16 lg:grid-cols-[1fr_0.95fr] lg:gap-8 lg:pb-28 lg:pt-20">
          <div className="landing-float absolute -left-56 top-8 -z-0 h-[480px] w-[480px] rounded-full bg-emerald-100/60 blur-3xl" />
          <div className="landing-copy relative z-[1]">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/80 px-3 py-1.5 text-xs font-semibold text-emerald-800 shadow-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Sistem ERP untuk operasional distribusi
            </div>
            <h1 className="mt-6 max-w-2xl text-[2.65rem] font-semibold leading-[1.08] tracking-[-0.045em] text-slate-950 sm:text-5xl lg:text-[3.65rem]">
              Operasional bisnis, <span className="bg-gradient-to-r from-emerald-700 via-emerald-600 to-teal-500 bg-clip-text text-transparent">lebih terkoneksi.</span>
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-slate-600 sm:text-lg sm:leading-8">
              DistribuFlow menghubungkan proses pengadaan barang, pengelolaan persediaan, pemenuhan pesanan pelanggan, hingga pencatatan keuangan. Setiap tim dapat mengikuti status transaksi dari awal sampai tindak lanjutnya dalam satu workspace.
            </p>
            <div className="mt-8 flex flex-col gap-3 min-[420px]:flex-row">
              <button onClick={onLogin} className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-700 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-900/10 transition hover:-translate-y-0.5 hover:bg-emerald-800">
                Jelajahi aplikasi <ArrowRight size={16} />
              </button>
              <a href="#fitur" className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-emerald-300 hover:text-emerald-800">
                Lihat fitur
              </a>
            </div>
            <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs font-medium text-slate-500">
              <span className="inline-flex items-center gap-1.5"><ShieldCheck size={14} className="text-emerald-700" /> Akses berbasis peran</span>
              <span className="inline-flex items-center gap-1.5"><Activity size={14} className="text-emerald-700" /> Alur operasional terintegrasi</span>
            </div>
          </div>

          <div className="landing-preview relative z-[1] mx-auto w-full max-w-[570px] lg:ml-auto">
            <div className="landing-orbit absolute -right-5 -top-7 h-32 w-32 rounded-full border border-emerald-200/70" />
            <div className="absolute -bottom-7 -left-6 h-28 w-28 rounded-full bg-amber-100/80 blur-2xl" />
            <div className="relative rounded-2xl border border-slate-200/80 bg-white p-3 shadow-[0_24px_80px_-30px_rgba(15,80,60,0.28)] sm:rounded-[22px] sm:p-4">
              <div className="flex items-center justify-between border-b border-slate-100 px-2 pb-3">
                <div className="flex items-center gap-2">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700"><LayoutDashboard size={16} /></span>
                  <div>
                    <p className="text-xs font-bold text-slate-800">Ringkasan operasional</p>
                    <p className="mt-0.5 text-[10px] text-slate-400">DistribuFlow workspace</p>
                  </div>
                </div>
                <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-semibold text-emerald-700">Dashboard</span>
              </div>
              <div className="grid grid-cols-2 gap-2.5 py-3 sm:grid-cols-3">
                {[
                  ['Pesanan aktif', 'Sales'],
                  ['Nilai persediaan', 'Inventory'],
                  ['Stok minimum', 'Monitoring'],
                ].map(([title, label], index) => (
                  <div key={title} className="rounded-xl border border-slate-100 bg-[#fcfdfc] p-3">
                    <p className="text-[10px] font-medium text-slate-400">{title}</p>
                    <div className="mt-2 flex items-end justify-between gap-1">
                      <span className="text-sm font-bold text-slate-800">{['Pesanan', 'Stok', 'Alert'][index]}</span>
                      <span className={`rounded-md px-1.5 py-1 text-[9px] font-semibold ${index === 2 ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'}`}>{label}</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="rounded-xl border border-slate-100 bg-[#fcfdfc] p-3 sm:p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-slate-800">Alur transaksi</p>
                    <p className="mt-1 text-[10px] text-slate-400">Dari order hingga pemenuhan</p>
                  </div>
                  <span className="text-[10px] font-medium text-slate-400">Workflow</span>
                </div>
                <div className="mt-5 flex items-center">
                  {[
                    ['01', 'Pesanan'],
                    ['02', 'Reservasi'],
                    ['03', 'Pengiriman'],
                    ['04', 'Faktur'],
                  ].map(([number, label], index) => (
                    <div key={number} className="flex min-w-0 flex-1 items-center last:flex-none">
                      <div className="flex flex-col items-center gap-2">
                        <span className={`flex h-8 w-8 items-center justify-center rounded-full text-[10px] font-bold ${index < 3 ? 'bg-emerald-700 text-white' : 'border border-slate-200 bg-white text-slate-400'}`}>{number}</span>
                        <span className="whitespace-nowrap text-[9px] font-medium text-slate-500 sm:text-[10px]">{label}</span>
                      </div>
                      {index < 3 && <span className="mb-5 mx-1 h-px flex-1 bg-slate-200 sm:mx-2" />}
                    </div>
                  ))}
                </div>
              </div>
              <div className="mt-2.5 flex items-center gap-2 rounded-xl bg-[#102a21] px-3 py-2.5 text-white">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/10"><ShieldCheck size={14} className="text-emerald-300" /></span>
                <p className="text-[10px] font-medium text-slate-200">Setiap tim melihat menu dan data sesuai hak aksesnya.</p>
                <ArrowUpRight size={14} className="ml-auto shrink-0 text-emerald-300" />
              </div>
            </div>
          </div>
        </section>

        <section id="fitur" className="border-y border-slate-200/70 bg-white py-16 sm:py-20">
          <div className="mx-auto max-w-7xl px-5 sm:px-8">
            <div className="mx-auto max-w-2xl text-center">
              <p className="text-[11px] font-bold uppercase tracking-[0.19em] text-emerald-700">Fitur utama</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">Semua proses penting, satu alur kerja</h2>
              <p className="mt-4 text-sm leading-6 text-slate-500 sm:text-base">Setiap modul menangani tanggung jawab yang berbeda, sekaligus berbagi konteks transaksi agar pekerjaan antarbagian lebih mudah ditelusuri.</p>
            </div>
            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:mt-12 lg:grid-cols-3">
              {features.map(({ icon: Icon, number, title, description, tone }, index) => (
                <article key={number} style={{ animationDelay: `${index * 90}ms` }} className="landing-reveal landing-feature group rounded-2xl border border-slate-200/80 bg-white p-5 sm:p-6">
                  <div className="flex items-start justify-between">
                    <span className={`landing-feature-icon flex h-11 w-11 items-center justify-center rounded-xl ${tone}`}><Icon size={20} /></span>
                    <span className="text-[11px] font-semibold tracking-wider text-slate-300">{number}</span>
                  </div>
                  <h3 className="mt-5 text-base font-semibold text-slate-900">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="alur-kerja" className="mx-auto max-w-7xl px-5 py-16 sm:px-8 sm:py-20">
          <div className="grid gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.19em] text-emerald-700">Alur kerja terhubung</p>
              <h2 className="mt-3 text-3xl font-semibold leading-tight tracking-tight text-slate-950 sm:text-4xl">Dari barang masuk sampai transaksi tercatat.</h2>
              <p className="mt-4 text-sm leading-7 text-slate-500 sm:text-base">
                Alur berikut menjelaskan bagaimana aktivitas antarbagian saling berkaitan. Tim dapat melihat konteks dan status proses tanpa memisahkan setiap transaksi ke dalam catatan yang berdiri sendiri.
              </p>
            </div>
            <ol className="relative space-y-3 before:absolute before:bottom-8 before:left-[19px] before:top-8 before:w-px before:bg-emerald-100">
              {[
                {
                  number: '01',
                  title: 'Siapkan data operasional',
                  text: 'Produk, pelanggan, supplier, dan gudang menjadi data dasar yang digunakan saat mencatat transaksi.',
                  icon: Package,
                },
                {
                  number: '02',
                  title: 'Lakukan pengadaan',
                  text: 'Purchase order mencatat barang yang dipesan dari supplier. Saat barang diterima, penerimaan dicatat untuk memperbarui persediaan gudang.',
                  icon: Truck,
                },
                {
                  number: '03',
                  title: 'Pantau ketersediaan persediaan',
                  text: 'Tim dapat membandingkan stok fisik, stok yang sudah direservasi, dan jumlah yang tersedia untuk memenuhi kebutuhan operasional.',
                  icon: Boxes,
                },
                {
                  number: '04',
                  title: 'Proses pesanan pelanggan',
                  text: 'Sales order mencatat kebutuhan pelanggan. Stok yang diperlukan dapat dicadangkan, lalu pesanan ditindaklanjuti melalui pengiriman dan pembuatan faktur.',
                  icon: ShoppingCart,
                },
                {
                  number: '05',
                  title: 'Tinjau tagihan dan pembayaran',
                  text: 'Faktur penjualan dan tagihan supplier memberi tim keuangan konteks untuk memantau saldo, jatuh tempo, serta pembayaran yang tercatat.',
                  icon: FileText,
                },
              ].map(({ number, title, text, icon: Icon }, index) => (
                <li key={number} style={{ animationDelay: `${index * 100}ms` }} className="landing-reveal relative flex gap-4 rounded-xl border border-slate-200/80 bg-white p-4 shadow-sm sm:gap-5 sm:p-5">
                  <span className="relative z-[1] flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-emerald-100 bg-emerald-50 text-emerald-700">
                    <Icon size={18} />
                  </span>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-baseline gap-x-2">
                      <span className="text-[10px] font-bold tracking-wider text-emerald-700">{number}</span>
                      <h3 className="text-sm font-semibold text-slate-900 sm:text-base">{title}</h3>
                    </div>
                    <p className="mt-1.5 text-xs leading-5 text-slate-500 sm:text-sm sm:leading-6">{text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="tentang" className="relative overflow-hidden border-y border-slate-200/70 bg-[#f4f8f5] py-16 text-slate-800 sm:py-20 lg:py-24">
          <div className="pointer-events-none absolute -right-40 -top-56 h-[520px] w-[520px] rounded-full border border-emerald-700/[0.07]" />
          <div className="pointer-events-none absolute -right-16 -top-32 h-[360px] w-[360px] rounded-full border border-emerald-700/[0.08]" />
          <div className="pointer-events-none absolute -bottom-48 left-[8%] h-[420px] w-[420px] rounded-full bg-emerald-200/40 blur-3xl" />
          <div className="relative mx-auto max-w-7xl px-5 sm:px-8">
            <div className="flex flex-col gap-5 border-b border-slate-200 pb-8 sm:flex-row sm:items-end sm:justify-between sm:pb-10">
              <div className="max-w-3xl">
                <p className="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.19em] text-emerald-700">
                  <span className="h-px w-6 bg-emerald-700" /> Tentang proyek
                </p>
                <h2 className="mt-4 text-3xl font-semibold leading-tight tracking-[-0.035em] text-slate-950 sm:text-4xl lg:text-5xl">
                  Merancang alur distribusi <span className="text-emerald-700">dalam satu sistem.</span>
                </h2>
              </div>
              <span className="w-fit rounded-full border border-emerald-800/15 bg-white/70 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-600">
                ERP Portfolio Project
              </span>
            </div>

            <div className="grid gap-8 pt-8 sm:pt-10 lg:grid-cols-[0.9fr_1.1fr] lg:gap-14">
              <div className="lg:pr-2">
                <p className="max-w-2xl text-base leading-8 text-slate-700 sm:text-lg sm:leading-8">
                  DistribuFlow adalah aplikasi ERP yang mengeksplorasi bagaimana proses distribusi dapat dikelola secara terstruktur—mulai dari data dasar dan pengadaan, dilanjutkan dengan pengelolaan stok, pemenuhan pesanan pelanggan, hingga pencatatan keuangan.
                </p>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-500 sm:mt-5 sm:text-base">
                  Proyek ini dirancang untuk memperlihatkan keterkaitan antarmodul dalam satu pengalaman kerja. Dashboard merangkum informasi operasional, sementara autentikasi berbasis peran dan cakupan gudang membantu menyesuaikan akses pengguna dengan tanggung jawabnya.
                </p>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-500 sm:mt-5 sm:text-base">
                  Antarmuka responsif dibangun menggunakan React, Vite, TypeScript, dan Tailwind CSS. Backend Python dengan Flask menyediakan REST API, menggunakan SQLAlchemy untuk akses data, dan memproses nominal transaksi dengan tipe desimal.
                </p>
              </div>

              <div className="grid content-start gap-3.5 sm:grid-cols-2">
                <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_2px_12px_-8px_rgba(15,23,42,0.18)] sm:col-span-2 sm:p-6">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">Cakupan sistem</p>
                      <p className="mt-1 text-xs text-slate-500">Modul yang menyusun alur operasional DistribuFlow.</p>
                    </div>
                    <ClipboardList size={16} className="text-emerald-700" />
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
                    {['Data master', 'Pembelian', 'Persediaan', 'Penjualan', 'Pengiriman', 'Faktur & pembayaran'].map((item) => (
                      <span key={item} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-[11px] font-medium text-slate-600">{item}</span>
                    ))}
                  </div>
                </div>
                <div className="flex min-h-[160px] flex-col rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_2px_12px_-8px_rgba(15,23,42,0.18)] sm:p-6">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-slate-900">Frontend</p>
                    <span className="rounded-lg bg-emerald-50 p-2 text-emerald-700"><LayoutDashboard size={15} /></span>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-500">Antarmuka responsif dan komponen interaktif untuk desktop maupun perangkat mobile.</p>
                  <div className="mt-auto flex flex-wrap gap-1.5 pt-4">
                    {['React', 'Vite', 'TypeScript', 'Tailwind'].map((item) => (
                      <span key={item} className="rounded-md bg-emerald-50 px-2 py-1 text-[10px] font-medium text-emerald-800">{item}</span>
                    ))}
                  </div>
                </div>
                <div className="flex min-h-[160px] flex-col rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_2px_12px_-8px_rgba(15,23,42,0.18)] sm:p-6">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-slate-900">Backend</p>
                    <span className="rounded-lg bg-emerald-50 p-2 text-emerald-700"><Activity size={15} /></span>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-500">REST API untuk autentikasi, otorisasi, transaksi, dan pengelolaan data ERP.</p>
                  <div className="mt-auto flex flex-wrap gap-1.5 pt-4">
                    {['Python', 'Flask', 'SQLAlchemy', 'Flask-Migrate'].map((item) => (
                      <span key={item} className="rounded-md bg-emerald-50 px-2 py-1 text-[10px] font-medium text-emerald-800">{item}</span>
                    ))}
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_2px_12px_-8px_rgba(15,23,42,0.18)] sm:col-span-2 sm:p-6">
                  <p className="text-sm font-semibold text-slate-900">Prinsip implementasi</p>
                  <div className="mt-4 grid gap-3 border-t border-slate-100 pt-4 sm:grid-cols-3 sm:gap-0">
                    {[
                      'Alur transaksi yang dapat ditelusuri',
                      'Akses sesuai role dan gudang',
                      'Presisi desimal untuk nominal uang',
                    ].map((principle, index) => (
                      <div key={principle} className={`flex items-start gap-2.5 text-xs leading-5 text-slate-600 ${index > 0 ? 'sm:border-l sm:border-slate-100 sm:pl-4' : ''} ${index < 2 ? 'sm:pr-4' : ''}`}>
                        <span className="mt-0.5 text-[10px] font-bold tracking-wider text-emerald-700">0{index + 1}</span>
                        <span>{principle}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-cta mx-5 mb-14 overflow-hidden rounded-2xl sm:mx-8 lg:mx-auto lg:mb-20 lg:max-w-7xl">
          <div className="flex flex-col gap-6 px-6 py-9 sm:px-10 sm:py-11 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-300">Siap melihat lebih dekat?</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-3xl">Jelajahi workspace DistribuFlow.</h2>
              <p className="mt-2 text-sm text-slate-300">Masuk dengan akun yang tersedia untuk melihat aplikasi.</p>
            </div>
            <button onClick={onLogin} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-emerald-400 px-5 py-3 text-sm font-semibold text-[#102a21] transition hover:bg-emerald-300">
              Masuk ke aplikasi <ArrowRight size={16} />
            </button>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200/70 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 px-5 py-6 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span className="font-semibold text-slate-600">DistribuFlow <span className="font-normal text-slate-400">· ERP Portfolio Project</span></span>
          <span>© {currentYear} DistribuFlow. Dibuat sebagai proyek portofolio.</span>
        </div>
      </footer>
    </div>
  )
}

function LoginScreen({ onLogin, onBack }: { onLogin: (session: AuthSession) => void; onBack: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const response = await apiRequest<{ data: AuthSession }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
      onLogin(response.data)
    } catch (failure) {
      setError(getErrorMessage(failure))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-white">
      <div className="relative hidden flex-1 flex-col justify-between overflow-hidden bg-[#101828] p-12 text-white lg:flex xl:p-16">
        <div className="absolute -right-28 -top-24 h-[460px] w-[460px] rounded-full border border-white/[0.06]" />
        <div className="absolute -right-8 -top-2 h-[330px] w-[330px] rounded-full border border-white/[0.08]" />
        <div className="absolute bottom-[-190px] left-[12%] h-[520px] w-[520px] rounded-full bg-emerald-400/[0.08] blur-3xl" />
        <div className="relative z-10 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-400 text-[#102a21]"><Boxes size={24} /></div>
          <div>
            <p className="font-bold tracking-wide">DistribuFlow</p>
            <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Enterprise Suite</p>
          </div>
        </div>
        <div className="relative z-10 max-w-xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1.5 text-xs text-emerald-200">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-300" /> Satu sistem untuk operasional Anda
          </div>
          <h1 className="text-4xl font-semibold leading-[1.15] tracking-tight xl:text-5xl">Kelola bisnis dengan alur yang lebih <span className="text-emerald-300">terarah.</span></h1>
          <p className="mt-5 max-w-md text-sm leading-6 text-slate-400">Pantau persediaan, pembelian, penjualan, dan keuangan dalam satu platform yang terintegrasi.</p>
          <div className="mt-10 grid max-w-md grid-cols-3 gap-3">
            {[
              ['01', 'Inventory'],
              ['02', 'Purchasing'],
              ['03', 'Finance'],
            ].map(([number, label]) => (
              <div key={number} className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
                <p className="text-[10px] text-slate-500">{number}</p>
                <p className="mt-1 text-xs font-medium text-slate-200">{label}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="relative z-10 text-xs text-slate-500">© {currentYear} DistribuFlow. All rights reserved.</p>
      </div>

      <div className="flex w-full items-center justify-center px-6 py-12 lg:w-[520px] lg:shrink-0 xl:w-[600px]">
        <div className="w-full max-w-[380px]">
          <button onClick={onBack} className="mb-8 inline-flex items-center gap-2 text-xs font-medium text-slate-500 transition hover:text-emerald-700">
            <ChevronLeft size={15} /> Kembali ke halaman utama
          </button>
          <div className="mb-10 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-400 text-[#102a21]"><Boxes size={22} /></div>
            <span className="font-bold text-slate-900">DistribuFlow</span>
          </div>
          <p className="text-sm font-semibold text-emerald-700">SELAMAT DATANG KEMBALI</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Masuk ke akun Anda</h2>
          <p className="mt-2 text-sm leading-6 text-slate-500">Gunakan akun yang diberikan administrator untuk melanjutkan.</p>
          <form onSubmit={(event) => void submit(event)} className="mt-8 space-y-5">
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">Username</span>
              <input
                autoComplete="username"
                required
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Masukkan username"
                className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-3 text-sm outline-none transition placeholder:text-slate-400 focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10"
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-700">Kata sandi</span>
              <input
                autoComplete="current-password"
                required
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Masukkan kata sandi"
                className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-3 text-sm outline-none transition placeholder:text-slate-400 focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10"
              />
            </label>
            {error && <p role="alert" className="rounded-lg border border-rose-100 bg-rose-50 px-3 py-2.5 text-sm text-rose-700">{error}</p>}
            <button disabled={loading} className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#087e63] px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#066b55] disabled:cursor-wait disabled:opacity-60">
              {loading ? 'Memverifikasi…' : 'Masuk ke workspace'}
              {!loading && <ArrowRight size={16} />}
            </button>
          </form>
          <div className="mt-7 flex items-center justify-center gap-2 text-xs text-slate-400">
            <ShieldCheck size={14} /> Akses dilindungi autentikasi dan role
          </div>
        </div>
      </div>
    </div>
  )
}

function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="app-page-heading mb-6 flex flex-col gap-4 sm:mb-7 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="text-[11px] font-bold tracking-[0.16em] text-emerald-700">{eyebrow}</p>
        <h1 className="mt-2 text-[clamp(1.5rem,2.4vw,1.85rem)] font-semibold tracking-tight text-slate-950">{title}</h1>
        <p className="mt-1.5 max-w-2xl text-[13px] leading-6 text-slate-500 sm:text-sm">{description}</p>
      </div>
      {action}
    </div>
  )
}

function StatCard({
  title,
  value,
  detail,
  icon: Icon,
  tone,
}: {
  title: string
  value: string
  detail: string
  icon: typeof Package
  tone: 'green' | 'blue' | 'amber' | 'purple'
}) {
  const colors = {
    green: 'bg-emerald-50 text-emerald-700',
    blue: 'bg-sky-50 text-sky-700',
    amber: 'bg-amber-50 text-amber-700',
    purple: 'bg-violet-50 text-violet-700',
  }
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-[0_2px_10px_-7px_rgba(15,23,42,0.18)] sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-slate-500 sm:text-[13px]">{title}</p>
          <p className="mt-3 text-2xl font-semibold tracking-tight text-slate-900 sm:text-[28px]">{value}</p>
        </div>
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${colors[tone]}`}><Icon size={19} /></div>
      </div>
      <p className="mt-3 flex items-center gap-1 text-xs text-slate-500">{detail}</p>
    </div>
  )
}

function DashboardPage({
  warehouseId,
  selectedWarehouse,
  canSelectAllWarehouses,
  canViewFinancialMetrics,
  permissions,
  onNavigate,
}: {
  warehouseId: string
  selectedWarehouse?: WarehouseRecord
  canSelectAllWarehouses: boolean
  canViewFinancialMetrics: boolean
  permissions: string[]
  onNavigate: (page: PageId) => void
}) {
  const [stats, setStats] = useState<Statistics | null>(null)
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const today = new Date()
  const localDate = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  const [fromDate, setFromDate] = useState(`${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-01`)
  const [toDate, setToDate] = useState(localDate)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const quickActions: Array<{ page: PageId; title: string; description: string; permission: string[]; icon: typeof Package }> = [
    { page: 'sales', title: 'Buat pesanan penjualan', description: 'Catat kebutuhan pelanggan dan pantau pemenuhan.', permission: ['sales_orders.create'], icon: ShoppingCart },
    { page: 'purchasing', title: 'Buat pesanan pembelian', description: 'Ajukan pembelian barang kepada supplier.', permission: ['purchase_orders.create'], icon: Truck },
    { page: 'operations', title: 'Kelola pekerjaan gudang', description: 'Terima barang, transfer, atau ajukan penyesuaian stok.', permission: ['inventory.transfer.create', 'inventory.adjust.create', 'goods_receipts.create', 'shipments.post'], icon: WarehouseIcon },
    { page: 'operations', title: 'Tinjau pengajuan', description: 'Periksa transaksi yang menunggu persetujuan Anda.', permission: ['inventory.transfer.approve', 'inventory.adjust.approve', 'purchase_orders.approve', 'sales_orders.approve'], icon: ClipboardList },
    { page: 'finance', title: 'Buka keuangan', description: 'Pantau invoice, tagihan, dan pembayaran.', permission: ['finance.read'], icon: FileText },
    { page: 'reports', title: 'Lihat laporan', description: 'Telusuri ringkasan dan ekspor laporan operasional.', permission: ['reports.read'], icon: Activity },
  ].filter((action) => canAccessPage(action.page, permissions) && action.permission.some((permission) => permissions.includes(permission)))

  useEffect(() => {
    let active = true
    if (!canSelectAllWarehouses && !warehouseId) {
      setError('Akun ini belum memiliki cakupan gudang. Minta Admin menetapkan gudang melalui Pengguna → Atur gudang.')
      setLoading(false)
      return () => { active = false }
    }
    setError('')
    const statsParams = new URLSearchParams()
    if (warehouseId) statsParams.set('warehouse_id', warehouseId)
    const summaryParams = new URLSearchParams({ from_date: fromDate, to_date: toDate })
    if (warehouseId) summaryParams.set('warehouse_id', warehouseId)
    const summaryRequest = canViewFinancialMetrics
      ? apiRequest<{ data: DashboardSummary }>(`/dashboard/summary?${summaryParams.toString()}`)
      : Promise.resolve(null)
    Promise.all([
      apiRequest<{ data: Statistics }>(`/statistics${statsParams.size ? `?${statsParams.toString()}` : ''}`),
      summaryRequest,
    ]).then(([statsResponse, summaryResponse]) => {
        if (active) {
          setStats(statsResponse.data)
          setSummary(summaryResponse?.data ?? null)
        }
      })
      .catch((failure: unknown) => {
        if (active) setError(getErrorMessage(failure))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [warehouseId, canSelectAllWarehouses, canViewFinancialMetrics, fromDate, toDate])

  return (
    <>
      <PageHeading
        eyebrow="OVERVIEW"
        title="Selamat datang kembali"
        description={`Pantau operasional bisnis${selectedWarehouse ? ` di ${selectedWarehouse.name}` : ''} hari ini.`}
      />
      {error ? <ErrorPanel message={error} /> : (
        <>
          {loading && <LoadingBar />}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard title="Total produk" value={stats ? numberFormat.format(stats.total_products) : '—'} detail="Produk aktif di katalog" icon={Package} tone="green" />
            <StatCard title="Pesanan penjualan" value={stats ? numberFormat.format(stats.total_sales_orders) : '—'} detail="Seluruh status pesanan" icon={ShoppingCart} tone="blue" />
            <StatCard title="Nilai persediaan" value={stats?.total_inventory_value != null ? currency.format(stats.total_inventory_value) : '—'} detail={canViewFinancialMetrics ? 'Berdasarkan rata-rata biaya' : 'Perlu akses keuangan'} icon={Boxes} tone="purple" />
            <StatCard title="Stok menipis" value={stats ? numberFormat.format(stats.low_stock_count) : '—'} detail="Di bawah batas minimum" icon={ArrowDownRight} tone="amber" />
          </div>

          {quickActions.length > 0 && <section className="mt-6" aria-labelledby="quick-actions-heading">
            <div className="mb-3 flex items-end justify-between gap-3">
              <div>
                <h2 id="quick-actions-heading" className="text-sm font-semibold text-slate-900">Mulai pekerjaan</h2>
                <p className="mt-1 text-xs text-slate-500">Akses cepat sesuai tugas dan izin akun Anda.</p>
              </div>
              <span className="hidden text-[11px] text-slate-400 sm:inline">Pilih aktivitas untuk membuka modul</span>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {quickActions.map(({ page: targetPage, title, description: actionDescription, icon: Icon }) => (
                <button key={`${targetPage}-${title}`} type="button" onClick={() => onNavigate(targetPage)} className="quick-action-card group flex min-h-[104px] items-center gap-3 rounded-xl border border-slate-200/80 bg-white p-4 text-left shadow-[0_2px_10px_-7px_rgba(15,23,42,0.18)] transition hover:-translate-y-0.5 hover:border-emerald-300 hover:shadow-md focus-visible:outline-emerald-500">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 transition group-hover:bg-emerald-100"><Icon size={18} /></span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold text-slate-800">{title}</span>
                    <span className="mt-1 block text-xs leading-5 text-slate-500">{actionDescription}</span>
                  </span>
                  <ArrowRight size={16} className="shrink-0 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-emerald-700" />
                </button>
              ))}
            </div>
          </section>}

          {canViewFinancialMetrics && <>
            <div className="mt-5 flex flex-col gap-3 rounded-xl border border-slate-200/80 bg-white p-4 sm:flex-row sm:items-end sm:justify-between"><div><h2 className="text-sm font-semibold text-slate-900">Ringkasan keuangan</h2><p className="mt-1 text-xs text-slate-500">Penjualan, pembelian, dan arus kas mengikuti periode; saldo piutang dan utang menunjukkan saldo berjalan.</p></div><div className="grid grid-cols-2 gap-2 sm:flex"><label className="text-[11px] font-semibold text-slate-600">Dari<input type="date" value={fromDate} max={toDate} onChange={(event) => setFromDate(event.target.value)} className="mt-1 block rounded-lg border border-slate-200 px-2.5 py-2 text-xs" /></label><label className="text-[11px] font-semibold text-slate-600">Sampai<input type="date" value={toDate} min={fromDate} onChange={(event) => setToDate(event.target.value)} className="mt-1 block rounded-lg border border-slate-200 px-2.5 py-2 text-xs" /></label></div></div>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <StatCard title="Total penjualan" value={summary ? currency.format(summary.total_sales_amount) : '—'} detail="Nilai invoice terbit dalam periode" icon={ArrowUpRight} tone="green" />
              <StatCard title="Total pembelian" value={summary ? currency.format(summary.total_purchase_amount) : '—'} detail="Nilai vendor bill terbit dalam periode" icon={Truck} tone="blue" />
              <StatCard title="Piutang berjalan" value={summary ? currency.format(summary.receivables_outstanding) : '—'} detail="Saldo invoice yang belum lunas" icon={ArrowDownRight} tone="amber" />
              <StatCard title="Utang berjalan" value={summary ? currency.format(summary.payables_outstanding) : '—'} detail="Saldo vendor bill yang belum lunas" icon={FileText} tone="purple" />
              <StatCard title="Kas masuk" value={summary ? currency.format(summary.cash_incoming) : '—'} detail="Pembayaran pelanggan diposting dalam periode" icon={ArrowDownRight} tone="green" />
              <StatCard title="Kas keluar" value={summary ? currency.format(summary.cash_outgoing) : '—'} detail="Pembayaran supplier diposting dalam periode" icon={ArrowUpRight} tone="amber" />
            </div>
            {summary && <section className="mt-5 overflow-hidden rounded-xl border border-slate-200/80 bg-white"><div className="border-b border-slate-100 px-5 py-4"><h2 className="text-sm font-semibold text-slate-900">Distribusi stok antar-gudang</h2><p className="mt-1 text-xs text-slate-500">Kas bersih periode {formatDate(summary.period.from_date)} – {formatDate(summary.period.to_date)}: <strong className="text-slate-700">{currency.format(summary.cash_net)}</strong></p></div><div className="overflow-x-auto"><table className="w-full min-w-[600px] text-left text-xs"><thead className="bg-slate-50 text-slate-500"><tr><th className="px-5 py-3">Gudang</th><th className="px-4 py-3 text-right">On hand</th><th className="px-4 py-3 text-right">Reservasi</th><th className="px-4 py-3 text-right">Tersedia</th><th className="px-5 py-3 text-right">Nilai stok</th></tr></thead><tbody className="divide-y divide-slate-100">{summary.stock_distribution.map((row) => <tr key={row.warehouse_id}><td className="px-5 py-3.5 font-medium text-slate-800">{row.warehouse_code} · {row.warehouse_name}</td><td className="px-4 py-3.5 text-right">{numberFormat.format(row.quantity_on_hand)}</td><td className="px-4 py-3.5 text-right">{numberFormat.format(row.quantity_reserved)}</td><td className="px-4 py-3.5 text-right font-semibold text-emerald-700">{numberFormat.format(row.quantity_available)}</td><td className="px-5 py-3.5 text-right">{currency.format(row.inventory_value)}</td></tr>)}</tbody></table>{summary.stock_distribution.length === 0 && <EmptyState title="Belum ada saldo gudang" description="Distribusi muncul setelah gudang memiliki saldo stok." />}</div></section>}
          </>}

          <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-[1.45fr_1fr]">
            <section className="overflow-hidden rounded-xl border border-slate-200/80 bg-white">
              <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
                <div>
                  <h2 className="text-sm font-semibold text-slate-900">Pesanan terbaru</h2>
                  <p className="mt-1 text-xs text-slate-500">Aktivitas sales order terakhir</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-2 text-slate-500"><Activity size={16} /></div>
              </div>
              {stats?.recent_sales.length ? (
                <div className="divide-y divide-slate-100">
                  {stats.recent_sales.map((order) => (
                    <div key={order.id} className="flex items-center gap-3 px-5 py-3.5">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700"><ShoppingCart size={16} /></div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-slate-800">{order.code}</p>
                        <p className="mt-1 text-xs text-slate-500">{formatDate(order.created_at)}</p>
                      </div>
                      {canViewFinancialMetrics && order.total_amount != null && <span className="hidden text-sm font-medium text-slate-700 sm:block">{currency.format(order.total_amount)}</span>}
                      <StatusBadge status={order.status} />
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title="Belum ada pesanan" description="Pesanan terbaru akan muncul di sini." />
              )}
              <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/60 px-5 py-3 text-xs text-slate-500">
                <span>{stats ? `${numberFormat.format(stats.total_sales_orders)} pesanan tercatat` : 'Memuat data…'}</span>
                <span className="flex items-center gap-1 text-emerald-700">Data diperbarui langsung <ArrowUpRight size={13} /></span>
              </div>
            </section>

            <section className="rounded-xl border border-slate-200/80 bg-white p-5">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-slate-900">Ringkasan operasional</h2>
                  <p className="mt-1 text-xs text-slate-500">Status ruang kerja Anda</p>
                </div>
                <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700">Live</span>
              </div>
              <div className="mt-6 space-y-5">
                <ProgressRow label="Produk terdaftar" value={stats?.total_products ?? 0} max={Math.max(stats?.total_products ?? 0, 1)} color="bg-emerald-500" />
                <ProgressRow label="Gudang operasional" value={stats?.total_warehouses ?? 0} max={Math.max(stats?.total_warehouses ?? 0, 1)} color="bg-blue-500" />
                <ProgressRow label="Pelanggan terdaftar" value={stats?.total_customers ?? 0} max={Math.max(stats?.total_customers ?? 0, 1)} color="bg-violet-500" />
              </div>
              <div className="mt-7 rounded-lg border border-amber-100 bg-amber-50/80 p-3.5">
                <div className="flex gap-3">
                  <div className="mt-0.5 text-amber-600"><Activity size={17} /></div>
                  <div>
                    <p className="text-xs font-semibold text-amber-900">Perhatian persediaan</p>
                    <p className="mt-1 text-xs leading-5 text-amber-800">
                      {stats ? `${stats.low_stock_count} produk berada di bawah batas stok minimum.` : 'Memuat status persediaan…'}
                    </p>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </>
      )}
    </>
  )
}

function ProgressRow({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const percentage = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-xs">
        <span className="text-slate-500">{label}</span>
        <span className="font-semibold text-slate-700">{numberFormat.format(value)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full ${color}`} style={{ width: `${percentage}%` }} /></div>
    </div>
  )
}

function SalesOrdersPage({
  warehouseId,
  warehouses,
  canViewShipments,
  canCreate,
  canSubmit,
  canReview,
  canCancel,
  canCreateShipment,
  canPostShipment,
  onNotice,
}: {
  warehouseId: string
  warehouses: WarehouseRecord[]
  canViewShipments: boolean
  canCreate: boolean
  canSubmit: boolean
  canReview: boolean
  canCancel: boolean
  canCreateShipment: boolean
  canPostShipment: boolean
  onNotice: (message: string) => void
}) {
  const [orders, setOrders] = useState<SalesOrderRecord[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [reload, setReload] = useState(0)
  const [shipments, setShipments] = useState<ShipmentRecord[]>([])
  const [shipmentError, setShipmentError] = useState('')
  const [reviewingOrderId, setReviewingOrderId] = useState<number | null>(null)
  const [editingOrder, setEditingOrder] = useState<SalesOrderRecord | null>(null)
  const [shipmentOrder, setShipmentOrder] = useState<SalesOrderRecord | null>(null)
  const [shipmentToEdit, setShipmentToEdit] = useState<ShipmentRecord | null>(null)

  useEffect(() => {
    let active = true
    const params = new URLSearchParams({ page: String(page), per_page: '10' })
    if (warehouseId) params.set('warehouse_id', warehouseId)
    if (status) params.set('status', status)
    apiRequest<PageResult<SalesOrderRecord>>(`/sales-orders?${params.toString()}`)
      .then((response) => {
        if (!active) return
        setOrders(response.data)
        setTotal(response.total)
        setPages(Math.max(response.pages, 1))
      })
      .catch((failure: unknown) => {
        if (active) setError(getErrorMessage(failure))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [page, status, warehouseId, reload])

  useEffect(() => {
    if (!canViewShipments) return
    let active = true
    const params = new URLSearchParams({ per_page: '100' })
    if (warehouseId) params.set('warehouse_id', warehouseId)
    apiRequest<PageResult<ShipmentRecord>>(`/shipments?${params.toString()}`)
      .then((response) => {
        if (active) {
          setShipments(response.data)
          setShipmentError('')
        }
      })
      .catch((failure: unknown) => {
        if (active) setShipmentError(getErrorMessage(failure))
      })
    return () => {
      active = false
    }
  }, [canViewShipments, warehouseId, reload])

  const filteredOrders = orders.filter((order) =>
    `${order.code} ${order.status}`.toLowerCase().includes(search.toLowerCase()),
  )

  async function reviewOrder(orderId: number, action: 'submit' | 'approve' | 'reject') {
    setReviewingOrderId(orderId)
    setError('')
    try {
      await apiRequest(`/sales-orders/${orderId}/${action}`, { method: 'POST' })
      onNotice(action === 'submit' ? 'Sales order diajukan untuk persetujuan.' : action === 'approve' ? 'Sales order disetujui.' : 'Sales order ditolak.')
      setReload((value) => value + 1)
    } catch (failure) {
      setError(getErrorMessage(failure))
    } finally {
      setReviewingOrderId(null)
    }
  }

  async function cancelOrder(order: SalesOrderRecord) {
    if (!window.confirm(`Batalkan ${order.code}? Reservasi stok yang belum dikirim akan dilepas.`)) return
    setReviewingOrderId(order.id)
    setError('')
    try {
      await apiRequest(`/sales-orders/${order.id}/cancel`, { method: 'POST' })
      onNotice('Sales order dibatalkan dan reservasi yang tersisa dilepas.')
      setReload((value) => value + 1)
    } catch (failure) { setError(getErrorMessage(failure)) }
    finally { setReviewingOrderId(null) }
  }

  async function postShipment(shipmentId: number) {
    setReviewingOrderId(shipmentId)
    try {
      await apiRequest(`/shipments/${shipmentId}/post`, { method: 'POST' })
      onNotice('Shipment berhasil diposting; stok dan status SO diperbarui.')
      setReload((value) => value + 1)
    } catch (failure) { setError(getErrorMessage(failure)) }
    finally { setReviewingOrderId(null) }
  }

  async function cancelShipment(shipment: ShipmentRecord) {
    if (!window.confirm(`Batalkan draft ${shipment.code}? Draft yang dibatalkan tidak mengurangi stok.`)) return
    setReviewingOrderId(shipment.id)
    try {
      await apiRequest(`/shipments/${shipment.id}/cancel`, { method: 'POST' })
      onNotice(`Draft ${shipment.code} dibatalkan.`)
      setReload((value) => value + 1)
    } catch (failure) { setShipmentError(getErrorMessage(failure)) }
    finally { setReviewingOrderId(null) }
  }

  return (
    <>
      <PageHeading
        eyebrow="SALES"
        title="Pesanan penjualan"
        description="Pantau pesanan, status pemenuhan, dan nilai transaksi penjualan."
        action={canCreate ? (
          <button
            onClick={() => setCreateOpen(true)}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#087e63] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#066b55]"
          >
            <Plus size={17} /> Buat pesanan
          </button>
        ) : undefined}
      />

      <section className="overflow-hidden rounded-xl border border-slate-200/80 bg-white">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Daftar sales order</h2>
            <p className="mt-1 text-xs text-slate-500">{numberFormat.format(total)} pesanan ditemukan</p>
          </div>
          <div className="flex flex-col gap-2 min-[420px]:flex-row">
            <label className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2">
              <Search size={15} className="text-slate-400" />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Cari pesanan…" className="w-full bg-transparent text-xs outline-none placeholder:text-slate-400 min-[420px]:w-36" />
            </label>
            <select value={status} onChange={(event) => { setError(''); setLoading(true); setStatus(event.target.value); setPage(1) }} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600 outline-none focus:border-emerald-500">
              <option value="">Semua status</option>
                  {['RESERVED', 'SUBMITTED', 'PARTIALLY_SHIPPED', 'SHIPPED', 'INVOICED', 'CLOSED', 'CANCELLED', 'REJECTED'].map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}
            </select>
          </div>
        </div>

        {error ? <div className="p-5"><ErrorPanel message={error} /></div> : (
          <>
            {loading && <LoadingBar />}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-[760px] text-left">
                <thead className="bg-slate-50/80 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-5 py-3.5">Nomor pesanan</th>
                    <th className="px-4 py-3.5">Pelanggan</th>
                    <th className="px-4 py-3.5">Gudang</th>
                    <th className="px-4 py-3.5">Jatuh tempo</th>
                    <th className="px-4 py-3.5 text-right">Nilai</th>
                    <th className="px-5 py-3.5">Status</th>
                    {(canReview || canSubmit || canCancel || canCreateShipment) && <th className="px-5 py-3.5">Tindakan</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredOrders.map((order) => (
                    <tr key={order.id} className="transition hover:bg-slate-50/70">
                      <td className="px-5 py-4">
                        <p className="text-sm font-semibold text-slate-800">{order.code}</p>
                        <p className="mt-1 text-[11px] text-slate-400">Dibuat {formatDate(order.created_at)}</p>
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-600">Pelanggan #{order.customer_id}</td>
                      <td className="px-4 py-4 text-sm text-slate-600">{warehouses.find((item) => item.id === order.warehouse_id)?.code ?? `Gudang #${order.warehouse_id}`}</td>
                      <td className="px-4 py-4 text-sm text-slate-600">{formatDate(order.due_date)}</td>
                      <td className="px-4 py-4 text-right text-sm font-semibold text-slate-800">{currency.format(order.total_amount)}</td>
                      <td className="px-5 py-4"><StatusBadge status={order.status} />{order.approved_by && <p className="mt-1 text-[10px] text-slate-400">Disetujui {order.approved_by_username ?? `#${order.approved_by}`} · {formatDateTime(order.approved_at)}</p>}{order.rejected_by && <p className="mt-1 text-[10px] text-rose-600">Ditolak {order.rejected_by_username ?? `#${order.rejected_by}`} · {formatDateTime(order.rejected_at)}</p>}</td>
                      {(canReview || canSubmit || canCancel || canCreateShipment) && <td className="px-5 py-4"><div className="flex flex-wrap gap-1.5">{canCreate && order.status === 'RESERVED' && !order.approved_by && <button type="button" onClick={() => setEditingOrder(order)} className="rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700">Ubah</button>}{order.status === 'RESERVED' && !order.approved_by && canSubmit && <button type="button" disabled={reviewingOrderId !== null} onClick={() => void reviewOrder(order.id, 'submit')} className="rounded-md border border-amber-200 px-2.5 py-1.5 text-xs font-semibold text-amber-800 disabled:opacity-50">Ajukan</button>}{canReview && order.status === 'SUBMITTED' && <><button type="button" disabled={reviewingOrderId !== null} onClick={() => void reviewOrder(order.id, 'approve')} className="rounded-md border border-emerald-200 px-2.5 py-1.5 text-xs font-semibold text-emerald-800 disabled:opacity-50">Setujui</button><button type="button" disabled={reviewingOrderId !== null} onClick={() => void reviewOrder(order.id, 'reject')} className="rounded-md border border-rose-200 px-2.5 py-1.5 text-xs font-semibold text-rose-700 disabled:opacity-50">Tolak</button></>}{canCancel && ['RESERVED', 'SUBMITTED', 'PARTIALLY_SHIPPED'].includes(order.status) && <button type="button" disabled={reviewingOrderId !== null} onClick={() => void cancelOrder(order)} className="rounded-md border border-rose-200 px-2.5 py-1.5 text-xs font-semibold text-rose-700">Batalkan</button>}{canCreateShipment && order.approved_by && ['RESERVED', 'PARTIALLY_SHIPPED'].includes(order.status) && order.remaining_qty > 0 && <button type="button" onClick={() => setShipmentOrder(order)} className="rounded-md border border-emerald-200 px-2.5 py-1.5 text-xs font-semibold text-emerald-800">Buat shipment</button>}</div></td>}
                    </tr>
                  ))}
                </tbody>
              </table>
              {!loading && filteredOrders.length === 0 && <EmptyState title="Tidak ada pesanan" description={search ? 'Coba kata kunci pencarian lain.' : 'Pesanan akan tampil di sini setelah dibuat.'} />}
            </div>

            <div className="divide-y divide-slate-100 md:hidden">
              {filteredOrders.map((order) => (
                <article key={order.id} className="space-y-3 px-4 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div><p className="text-sm font-semibold text-slate-800">{order.code}</p><p className="mt-1 text-xs text-slate-500">{formatDate(order.created_at)}</p>{order.approved_by && <p className="mt-1 text-[10px] text-slate-400">Disetujui {order.approved_by_username ?? `#${order.approved_by}`} · {formatDateTime(order.approved_at)}</p>}{order.rejected_by && <p className="mt-1 text-[10px] text-rose-600">Ditolak {order.rejected_by_username ?? `#${order.rejected_by}`} · {formatDateTime(order.rejected_at)}</p>}</div>
                    <StatusBadge status={order.status} />
                  </div>
                  {canSubmit && order.status === 'RESERVED' && !order.approved_by && <button type="button" disabled={reviewingOrderId !== null} onClick={() => void reviewOrder(order.id, 'submit')} className="rounded-md border border-amber-200 px-2.5 py-1.5 text-xs font-semibold text-amber-800 disabled:opacity-50">Ajukan</button>}
                  {canReview && order.status === 'SUBMITTED' && <div className="flex gap-2"><button type="button" disabled={reviewingOrderId !== null} onClick={() => void reviewOrder(order.id, 'approve')} className="rounded-md border border-emerald-200 px-2.5 py-1.5 text-xs font-semibold text-emerald-800 disabled:opacity-50">Setujui</button><button type="button" disabled={reviewingOrderId !== null} onClick={() => void reviewOrder(order.id, 'reject')} className="rounded-md border border-rose-200 px-2.5 py-1.5 text-xs font-semibold text-rose-700 disabled:opacity-50">Tolak</button></div>}
                  {canCreate && order.status === 'RESERVED' && !order.approved_by && <button type="button" onClick={() => setEditingOrder(order)} className="rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700">Ubah pesanan</button>}
                  {canCancel && ['RESERVED', 'SUBMITTED', 'PARTIALLY_SHIPPED'].includes(order.status) && <button type="button" disabled={reviewingOrderId !== null} onClick={() => void cancelOrder(order)} className="rounded-md border border-rose-200 px-2.5 py-1.5 text-xs font-semibold text-rose-700">Batalkan</button>}
                  {canCreateShipment && order.approved_by && ['RESERVED', 'PARTIALLY_SHIPPED'].includes(order.status) && order.remaining_qty > 0 && <button type="button" onClick={() => setShipmentOrder(order)} className="rounded-md border border-emerald-200 px-2.5 py-1.5 text-xs font-semibold text-emerald-800">Buat shipment</button>}
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div><p className="text-slate-400">Gudang</p><p className="mt-1 font-medium text-slate-700">{warehouses.find((item) => item.id === order.warehouse_id)?.code ?? `#${order.warehouse_id}`}</p></div>
                    <div><p className="text-slate-400">Jatuh tempo</p><p className="mt-1 font-medium text-slate-700">{formatDate(order.due_date)}</p></div>
                  </div>
                  <div className="flex items-center justify-between border-t border-slate-100 pt-3 text-xs"><span className="text-slate-500">Pelanggan #{order.customer_id}</span><span className="font-semibold text-slate-800">{currency.format(order.total_amount)}</span></div>
                </article>
              ))}
              {!loading && filteredOrders.length === 0 && <EmptyState title="Tidak ada pesanan" description={search ? 'Coba kata kunci pencarian lain.' : 'Pesanan akan tampil di sini setelah dibuat.'} />}
            </div>

            <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 sm:px-5">
              <p className="text-xs text-slate-500">Halaman {page} dari {pages}</p>
              <div className="flex gap-2">
                <button disabled={page <= 1} onClick={() => { setLoading(true); setError(''); setPage((value) => value - 1) }} className="rounded-lg border border-slate-200 p-2 text-slate-600 disabled:opacity-40" aria-label="Halaman sebelumnya"><ChevronLeft size={16} /></button>
                <button disabled={page >= pages} onClick={() => { setLoading(true); setError(''); setPage((value) => value + 1) }} className="rounded-lg border border-slate-200 p-2 text-slate-600 disabled:opacity-40" aria-label="Halaman berikutnya"><ChevronRight size={16} /></button>
              </div>
            </div>
          </>
        )}
      </section>

      {canViewShipments && (
        <section className="mt-5 overflow-hidden rounded-xl border border-slate-200/80 bg-white">
          <div className="border-b border-slate-100 px-5 py-4">
            <h2 className="text-sm font-semibold text-slate-900">Pengiriman & surat jalan</h2>
            <p className="mt-1 text-xs text-slate-500">{shipments.length} pengiriman terbaru</p>
          </div>
          {shipmentError ? <div className="p-5"><ErrorPanel message={shipmentError} /></div> : (
            <div className="divide-y divide-slate-100">
              {shipments.map((shipment) => (
                <div key={shipment.id} className="flex flex-wrap items-center gap-3 px-4 py-4 sm:px-5">
                  <div className="min-w-[140px] flex-1">
                    <p className="text-sm font-semibold text-slate-800">{shipment.code}</p>
                    <p className="mt-1 text-xs text-slate-500">{shipment.customer_name} · SO {shipment.sales_order_code}</p>
                  </div>
                  <StatusBadge status={shipment.status} />
                  {shipment.status === 'DRAFT' && canCreateShipment && <button type="button" onClick={() => setShipmentToEdit(shipment)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700">Ubah draft</button>}
                  {shipment.status === 'DRAFT' && canPostShipment && <button type="button" disabled={reviewingOrderId !== null} onClick={() => void postShipment(shipment.id)} className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Posting</button>}
                  {shipment.status === 'DRAFT' && canCreateShipment && <button type="button" disabled={reviewingOrderId !== null} onClick={() => void cancelShipment(shipment)} className="rounded-lg border border-rose-200 px-3 py-2 text-xs font-semibold text-rose-700 disabled:opacity-50">Batalkan draft</button>}
                  <button
                    type="button"
                    onClick={() => requestPrint(`/shipments/${shipment.id}`, 'Surat jalan', (data: ShipmentRecord) => ({
                      title: 'Surat Jalan',
                      code: data.code,
                      subtitle: `Status ${data.status}`,
                      details: [
                        ['Nomor sales order', data.sales_order_code ?? '—'],
                        ['Pelanggan', data.customer_name ?? '—'],
                        ['Alamat tujuan', data.customer_address ?? '—'],
                        ['Telepon', data.customer_phone ?? '—'],
                        ['Gudang asal', `${data.warehouse_code ?? '—'} · ${data.warehouse_name ?? '—'}`],
                        ['Waktu pengiriman', formatDateTime(data.shipped_at)],
                      ],
                      columns: ['No.', 'Produk', 'Jumlah', 'Satuan'],
                      rows: printLines(data.items, false),
                      signatures: ['Disiapkan oleh', 'Pengemudi', 'Diterima oleh'],
                    }), onNotice)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    <Printer size={14} /> Cetak surat jalan
                  </button>
                </div>
              ))}
              {shipments.length === 0 && <EmptyState title="Belum ada pengiriman" description="Pengiriman yang dibuat dari sales order akan muncul di sini." />}
            </div>
          )}
        </section>
      )}

      {createOpen && (
        <SalesOrderDialog
          warehouses={warehouses}
          defaultWarehouseId={warehouseId}
          onClose={() => setCreateOpen(false)}
          onCreated={() => {
            setCreateOpen(false)
            setPage(1)
            setLoading(true)
            setError('')
            setReload((value) => value + 1)
            onNotice('Sales order berhasil dibuat dan stok telah direservasi.')
          }}
        />
      )}
      {editingOrder && <SalesOrderDialog warehouses={warehouses} defaultWarehouseId={warehouseId} order={editingOrder} onClose={() => setEditingOrder(null)} onCreated={() => { setEditingOrder(null); setReload((value) => value + 1); onNotice('Sales order berhasil diperbarui; reservasi stok disesuaikan.') }} />}
      {(shipmentOrder || shipmentToEdit) && <ShipmentDialog orderId={shipmentToEdit?.sales_order_id ?? shipmentOrder!.id} shipment={shipmentToEdit ?? undefined} onClose={() => { setShipmentOrder(null); setShipmentToEdit(null) }} onCreated={() => { const editing = Boolean(shipmentToEdit); setShipmentOrder(null); setShipmentToEdit(null); setReload((value) => value + 1); onNotice(editing ? 'Draft shipment berhasil diperbarui.' : 'Shipment draft berhasil dibuat. Posting diperlukan untuk mengurangi stok.') }} />}
    </>
  )
}

function SalesOrderDialog({
  warehouses,
  defaultWarehouseId,
  order,
  onClose,
  onCreated,
}: {
  warehouses: WarehouseRecord[]
  defaultWarehouseId: string
  order?: SalesOrderRecord
  onClose: () => void
  onCreated: () => void
}) {
  const [customers, setCustomers] = useState<CustomerRecord[]>([])
  const [products, setProducts] = useState<ProductRecord[]>([])
  const [customerId, setCustomerId] = useState(order ? String(order.customer_id) : '')
  const [warehouseId, setWarehouseId] = useState(order ? String(order.warehouse_id) : defaultWarehouseId || String(warehouses[0]?.id ?? ''))
  const [dueDate, setDueDate] = useState(order?.due_date ?? '')
  const [productId, setProductId] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [unitPrice, setUnitPrice] = useState('')
  const [items, setItems] = useState<Array<{ product_id: number; quantity: number; unit_price: number }>>(order?.items?.map((item) => ({ product_id: item.product_id, quantity: item.quantity, unit_price: item.unit_price })) ?? [])
  const [loadingData, setLoadingData] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([
      getApiData<CustomerRecord[]>('/customers?per_page=100'),
      getApiData<ProductRecord[]>('/products?per_page=100'),
    ])
      .then(([customerResponse, productResponse]) => {
        if (!active) return
        setCustomers(customerResponse.data)
        setProducts(productResponse.data)
      })
      .catch((failure: unknown) => {
        if (active) setError(getErrorMessage(failure))
      })
      .finally(() => {
        if (active) setLoadingData(false)
      })
    return () => {
      active = false
    }
  }, [])

  function addItem() {
    const parsedProduct = Number(productId)
    const parsedQuantity = Number(quantity)
    const parsedUnitPrice = Number(unitPrice)
    if (
      !parsedProduct || !Number.isFinite(parsedQuantity) || parsedQuantity <= 0
      || unitPrice.trim() === '' || !Number.isFinite(parsedUnitPrice) || parsedUnitPrice < 0
    ) {
      setError('Pilih produk, masukkan jumlah, dan isi harga jual yang valid.')
      return
    }
    setError('')
    setItems((current) => [...current, {
      product_id: parsedProduct,
      quantity: parsedQuantity,
      unit_price: parsedUnitPrice,
    }])
    setProductId('')
    setQuantity('1')
    setUnitPrice('')
  }

  async function createOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    if (!items.length) {
      setError('Tambahkan setidaknya satu produk ke pesanan.')
      return
    }
    setSaving(true)
    try {
      await apiRequest(order ? `/sales-orders/${order.id}` : '/sales-orders', {
        method: order ? 'PATCH' : 'POST',
        body: JSON.stringify({
          customer_id: Number(customerId),
          warehouse_id: Number(warehouseId),
          due_date: dueDate,
          items,
        }),
      })
      onCreated()
    } catch (failure) {
      setError(getErrorMessage(failure))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 p-0 sm:items-center sm:p-5" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <form onSubmit={(event) => void createOrder(event)} className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl">
        <div className="flex items-start justify-between border-b border-slate-100 px-5 py-4 sm:px-6">
          <div><p className="text-[11px] font-bold tracking-widest text-emerald-700">SALES ORDER</p><h2 className="mt-1 text-lg font-semibold text-slate-900">{order ? `Ubah ${order.code}` : 'Buat pesanan penjualan'}</h2><p className="mt-1 text-xs text-slate-500">Stok tersedia akan divalidasi dan reservasi diperbarui saat disimpan.</p></div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Tutup dialog"><X size={18} /></button>
        </div>
        <div className="space-y-5 px-5 py-5 sm:px-6">
          {loadingData ? <LoadingBar /> : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <label className="text-xs font-semibold text-slate-600">Pelanggan
                <select required value={customerId} onChange={(event) => setCustomerId(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500">
                  <option value="">Pilih pelanggan</option>
                  {customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}</option>)}
                </select>
              </label>
              <label className="text-xs font-semibold text-slate-600">Gudang
                <select required value={warehouseId} onChange={(event) => setWarehouseId(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500">
                  {warehouses.map((warehouse) => <option key={warehouse.id} value={warehouse.id}>{warehouse.code} · {warehouse.name}</option>)}
                </select>
              </label>
              <label className="text-xs font-semibold text-slate-600 sm:col-span-2">Tanggal jatuh tempo
                <input type="date" required value={dueDate} onChange={(event) => setDueDate(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" />
              </label>
            </div>
          )}

          <div className="rounded-xl border border-slate-200 p-4">
            <p className="text-xs font-semibold text-slate-800">Item pesanan</p>
            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-[1fr_100px_150px_auto]">
              <select value={productId} onChange={(event) => {
                const selectedProduct = products.find((product) => product.id === Number(event.target.value))
                setProductId(event.target.value)
                setUnitPrice(selectedProduct?.sales_price == null ? '' : String(selectedProduct.sales_price))
              }} className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-emerald-500">
                <option value="">Pilih produk</option>
                {products.map((product) => <option key={product.id} value={product.id}>{product.sku} · {product.name}</option>)}
              </select>
              <input type="number" min="0.0001" step="0.0001" value={quantity} onChange={(event) => setQuantity(event.target.value)} aria-label="Jumlah produk" className="rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-emerald-500" />
              <input type="number" min="0" step="0.01" value={unitPrice} onChange={(event) => setUnitPrice(event.target.value)} aria-label="Harga jual per unit" placeholder="Harga jual" className="rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-emerald-500" />
              <button type="button" onClick={addItem} className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-emerald-200 px-3 py-2.5 text-xs font-semibold text-emerald-800 hover:bg-emerald-50"><Plus size={15} /> Tambah</button>
            </div>
            {items.length > 0 && (
              <div className="mt-3 divide-y divide-slate-100">
                {items.map((item, index) => {
                  const product = products.find((entry) => entry.id === item.product_id)
                  return <div key={`${item.product_id}-${index}`} className="flex items-center justify-between gap-3 py-2 text-xs"><span className="font-medium text-slate-700">{product?.name ?? `Produk #${item.product_id}`}</span><span className="flex items-center gap-3 text-slate-500">{numberFormat.format(item.quantity)} × {currency.format(item.unit_price)}<button type="button" onClick={() => setItems((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="text-rose-600 hover:text-rose-800">Hapus</button></span></div>
                })}
              </div>
            )}
            <p className="mt-3 text-[11px] leading-5 text-slate-500">Harga jual dicatat terpisah dari biaya persediaan. Ketersediaan stok diperiksa dan direservasi oleh server saat pesanan dibuat.</p>
          </div>
          {error && <p role="alert" className="rounded-lg border border-rose-100 bg-rose-50 px-3 py-2.5 text-sm text-rose-700">{error}</p>}
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-4 sm:px-6">
          <button type="button" onClick={onClose} className="rounded-lg px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100">Batal</button>
          <button disabled={saving || loadingData} className="rounded-lg bg-[#087e63] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#066b55] disabled:opacity-50">{saving ? 'Menyimpan…' : order ? 'Simpan perubahan' : 'Simpan pesanan'}</button>
        </div>
      </form>
    </div>
  )
}

function ShipmentDialog({ orderId, shipment, onClose, onCreated }: { orderId: number; shipment?: ShipmentRecord; onClose: () => void; onCreated: () => void }) {
  const [order, setOrder] = useState<SalesOrderRecord | null>(null)
  const [lines, setLines] = useState<Array<{ id: number; product_id: number; quantity: number; remaining_qty: number; product_name?: string }>>([])
  const [quantities, setQuantities] = useState<Record<number, string>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([
      apiRequest<{ data: SalesOrderRecord }>(`/sales-orders/${orderId}`),
      apiRequest<PageResult<ShipmentRecord>>(`/shipments?sales_order_id=${orderId}&per_page=100`),
    ]).then(([detail, shipmentResponse]) => {
      if (!active) return
      setOrder(detail.data)
      const reserved = new Map<number, number>()
      for (const shipment of shipmentResponse.data) {
        if (shipment.id === shipment?.id) continue
        if (!['DRAFT', 'POSTED'].includes(shipment.status)) continue
        for (const item of shipment.items ?? []) {
          const id = Number((item as PrintableLine & { sales_order_item_id?: number }).sales_order_item_id)
          if (id) reserved.set(id, (reserved.get(id) ?? 0) + item.quantity)
        }
      }
      setLines((detail.data.items ?? []).map((item) => ({
        id: item.id,
        product_id: item.product_id,
        quantity: item.quantity,
        remaining_qty: Math.max(0, item.quantity - (reserved.get(item.id) ?? 0)),
      })).filter((item) => item.remaining_qty > 0))
      if (shipment) {
        setQuantities(Object.fromEntries((shipment.items ?? []).map((item) => [Number((item as PrintableLine & { sales_order_item_id?: number }).sales_order_item_id), String(item.quantity)])))
      }
    }).catch((failure: unknown) => { if (active) setError(getErrorMessage(failure)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [orderId, shipment?.id])

  async function createShipment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const items = lines.map((line) => ({ sales_order_item_id: line.id, quantity: Number(quantities[line.id] || 0) })).filter((item) => item.quantity > 0)
    if (!items.length) { setError('Isi jumlah untuk setidaknya satu produk.'); return }
    setSaving(true)
    setError('')
    try {
      await apiRequest(shipment ? `/shipments/${shipment.id}` : `/sales-orders/${orderId}/shipments`, { method: shipment ? 'PATCH' : 'POST', body: JSON.stringify({ items }) })
      onCreated()
    } catch (failure) { setError(getErrorMessage(failure)) }
    finally { setSaving(false) }
  }

  return <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 p-0 sm:items-center sm:p-5" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><form onSubmit={(event) => void createShipment(event)} className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl"><div className="flex items-start justify-between border-b border-slate-100 px-5 py-4"><div><p className="text-[11px] font-bold tracking-widest text-emerald-700">PENGIRIMAN</p><h2 className="mt-1 text-lg font-semibold text-slate-900">{shipment ? 'Ubah draft shipment' : 'Buat shipment'} · {order?.code ?? shipment?.sales_order_code}</h2><p className="mt-1 text-xs text-slate-500">Perubahan hanya berlaku sebelum posting. Posting mengurangi stok gudang.</p></div><button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Tutup dialog"><X size={18} /></button></div><div className="space-y-3 p-5">{loading ? <LoadingBar /> : lines.length ? lines.map((line) => <label key={line.id} className="grid grid-cols-[minmax(0,1fr)_120px] items-center gap-3 rounded-lg border border-slate-100 p-3"><span><span className="block text-sm font-medium text-slate-800">{line.product_name ?? `Produk #${line.product_id}`}</span><span className="text-xs text-slate-500">Sisa termasuk draft ini {numberFormat.format(line.remaining_qty)}</span></span><input type="number" min="0" max={line.remaining_qty} step="any" value={quantities[line.id] ?? ''} onChange={(event) => setQuantities((current) => ({ ...current, [line.id]: event.target.value }))} placeholder="Jumlah" className="w-full rounded-md border border-slate-200 px-2.5 py-2 text-sm" /></label>) : !error && <EmptyState title="Tidak ada kuantitas tersisa" description="Semua jumlah sudah masuk shipment draft atau sudah dikirim." />}{error && <p role="alert" className="rounded-lg border border-rose-100 bg-rose-50 px-3 py-2.5 text-sm text-rose-700">{error}</p>}</div><div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-4"><button type="button" onClick={onClose} className="rounded-lg px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-100">Batal</button><button disabled={saving || loading || !lines.length} className="rounded-lg bg-[#087e63] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{saving ? 'Menyimpan…' : shipment ? 'Simpan perubahan' : 'Simpan draft'}</button></div></form></div>
}

function InventoryPage({
  warehouseId,
  selectedWarehouse,
}: {
  warehouseId: string
  selectedWarehouse?: WarehouseRecord
}) {
  const [rows, setRows] = useState<InventoryRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    const query = warehouseId ? `?warehouse_id=${warehouseId}` : ''
    apiRequest<{ data: InventoryRecord[] }>(`/inventory/summary${query}`)
      .then((response) => { if (active) setRows(response.data) })
      .catch((failure: unknown) => { if (active) setError(getErrorMessage(failure)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [warehouseId])

  const totalValue = rows.reduce((total, row) => total + row.total_value, 0)
  const totalAvailable = rows.reduce((total, row) => total + row.available, 0)

  return (
    <>
      <PageHeading
        eyebrow="INVENTORY"
        title="Persediaan"
        description="Pantau stok on-hand, reservasi, dan ketersediaan produk di gudang."
        action={
          <button
            type="button"
            disabled={loading || rows.length === 0}
            onClick={() => {
              try {
                printDocument({
                  title: 'Laporan Persediaan',
                  code: `STOK-${new Date().toISOString().slice(0, 10)}`,
                  details: [
                    ['Gudang', selectedWarehouse ? `${selectedWarehouse.code} · ${selectedWarehouse.name}` : warehouseId ? `Gudang #${warehouseId}` : 'Semua gudang'],
                    ['Tanggal laporan', formatDate(new Date().toISOString())],
                    ['Jumlah baris', numberFormat.format(rows.length)],
                  ],
                  columns: ['No.', 'SKU / Produk', 'Gudang', 'On hand', 'Reservasi', 'Tersedia', 'Biaya rata-rata', 'Nilai stok fisik'],
                  rows: rows.map((row, index) => [
                    String(index + 1),
                    row.product_name,
                    row.warehouse_code,
                    numberFormat.format(row.on_hand),
                    numberFormat.format(row.reserved),
                    numberFormat.format(row.available),
                    currency.format(row.average_cost),
                    currency.format(row.total_value),
                  ]),
                  totals: [
                    ['Total unit tersedia', numberFormat.format(totalAvailable)],
                    ['Total nilai persediaan', currency.format(totalValue)],
                  ],
                })
              } catch (failure) {
                setError(getErrorMessage(failure))
              }
            }}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            <Printer size={16} /> Cetak laporan
          </button>
        }
      />
      <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatCard title="Jenis produk" value={numberFormat.format(rows.length)} detail="Saldo produk di gudang aktif" icon={Package} tone="green" />
        <StatCard title="Stok tersedia" value={numberFormat.format(totalAvailable)} detail="On-hand dikurangi reservasi" icon={Boxes} tone="blue" />
        <StatCard title="Nilai stok fisik" value={currency.format(totalValue)} detail="On hand × biaya rata-rata" icon={Activity} tone="purple" />
      </div>
      <section className="overflow-hidden rounded-xl border border-slate-200/80 bg-white">
        <div className="border-b border-slate-100 px-5 py-4"><h2 className="text-sm font-semibold text-slate-900">Ringkasan stok</h2><p className="mt-1 text-xs text-slate-500">Nilai stok fisik dihitung dari on hand × biaya rata-rata, termasuk unit yang direservasi.</p></div>
        {error ? <div className="p-5"><ErrorPanel message={error} /></div> : <>
          {loading && <LoadingBar />}
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[650px] text-left">
              <thead className="bg-slate-50/80 text-[11px] font-semibold uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3.5">Produk</th><th className="px-4 py-3.5">Gudang</th><th className="px-4 py-3.5 text-right">On hand</th><th className="px-4 py-3.5 text-right">Reserved</th><th className="px-4 py-3.5 text-right">Available</th><th className="px-4 py-3.5 text-right">Biaya rata-rata</th><th className="px-5 py-3.5 text-right">Nilai stok fisik</th></tr></thead>
              <tbody className="divide-y divide-slate-100">{rows.map((row, index) => <tr key={`${row.warehouse_code}-${row.product_name}-${index}`} className="hover:bg-slate-50/70"><td className="px-5 py-4 text-sm font-semibold text-slate-800">{row.product_name}</td><td className="px-4 py-4 text-sm text-slate-600">{row.warehouse_code}</td><td className="px-4 py-4 text-right text-sm text-slate-600">{numberFormat.format(row.on_hand)}</td><td className="px-4 py-4 text-right text-sm text-slate-600">{numberFormat.format(row.reserved)}</td><td className="px-4 py-4 text-right text-sm font-semibold text-emerald-700">{numberFormat.format(row.available)}</td><td className="px-4 py-4 text-right text-sm text-slate-600">{currency.format(row.average_cost)}</td><td className="px-5 py-4 text-right text-sm font-semibold text-slate-800">{currency.format(row.total_value)}</td></tr>)}</tbody>
            </table>
          </div>
          <div className="divide-y divide-slate-100 md:hidden">{rows.map((row, index) => <article key={`${row.warehouse_code}-${row.product_name}-${index}`} className="px-4 py-4"><div className="flex items-start justify-between gap-3"><div><p className="text-sm font-semibold text-slate-800">{row.product_name}</p><p className="mt-1 text-xs text-slate-500">{row.warehouse_code}</p></div><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">{numberFormat.format(row.available)} tersedia</span></div><div className="mt-3 grid grid-cols-2 gap-3 text-xs"><div><p className="text-slate-400">On hand</p><p className="mt-1 font-medium">{numberFormat.format(row.on_hand)}</p></div><div><p className="text-slate-400">Reservasi</p><p className="mt-1 font-medium">{numberFormat.format(row.reserved)}</p></div><div><p className="text-slate-400">Biaya rata-rata</p><p className="mt-1 font-medium">{currency.format(row.average_cost)}</p></div><div><p className="text-slate-400">Nilai stok fisik</p><p className="mt-1 font-medium">{currency.format(row.total_value)}</p></div></div></article>)}</div>
          {!loading && rows.length === 0 && <EmptyState title="Belum ada saldo stok" description="Saldo persediaan untuk gudang ini belum tersedia." />}
        </>}
      </section>
    </>
  )
}

function PurchasingPage({
  warehouseId,
  warehouses,
  canCreateOrders,
  canCancelOrders,
  canCreateReceipts,
  canPostReceipts,
  canViewReceipts,
  canViewPayments,
  canSubmit,
  canReview,
  onNotice,
}: {
  warehouseId: string
  warehouses: WarehouseRecord[]
  canCreateOrders: boolean
  canCancelOrders: boolean
  canCreateReceipts: boolean
  canPostReceipts: boolean
  canViewReceipts: boolean
  canViewPayments: boolean
  canSubmit: boolean
  canReview: boolean
  onNotice: (message: string) => void
}) {
  const [orders, setOrders] = useState<PurchaseOrderRecord[]>([])
  const [receipts, setReceipts] = useState<GoodsReceiptRecord[]>([])
  const [supplierPayments, setSupplierPayments] = useState<SupplierPaymentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [receiptsError, setReceiptsError] = useState('')
  const [supplierPaymentsError, setSupplierPaymentsError] = useState('')
  const [reviewingOrderId, setReviewingOrderId] = useState<number | null>(null)
  const [reload, setReload] = useState(0)
  const [orderDialogOpen, setOrderDialogOpen] = useState(false)
  const [editingOrder, setEditingOrder] = useState<PurchaseOrderRecord | null>(null)
  const [receiptDialogOpen, setReceiptDialogOpen] = useState(false)
  const [receiptToEdit, setReceiptToEdit] = useState<GoodsReceiptRecord | null>(null)
  useEffect(() => {
    let active = true
    const query = warehouseId ? `?warehouse_id=${warehouseId}&per_page=100` : '?per_page=100'
    apiRequest<PageResult<PurchaseOrderRecord>>(`/purchase-orders${query}`)
      .then((response) => { if (active) setOrders(response.data) })
      .catch((failure: unknown) => { if (active) setError(getErrorMessage(failure)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [warehouseId, reload])

  useEffect(() => {
    if (!canViewReceipts) return
    let active = true
    const query = warehouseId ? `?warehouse_id=${warehouseId}&per_page=100` : '?per_page=100'
    apiRequest<PageResult<GoodsReceiptRecord>>(`/goods-receipts${query}`)
      .then((response) => { if (active) { setReceipts(response.data); setReceiptsError('') } })
      .catch((failure: unknown) => { if (active) setReceiptsError(getErrorMessage(failure)) })
    return () => { active = false }
  }, [warehouseId, canViewReceipts, reload])

  useEffect(() => {
    if (!canViewPayments) return
    let active = true
    const query = warehouseId ? `?warehouse_id=${warehouseId}&per_page=100` : '?per_page=100'
    apiRequest<PageResult<SupplierPaymentRecord>>(`/supplier-payments${query}`)
      .then((response) => { if (active) { setSupplierPayments(response.data); setSupplierPaymentsError('') } })
      .catch((failure: unknown) => { if (active) setSupplierPaymentsError(getErrorMessage(failure)) })
    return () => { active = false }
  }, [canViewPayments, warehouseId, reload])

  async function reviewPurchaseOrder(orderId: number, action: 'submit' | 'approve' | 'reject') {
    setReviewingOrderId(orderId)
    setError('')
    try {
      await apiRequest(`/purchase-orders/${orderId}/${action}`, { method: 'POST' })
      onNotice(action === 'submit' ? 'Purchase order diajukan untuk persetujuan.' : action === 'approve' ? 'Purchase order disetujui.' : 'Purchase order ditolak.')
      const query = warehouseId ? `?warehouse_id=${warehouseId}&per_page=100` : '?per_page=100'
      const response = await apiRequest<PageResult<PurchaseOrderRecord>>(`/purchase-orders${query}`)
      setOrders(response.data)
    } catch (failure) {
      setError(getErrorMessage(failure))
    } finally {
      setReviewingOrderId(null)
    }
  }

  async function cancelPurchaseOrder(order: PurchaseOrderRecord) {
    if (!window.confirm(`Batalkan purchase order ${order.code}?`)) return
    setReviewingOrderId(order.id)
    setError('')
    try {
      await apiRequest(`/purchase-orders/${order.id}/cancel`, { method: 'POST' })
      onNotice('Purchase order dibatalkan.')
      setReload((value) => value + 1)
    } catch (failure) {
      setError(getErrorMessage(failure))
    } finally {
      setReviewingOrderId(null)
    }
  }

  async function postGoodsReceipt(receipt: GoodsReceiptRecord) {
    setReviewingOrderId(receipt.id)
    setReceiptsError('')
    try {
      await apiRequest(`/goods-receipts/${receipt.id}/post`, { method: 'POST' })
      onNotice(`Penerimaan ${receipt.code} berhasil diposting.`)
      setReload((value) => value + 1)
    } catch (failure) {
      setReceiptsError(getErrorMessage(failure))
    } finally {
      setReviewingOrderId(null)
    }
  }

  async function cancelGoodsReceipt(receipt: GoodsReceiptRecord) {
    if (!window.confirm(`Batalkan draft penerimaan ${receipt.code}? Stok belum berubah sebelum posting.`)) return
    setReviewingOrderId(receipt.id)
    setReceiptsError('')
    try {
      await apiRequest(`/goods-receipts/${receipt.id}/cancel`, { method: 'POST' })
      onNotice(`Draft penerimaan ${receipt.code} dibatalkan.`)
      setReload((value) => value + 1)
    } catch (failure) { setReceiptsError(getErrorMessage(failure)) }
    finally { setReviewingOrderId(null) }
  }

  const receivableOrders = orders.filter((order) =>
    ['APPROVED', 'PARTIALLY_RECEIVED'].includes(order.status) && (order.remaining_qty ?? 0) > 0,
  )

  return (
    <>
      <PageHeading eyebrow="PURCHASING" title="Pembelian" description="Buat PO, ajukan persetujuan, lalu catat penerimaan barang untuk gudang yang ditugaskan." action={canCreateOrders ? <button type="button" onClick={() => { setEditingOrder(null); setOrderDialogOpen(true) }} className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800"><Plus size={16} /> Buat PO</button> : undefined} />
      <section className="overflow-hidden rounded-xl border border-slate-200/80 bg-white">
        <div className="border-b border-slate-100 px-5 py-4"><h2 className="text-sm font-semibold text-slate-900">Purchase order</h2><p className="mt-1 text-xs text-slate-500">{orders.length} pesanan pembelian terbaru</p></div>
        {error ? <div className="p-5"><ErrorPanel message={error} /></div> : <>
          {loading && <LoadingBar />}
          <div className="divide-y divide-slate-100">
            {orders.map((order) => <div key={order.id} className="flex flex-wrap items-center gap-3 px-5 py-4"><div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-700"><Truck size={17} /></div><div className="min-w-[120px] flex-1"><p className="text-sm font-semibold text-slate-800">{order.code}</p><p className="mt-1 text-xs text-slate-500">{order.supplier_name ?? `Supplier #${order.supplier_id}`} · {formatDate(order.order_date)}</p>{order.approved_by && <p className="mt-1 text-[10px] text-slate-400">Disetujui {order.approved_by_username ?? `#${order.approved_by}`} · {formatDateTime(order.approved_at)}</p>}{order.rejected_by && <p className="mt-1 text-[10px] text-rose-600">Ditolak {order.rejected_by_username ?? `#${order.rejected_by}`} · {formatDateTime(order.rejected_at)}</p>}</div><span className="mr-2 text-sm font-semibold text-slate-800">{currency.format(order.total_amount)}</span><StatusBadge status={order.status} />{canCreateOrders && order.status === 'DRAFT' && <button type="button" disabled={reviewingOrderId !== null} onClick={() => { setEditingOrder(order); setOrderDialogOpen(true) }} className="rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-50">Ubah</button>}{canSubmit && order.status === 'DRAFT' && <button type="button" disabled={reviewingOrderId !== null} onClick={() => void reviewPurchaseOrder(order.id, 'submit')} className="rounded-md border border-amber-200 px-2.5 py-1.5 text-xs font-semibold text-amber-800 disabled:opacity-50">Ajukan</button>}{canCancelOrders && ['DRAFT', 'SUBMITTED', 'APPROVED'].includes(order.status) && <button type="button" disabled={reviewingOrderId !== null} onClick={() => void cancelPurchaseOrder(order)} className="rounded-md border border-rose-200 px-2.5 py-1.5 text-xs font-semibold text-rose-700 disabled:opacity-50">Batalkan</button>}{canReview && order.status === 'SUBMITTED' && <div className="flex gap-2"><button type="button" disabled={reviewingOrderId !== null} onClick={() => void reviewPurchaseOrder(order.id, 'approve')} className="rounded-md border border-emerald-200 px-2.5 py-1.5 text-xs font-semibold text-emerald-800 disabled:opacity-50">Setujui</button><button type="button" disabled={reviewingOrderId !== null} onClick={() => void reviewPurchaseOrder(order.id, 'reject')} className="rounded-md border border-rose-200 px-2.5 py-1.5 text-xs font-semibold text-rose-700 disabled:opacity-50">Tolak</button></div>}<button type="button" onClick={() => requestPrint(`/purchase-orders/${order.id}${warehouseId ? `?warehouse_id=${encodeURIComponent(warehouseId)}` : ''}`, 'Purchase order', (data: PurchaseOrderDetail) => ({ title: 'Purchase Order', code: data.code, subtitle: `Status ${data.status}`, details: [['Supplier', `${data.supplier_code} · ${data.supplier_name}`], ['Alamat supplier', data.supplier_address ?? '—'], ['Email / telepon', [data.supplier_email, data.supplier_phone].filter(Boolean).join(' · ')], ['Tanggal pesanan', formatDate(data.order_date)], ['Gudang tujuan', `${data.warehouse_code} · ${data.warehouse_name}`]], columns: ['No.', 'Produk', 'Jumlah', 'Satuan', 'Harga satuan', 'Subtotal'], rows: printLines(data.items, true), totals: [['Total kuantitas', numberFormat.format(data.total_qty)], ['Total pesanan', currency.format(data.total_amount)]], note: data.notes ?? undefined, signatures: ['Dibuat oleh', 'Disetujui oleh'], }), onNotice)} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"><Printer size={14} /> Cetak PO</button></div>)}
            {!loading && orders.length === 0 && <EmptyState title="Belum ada purchase order" description="Purchase order akan tampil setelah dibuat." />}
          </div>
        </>}
      </section>
      {canViewReceipts && (
        <section className="mt-5 overflow-hidden rounded-xl border border-slate-200/80 bg-white">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4"><div><h2 className="text-sm font-semibold text-slate-900">Penerimaan barang</h2><p className="mt-1 text-xs text-slate-500">{receipts.length} bukti penerimaan terbaru</p></div>{canCreateReceipts && <button type="button" disabled={receivableOrders.length === 0} onClick={() => setReceiptDialogOpen(true)} className="inline-flex items-center gap-2 rounded-lg border border-emerald-200 px-3 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-50"><Plus size={15} /> Catat penerimaan</button>}</div>
          {receiptsError ? <div className="p-5"><ErrorPanel message={receiptsError} /></div> : <div className="divide-y divide-slate-100">
            {receipts.map((receipt) => <div key={receipt.id} className="flex flex-wrap items-center gap-3 px-4 py-4 sm:px-5"><div className="min-w-[140px] flex-1"><p className="text-sm font-semibold text-slate-800">{receipt.code}</p><p className="mt-1 text-xs text-slate-500">{receipt.supplier_name ?? 'Supplier'} · PO {receipt.purchase_order_code ?? '—'} · {formatDate(receipt.received_date)}</p></div><StatusBadge status={receipt.status} />{canCreateReceipts && receipt.status === 'DRAFT' && <button type="button" onClick={() => setReceiptToEdit(receipt)} className="rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700">Ubah draft</button>}{canPostReceipts && receipt.status === 'DRAFT' && <button type="button" disabled={reviewingOrderId !== null} onClick={() => void postGoodsReceipt(receipt)} className="rounded-md border border-emerald-200 px-2.5 py-1.5 text-xs font-semibold text-emerald-800 disabled:opacity-50">Posting</button>}{canCreateReceipts && receipt.status === 'DRAFT' && <button type="button" disabled={reviewingOrderId !== null} onClick={() => void cancelGoodsReceipt(receipt)} className="rounded-md border border-rose-200 px-2.5 py-1.5 text-xs font-semibold text-rose-700 disabled:opacity-50">Batalkan draft</button>}<button type="button" onClick={() => requestPrint(`/goods-receipts/${receipt.id}${warehouseId ? `?warehouse_id=${encodeURIComponent(warehouseId)}` : ''}`, 'Bukti penerimaan barang', (data: GoodsReceiptRecord) => ({ title: 'Bukti Penerimaan Barang', code: data.code, subtitle: `Status ${data.status}`, details: [['Purchase order', data.purchase_order_code ?? '—'], ['Supplier', `${data.supplier_code ?? '—'} · ${data.supplier_name ?? '—'}`], ['Alamat supplier', data.supplier_address ?? '—'], ['Gudang penerima', `${data.warehouse_code ?? '—'} · ${data.warehouse_name ?? '—'}`], ['Tanggal diterima', formatDate(data.received_date)]], columns: ['No.', 'Produk', 'Jumlah diterima', 'Satuan', 'Biaya satuan'], rows: printLines(data.items, false).map((row, index) => [row[0], row[1], row[2], row[3], currency.format(data.items?.[index]?.unit_cost ?? 0)]), note: data.notes ?? undefined, signatures: ['Petugas penerima', 'Perwakilan supplier'], }), onNotice)} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"><Printer size={14} /> Cetak bukti</button></div>)}
            {receipts.length === 0 && <EmptyState title="Belum ada penerimaan" description="Bukti penerimaan barang akan tampil di sini." />}
          </div>}
        </section>
      )}
      {canViewPayments && (
        <section className="mt-5 overflow-hidden rounded-xl border border-slate-200/80 bg-white">
          <div className="border-b border-slate-100 px-5 py-4"><h2 className="text-sm font-semibold text-slate-900">Pembayaran supplier</h2><p className="mt-1 text-xs text-slate-500">{supplierPayments.length} transaksi pembayaran terbaru</p></div>
          {supplierPaymentsError ? <div className="p-5"><ErrorPanel message={supplierPaymentsError} /></div> : <div className="divide-y divide-slate-100">
            {supplierPayments.map((payment) => <div key={payment.id} className="flex flex-wrap items-center gap-3 px-4 py-4 sm:px-5"><div className="min-w-[140px] flex-1"><p className="text-sm font-semibold text-slate-800">{payment.code} · {payment.supplier_name ?? `Supplier #${payment.supplier_id}`}</p><p className="mt-1 text-xs text-slate-500">{formatDateTime(payment.payment_date)} · {payment.payment_method}</p></div><span className="text-sm font-semibold">{currency.format(payment.amount)}</span><StatusBadge status={payment.status} /><button type="button" onClick={() => { try { printDocument({ title: 'Bukti Pembayaran Supplier', code: payment.code, subtitle: `Status ${payment.status}`, details: [['Supplier', `${payment.supplier_code ?? `#${payment.supplier_id}`} · ${payment.supplier_name ?? ''}`], ['Alamat supplier', payment.supplier_address ?? '—'], ['Email / telepon', [payment.supplier_email, payment.supplier_phone].filter(Boolean).join(' · ')], ['Tanggal pembayaran', formatDateTime(payment.payment_date)], ['Metode', payment.payment_method]], columns: ['Tagihan supplier', 'Jumlah alokasi'], rows: (payment.allocations ?? []).map((allocation) => [allocation.vendor_bill_code ?? `Tagihan #${allocation.vendor_bill_id ?? '—'}`, currency.format(allocation.amount)]), totals: [['Nilai pembayaran', currency.format(payment.amount)], ['Dialokasikan', currency.format(payment.allocated_amount)], ['Belum dialokasikan', currency.format(payment.unallocated_amount)]], signatures: ['Dibuat oleh', 'Diterima / disahkan oleh'], }) } catch (failure) { onNotice(getErrorMessage(failure)) } }} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"><Printer size={14} /> Cetak bukti</button></div>)}
            {supplierPayments.length === 0 && <EmptyState title="Belum ada pembayaran supplier" description="Transaksi pembayaran akan tampil di sini." />}
          </div>}
        </section>
      )}
      {orderDialogOpen && (
        <PurchaseOrderEditorDialog
          order={editingOrder ?? undefined}
          warehouseId={warehouseId}
          warehouses={warehouses}
          onClose={() => setOrderDialogOpen(false)}
          onSaved={() => { setOrderDialogOpen(false); setReload((value) => value + 1) }}
        />
      )}
      {(receiptDialogOpen || receiptToEdit) && (
        <GoodsReceiptEditorDialog
          orders={receivableOrders}
          warehouseId={warehouseId}
          receipt={receiptToEdit ?? undefined}
          onClose={() => { setReceiptDialogOpen(false); setReceiptToEdit(null) }}
          onSaved={() => { setReceiptDialogOpen(false); setReceiptToEdit(null); setReload((value) => value + 1) }}
        />
      )}
    </>
  )
}

interface PurchaseOrderItemDraft {
  product_id: string
  quantity: string
  unit_cost: string
}

function PurchaseOrderEditorDialog({
  order,
  warehouseId,
  warehouses,
  onClose,
  onSaved,
}: {
  order?: PurchaseOrderRecord
  warehouseId: string
  warehouses: WarehouseRecord[]
  onClose: () => void
  onSaved: () => void
}) {
  const [suppliers, setSuppliers] = useState<PartnerRecord[]>([])
  const [products, setProducts] = useState<ProductRecord[]>([])
  const [supplierId, setSupplierId] = useState('')
  const [selectedWarehouseId, setSelectedWarehouseId] = useState(warehouseId || '')
  const [orderDate, setOrderDate] = useState(new Date().toISOString().slice(0, 10))
  const [notes, setNotes] = useState('')
  const [items, setItems] = useState<PurchaseOrderItemDraft[]>([{ product_id: '', quantity: '1', unit_cost: '' }])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    const detailQuery = warehouseId ? `?warehouse_id=${encodeURIComponent(warehouseId)}` : ''
    Promise.all([
      apiRequest<PageResult<PartnerRecord>>('/suppliers?per_page=100'),
      apiRequest<PageResult<ProductRecord>>('/products?per_page=100&active=true'),
      ...(order ? [apiRequest<{ data: PurchaseOrderDetail }>(`/purchase-orders/${order.id}${detailQuery}`)] : []),
    ]).then((results) => {
      if (!active) return
      const supplierResponse = results[0] as PageResult<PartnerRecord>
      const productResponse = results[1] as PageResult<ProductRecord>
      setSuppliers(supplierResponse.data.filter((supplier) => supplier.is_active !== false))
      setProducts(productResponse.data.filter((product) => product.is_active !== false))
      if (order) {
        const detail = (results[2] as { data: PurchaseOrderDetail }).data
        setSupplierId(String(detail.supplier_id))
        setSelectedWarehouseId(String(detail.warehouse_id))
        setOrderDate(detail.order_date.slice(0, 10))
        setNotes(detail.notes ?? '')
        setItems(detail.items.map((item) => ({ product_id: String(item.product_id ?? ''), quantity: String(item.quantity), unit_cost: String(item.unit_cost ?? '') })))
      }
    }).catch((failure: unknown) => {
      if (active) setError(getErrorMessage(failure))
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [order, warehouseId])

  function updateItem(index: number, key: keyof PurchaseOrderItemDraft, value: string) {
    setItems((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: value } : item))
  }

  async function saveOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    const validItems = items.map((item) => ({ product_id: Number(item.product_id), quantity: Number(item.quantity), unit_cost: Number(item.unit_cost) }))
    if (!supplierId || !selectedWarehouseId || !orderDate || validItems.some((item) => !Number.isInteger(item.product_id) || item.product_id <= 0 || !Number.isFinite(item.quantity) || item.quantity <= 0 || !Number.isFinite(item.unit_cost) || item.unit_cost < 0)) {
      setError('Supplier, gudang, tanggal, produk, jumlah, dan biaya satuan harus diisi dengan benar.')
      return
    }
    setSaving(true)
    try {
      await apiRequest(order ? `/purchase-orders/${order.id}` : '/purchase-orders', {
        method: order ? 'PATCH' : 'POST',
        body: JSON.stringify({ supplier_id: Number(supplierId), warehouse_id: Number(selectedWarehouseId), order_date: orderDate, notes: notes.trim() || null, items: validItems }),
      })
      onSaved()
    } catch (failure) {
      setError(getErrorMessage(failure))
    } finally {
      setSaving(false)
    }
  }

  const total = items.reduce((sum, item) => sum + (Number(item.quantity) || 0) * (Number(item.unit_cost) || 0), 0)
  const availableWarehouses = warehouses.filter((warehouse) => warehouse.is_active !== false)

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 p-0 sm:items-center sm:p-5" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <form onSubmit={(event) => void saveOrder(event)} className="max-h-[94vh] w-full max-w-3xl overflow-y-auto rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl">
        <div className="flex items-start justify-between border-b border-slate-100 px-5 py-4 sm:px-6"><div><p className="text-[11px] font-bold tracking-widest text-emerald-700">PURCHASE ORDER</p><h2 className="mt-1 text-lg font-semibold text-slate-900">{order ? 'Ubah draft PO' : 'Buat purchase order'}</h2><p className="mt-1 text-xs text-slate-500">PO disimpan sebagai draft. Ajukan setelah detail pesanan siap.</p></div><button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Tutup dialog"><X size={18} /></button></div>
        {loading ? <div className="p-6"><LoadingBar /></div> : <>
          <div className="grid grid-cols-1 gap-4 px-5 py-5 sm:grid-cols-2 sm:px-6">
            <label className="text-xs font-semibold text-slate-600">Supplier<select required value={supplierId} onChange={(event) => setSupplierId(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal"><option value="">Pilih supplier</option>{suppliers.map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.code} · {supplier.name}</option>)}</select></label>
            <label className="text-xs font-semibold text-slate-600">Gudang tujuan<select required disabled={Boolean(warehouseId)} value={selectedWarehouseId} onChange={(event) => setSelectedWarehouseId(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal disabled:bg-slate-50">{!warehouseId && <option value="">Pilih gudang</option>}{availableWarehouses.map((warehouse) => <option key={warehouse.id} value={warehouse.id}>{warehouse.code} · {warehouse.name}</option>)}</select></label>
            <label className="text-xs font-semibold text-slate-600">Tanggal PO<input required type="date" value={orderDate} onChange={(event) => setOrderDate(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
            <div className="text-xs font-semibold text-slate-600">Nilai PO<div className="mt-2 rounded-lg bg-slate-50 px-3 py-2.5 text-sm font-semibold text-slate-800">{currency.format(total)}</div></div>
            <div className="space-y-3 sm:col-span-2"><div className="flex items-center justify-between"><h3 className="text-sm font-semibold text-slate-800">Barang yang dipesan</h3><button type="button" onClick={() => setItems((current) => [...current, { product_id: '', quantity: '1', unit_cost: '' }])} className="inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-xs font-semibold text-emerald-800 hover:bg-emerald-50"><Plus size={14} /> Tambah baris</button></div>
              {items.map((item, index) => <div key={index} className="grid grid-cols-1 items-end gap-3 rounded-lg border border-slate-100 p-3 sm:grid-cols-[minmax(0,1fr)_110px_150px_38px]"><label className="text-[11px] font-semibold text-slate-500 sm:col-span-1">Produk<select required value={item.product_id} onChange={(event) => updateItem(index, 'product_id', event.target.value)} className="mt-1.5 w-full rounded-md border border-slate-200 bg-white px-2.5 py-2 text-sm font-normal"><option value="">Pilih produk</option>{products.map((product) => <option key={product.id} value={product.id}>{product.sku} · {product.name}</option>)}</select></label><label className="text-[11px] font-semibold text-slate-500">Jumlah<input required min="0.0001" step="any" type="number" value={item.quantity} onChange={(event) => updateItem(index, 'quantity', event.target.value)} className="mt-1.5 w-full rounded-md border border-slate-200 px-2.5 py-2 text-sm font-normal" /></label><label className="text-[11px] font-semibold text-slate-500">Biaya satuan<input required min="0" step="any" type="number" value={item.unit_cost} onChange={(event) => updateItem(index, 'unit_cost', event.target.value)} className="mt-1.5 w-full rounded-md border border-slate-200 px-2.5 py-2 text-sm font-normal" /></label><button type="button" disabled={items.length === 1} onClick={() => setItems((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="flex h-9 items-center justify-center rounded-md text-slate-400 hover:bg-rose-50 hover:text-rose-600 disabled:opacity-30" aria-label="Hapus baris"><X size={16} /></button></div>)}
            </div>
            <label className="text-xs font-semibold text-slate-600 sm:col-span-2">Catatan<textarea rows={2} value={notes} onChange={(event) => setNotes(event.target.value)} className="mt-2 w-full resize-y rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
            {error && <p role="alert" className="rounded-lg border border-rose-100 bg-rose-50 px-3 py-2.5 text-sm text-rose-700 sm:col-span-2">{error}</p>}
            {!loading && (suppliers.length === 0 || products.length === 0 || availableWarehouses.length === 0) && <p className="rounded-lg bg-amber-50 px-3 py-2.5 text-xs text-amber-800 sm:col-span-2">Lengkapi data supplier, produk, dan gudang aktif sebelum membuat PO.</p>}
          </div>
          <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-4 sm:px-6"><button type="button" onClick={onClose} className="rounded-lg px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100">Batal</button><button disabled={saving || !suppliers.length || !products.length || !availableWarehouses.length} className="rounded-lg bg-[#087e63] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#066b55] disabled:opacity-50">{saving ? 'Menyimpan…' : 'Simpan draft PO'}</button></div>
        </>}
      </form>
    </div>
  )
}

function GoodsReceiptEditorDialog({
  orders,
  warehouseId,
  receipt,
  onClose,
  onSaved,
}: {
  orders: PurchaseOrderRecord[]
  warehouseId: string
  receipt?: GoodsReceiptRecord
  onClose: () => void
  onSaved: () => void
}) {
  const [orderId, setOrderId] = useState('')
  const [orderDetail, setOrderDetail] = useState<PurchaseOrderDetail | null>(null)
  const [quantities, setQuantities] = useState<Record<number, string>>({})
  const [receivedDate, setReceivedDate] = useState(new Date().toISOString().slice(0, 10))
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!receipt) return
    setOrderId(String(receipt.purchase_order_id ?? ''))
    setReceivedDate(receipt.received_date)
    setNotes(receipt.notes ?? '')
  }, [receipt?.id])

  useEffect(() => {
    if (!orderId) { setOrderDetail(null); return }
    let active = true
    setLoading(true)
    const query = warehouseId ? `?warehouse_id=${encodeURIComponent(warehouseId)}` : ''
    apiRequest<{ data: PurchaseOrderDetail }>(`/purchase-orders/${orderId}${query}`).then(({ data }) => {
      if (!active) return
      setOrderDetail(data)
      const existingQuantities = new Map((receipt?.items ?? []).map((item) => [
        Number((item as PrintableLine & { purchase_order_item_id?: number }).purchase_order_item_id),
        String(item.quantity),
      ]))
      setQuantities(Object.fromEntries(data.items.map((item) => [item.id ?? 0, existingQuantities.get(item.id ?? 0) ?? ''])))
    }).catch((failure: unknown) => { if (active) setError(getErrorMessage(failure)) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [orderId, warehouseId, receipt?.id])

  function existingReceiptQuantity(purchaseOrderItemId: number) {
    return Number((receipt?.items ?? []).find((item) => Number((item as PrintableLine & { purchase_order_item_id?: number }).purchase_order_item_id) === purchaseOrderItemId)?.quantity ?? 0)
  }

  async function saveReceipt(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    const items = (orderDetail?.items ?? []).map((item) => ({ purchase_order_item_id: item.id ?? 0, quantity: Number(quantities[item.id ?? 0]) })).filter((item) => item.quantity > 0)
    if (!orderId || !items.length || items.some((item) => !Number.isFinite(item.quantity))) {
      setError('Pilih PO dan isi jumlah diterima untuk minimal satu barang.')
      return
    }
    const overRemaining = items.some((item) => {
      const line = orderDetail?.items.find((candidate) => candidate.id === item.purchase_order_item_id)
      return !line || item.quantity > (line.remaining_qty ?? line.quantity) + existingReceiptQuantity(item.purchase_order_item_id)
    })
    if (overRemaining) { setError('Jumlah diterima tidak boleh melebihi sisa kuantitas PO.'); return }
    setSaving(true)
    try {
      await apiRequest(receipt ? `/goods-receipts/${receipt.id}` : '/goods-receipts', { method: receipt ? 'PATCH' : 'POST', body: JSON.stringify({ purchase_order_id: Number(orderId), received_date: receivedDate, notes: notes.trim() || null, items }) })
      onSaved()
    } catch (failure) {
      setError(getErrorMessage(failure))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 p-0 sm:items-center sm:p-5" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <form onSubmit={(event) => void saveReceipt(event)} className="max-h-[94vh] w-full max-w-2xl overflow-y-auto rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl">
        <div className="flex items-start justify-between border-b border-slate-100 px-5 py-4 sm:px-6"><div><p className="text-[11px] font-bold tracking-widest text-emerald-700">GOODS RECEIPT</p><h2 className="mt-1 text-lg font-semibold text-slate-900">{receipt ? 'Ubah draft penerimaan' : 'Catat penerimaan barang'}</h2><p className="mt-1 text-xs text-slate-500">{receipt ? 'Koreksi tanggal, catatan, dan jumlah barang sebelum posting.' : 'Pilih PO yang sudah disetujui, lalu masukkan jumlah yang benar-benar diterima.'}</p></div><button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Tutup dialog"><X size={18} /></button></div>
        <div className="grid grid-cols-1 gap-4 px-5 py-5 sm:px-6"><label className="text-xs font-semibold text-slate-600">Purchase order{receipt && <span className="ml-2 font-normal text-emerald-700">{receipt.purchase_order_code}</span>}<select required disabled={Boolean(receipt)} value={orderId} onChange={(event) => { setOrderId(event.target.value); setError('') }} className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal disabled:bg-slate-50"><option value="">Pilih PO disetujui</option>{orders.map((order) => <option key={order.id} value={order.id}>{order.code} · {order.supplier_name ?? `Supplier #${order.supplier_id}`} · sisa {numberFormat.format(order.remaining_qty ?? 0)}</option>)}</select></label>
          <label className="text-xs font-semibold text-slate-600">Tanggal diterima<input required type="date" value={receivedDate} onChange={(event) => setReceivedDate(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
          {loading && <LoadingBar />}
          {orderDetail && <div className="space-y-2"><h3 className="text-sm font-semibold text-slate-800">Jumlah yang diterima</h3>{orderDetail.items.map((item) => <label key={item.id} className="grid grid-cols-[minmax(0,1fr)_120px] items-center gap-3 rounded-lg border border-slate-100 p-3"><span className="min-w-0"><span className="block truncate text-sm font-medium text-slate-800">{item.product_name}</span><span className="text-xs text-slate-500">Sisa {numberFormat.format(item.remaining_qty ?? item.quantity)} {item.unit ?? ''}</span></span><input type="number" min="0" max={(item.remaining_qty ?? item.quantity) + existingReceiptQuantity(item.id ?? 0)} step="any" value={quantities[item.id ?? 0] ?? ''} onChange={(event) => setQuantities((current) => ({ ...current, [item.id ?? 0]: event.target.value }))} placeholder="0" className="w-full rounded-md border border-slate-200 px-2.5 py-2 text-sm" /></label>)}</div>}
          <label className="text-xs font-semibold text-slate-600">Catatan<textarea rows={2} value={notes} onChange={(event) => setNotes(event.target.value)} className="mt-2 w-full resize-y rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
          {error && <p role="alert" className="rounded-lg border border-rose-100 bg-rose-50 px-3 py-2.5 text-sm text-rose-700">{error}</p>}
          {!receipt && !orders.length && <EmptyState title="Belum ada PO untuk diterima" description="Penerimaan bisa dicatat setelah Manager menyetujui PO." />}
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-4 sm:px-6"><button type="button" onClick={onClose} className="rounded-lg px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100">Batal</button><button disabled={saving || loading || (!receipt && !orders.length)} className="rounded-lg bg-[#087e63] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#066b55] disabled:opacity-50">{saving ? 'Menyimpan…' : receipt ? 'Simpan perubahan' : 'Simpan draft penerimaan'}</button></div>
      </form>
    </div>
  )
}

function FinancePage({
  warehouseId,
  warehouses,
  canSelectAllWarehouses,
  onWarehouseChange,
  canViewFinancialMetrics,
  canViewInvoices,
  canCreateInvoices,
  canViewShipments,
  canViewVendorBills,
  canViewPayments,
  canViewSupplierPayments,
  canCreateCustomerPayments,
  canPostCustomerPayments,
  canAllocateCustomerPayments,
  canCreateSupplierPayments,
  canPostSupplierPayments,
  canAllocateSupplierPayments,
  onNotice,
}: {
  warehouseId: string
  warehouses: WarehouseRecord[]
  canSelectAllWarehouses: boolean
  onWarehouseChange: (warehouseId: string) => void
  canViewFinancialMetrics: boolean
  canViewInvoices: boolean
  canCreateInvoices: boolean
  canViewShipments: boolean
  canViewVendorBills: boolean
  canViewPayments: boolean
  canViewSupplierPayments: boolean
  canCreateCustomerPayments: boolean
  canPostCustomerPayments: boolean
  canAllocateCustomerPayments: boolean
  canCreateSupplierPayments: boolean
  canPostSupplierPayments: boolean
  canAllocateSupplierPayments: boolean
  onNotice: (message: string) => void
}) {
  const [invoices, setInvoices] = useState<InvoiceRecord[]>([])
  const [shipments, setShipments] = useState<ShipmentRecord[]>([])
  const [vendorBills, setVendorBills] = useState<VendorBillRecord[]>([])
  const [payments, setPayments] = useState<CustomerPaymentRecord[]>([])
  const [supplierPayments, setSupplierPayments] = useState<SupplierPaymentRecord[]>([])
  const [outstanding, setOutstanding] = useState(0)
  const [overdue, setOverdue] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [paymentDialog, setPaymentDialog] = useState<'customer' | 'supplier' | null>(null)
  const [draftToResume, setDraftToResume] = useState<{ kind: 'customer' | 'supplier'; id: number; amount: number; partyId: number } | null>(null)
  const [reload, setReload] = useState(0)
  useEffect(() => {
    let active = true
    const hasWarehouseScope = canSelectAllWarehouses || (
      Boolean(warehouseId) && warehouses.some((warehouse) => String(warehouse.id) === warehouseId)
    )
    if (!hasWarehouseScope) {
      setInvoices([])
      setPayments([])
      setSupplierPayments([])
      setShipments([])
      setVendorBills([])
      setOutstanding(0)
      setOverdue(0)
      setError('Akun ini belum memiliki cakupan gudang. Minta Admin menetapkan gudang melalui Pengguna → Atur gudang.')
      setLoading(false)
      return () => { active = false }
    }
    setLoading(true)
    setError('')
    const warehouseQuery = warehouseId ? `warehouse_id=${encodeURIComponent(warehouseId)}&` : ''
    const invoiceRequest = canViewInvoices
      ? apiRequest<PageResult<InvoiceRecord>>(`/invoices?${warehouseQuery}per_page=100`).then((response) => response.data)
      : canViewFinancialMetrics
        ? apiRequest<{ data: InvoiceRecord[] }>(`/finance/receivables?${warehouseQuery}per_page=100`).then((response) => response.data)
        : Promise.resolve([] as InvoiceRecord[])
    const paymentRequest = canViewPayments
      ? apiRequest<PageResult<CustomerPaymentRecord>>(`/customer-payments?${warehouseQuery}per_page=100`).then((response) => response.data)
      : Promise.resolve([] as CustomerPaymentRecord[])
    const supplierPaymentRequest = canViewSupplierPayments
      ? apiRequest<PageResult<SupplierPaymentRecord>>(`/supplier-payments?${warehouseQuery}per_page=100`).then((response) => response.data)
      : Promise.resolve([] as SupplierPaymentRecord[])
    const shipmentRequest = canViewShipments && canCreateInvoices
      ? apiRequest<PageResult<ShipmentRecord>>(`/shipments?${warehouseQuery}status=POSTED&per_page=100`).then((response) => response.data)
      : Promise.resolve([] as ShipmentRecord[])
    const vendorBillRequest = canViewVendorBills
      ? apiRequest<PageResult<VendorBillRecord>>(`/vendor-bills?${warehouseQuery}per_page=100`).then((response) => response.data)
      : Promise.resolve([] as VendorBillRecord[])
    const receivablesRequest = canViewFinancialMetrics
      ? apiRequest<{ summary: { outstanding_amount: number; overdue_amount: number } }>(`/finance/receivables?${warehouseQuery}per_page=100`)
      : Promise.resolve({ summary: { outstanding_amount: 0, overdue_amount: 0 } })
    Promise.all([invoiceRequest, paymentRequest, supplierPaymentRequest, receivablesRequest, shipmentRequest, vendorBillRequest])
      .then(([invoiceRows, paymentRows, supplierPaymentRows, receivables, shipmentRows, vendorBillRows]) => {
        if (!active) return
        setInvoices(invoiceRows)
        setPayments(paymentRows)
        setSupplierPayments(supplierPaymentRows)
        setShipments(shipmentRows)
        setVendorBills(vendorBillRows)
        setOutstanding(receivables.summary.outstanding_amount)
        setOverdue(receivables.summary.overdue_amount)
      })
      .catch((failure: unknown) => { if (active) setError(getErrorMessage(failure)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [warehouseId, warehouses, canSelectAllWarehouses, canViewFinancialMetrics, canViewInvoices, canViewPayments, canViewSupplierPayments, canViewShipments, canCreateInvoices, canViewVendorBills, reload])

  async function createInvoice(shipment: ShipmentRecord) {
    try {
      await apiRequest('/sales-invoices', { method: 'POST', body: JSON.stringify({ shipment_id: shipment.id }) })
      onNotice(`Invoice berhasil dibuat dari ${shipment.code}.`)
      setReload((value) => value + 1)
    } catch (failure) { setError(getErrorMessage(failure)) }
  }

  async function resumePaymentDraft(kind: 'customer' | 'supplier', payment: CustomerPaymentRecord | SupplierPaymentRecord) {
    if (payment.status !== 'DRAFT') return
    if (payment.allocations?.length) {
      try {
        await apiRequest(`/${kind === 'customer' ? 'customer-payments' : 'supplier-payments'}/${payment.id}/post`, { method: 'POST' })
        setReload((value) => value + 1)
        onNotice('Draft pembayaran berhasil diposting.')
      } catch (failure) { setError(getErrorMessage(failure)) }
      return
    }
    setDraftToResume({ kind, id: payment.id, amount: payment.amount, partyId: kind === 'customer' ? (payment as CustomerPaymentRecord).customer_id : (payment as SupplierPaymentRecord).supplier_id })
    setPaymentDialog(kind)
  }

  return (
    <>
      <PageHeading eyebrow="FINANCE" title={canViewFinancialMetrics ? 'Piutang & utang' : 'Status tagihan & pembayaran'} description={canViewFinancialMetrics ? 'Kelola invoice, tagihan supplier, alokasi, dan posting pembayaran.' : 'Lihat status invoice dan pembayaran tanpa akses ke nilai finansial.'} />
      <div className="mb-5 flex flex-col gap-2 rounded-xl border border-slate-200/80 bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700"><WarehouseIcon size={17} className="text-emerald-700" /> Cakupan gudang</div>
        <label className="flex min-w-0 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 sm:min-w-[280px]">
          <span className="shrink-0 text-xs text-slate-500">Gudang</span>
          <select value={warehouseId} onChange={(event) => onWarehouseChange(event.target.value)} disabled={!canSelectAllWarehouses && warehouses.length === 0} className="min-w-0 flex-1 bg-transparent text-sm font-medium text-slate-700 outline-none disabled:opacity-60" aria-label="Filter gudang Finance">
            {canSelectAllWarehouses && <option value="">Semua gudang</option>}
            {!canSelectAllWarehouses && !warehouseId && <option value="">Pilih gudang yang ditugaskan</option>}
            {warehouses.map((warehouse) => <option key={warehouse.id} value={warehouse.id}>{warehouse.code} · {warehouse.name}</option>)}
          </select>
          <ChevronDown size={14} className="shrink-0 text-slate-400" />
        </label>
        {!canSelectAllWarehouses && warehouses.length === 0 && <span className="text-xs text-amber-700">Akun belum ditugaskan ke gudang.</span>}
      </div>
      {canViewFinancialMetrics && <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <StatCard title="Piutang berjalan" value={currency.format(outstanding)} detail="Total saldo invoice terbuka" icon={FileText} tone="blue" />
        <StatCard title="Piutang jatuh tempo" value={currency.format(overdue)} detail="Saldo melewati tanggal jatuh tempo" icon={ArrowDownRight} tone="amber" />
      </div>}
      <section className="overflow-hidden rounded-xl border border-slate-200/80 bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4"><div><h2 className="text-sm font-semibold text-slate-900">Invoice pelanggan</h2><p className="mt-1 text-xs text-slate-500">{invoices.length} invoice ditemukan</p></div>{canCreateCustomerPayments && canPostCustomerPayments && canAllocateCustomerPayments && <button type="button" onClick={() => setPaymentDialog('customer')} className="rounded-lg bg-[#087e63] px-3 py-2 text-xs font-semibold text-white hover:bg-[#066b55]">Catat pembayaran pelanggan</button>}</div>
        {error ? <div className="p-5"><ErrorPanel message={error} /></div> : <>
          {loading && <LoadingBar />}
          <div className="divide-y border-t border-slate-100">{invoices.map((invoice) => <div key={invoice.id} className="flex flex-wrap items-center gap-3 px-4 py-4 sm:px-5"><div className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-50 text-violet-700"><FileText size={17} /></div><div className="min-w-[140px] flex-1"><p className="text-sm font-semibold text-slate-800">{invoice.code}</p><p className="mt-1 text-xs text-slate-500">{invoice.customer_name} · Jatuh tempo {formatDate(invoice.due_date)}</p></div><div className="text-right"><StatusBadge status={invoice.status ?? 'OPEN'} />{canViewFinancialMetrics && <><p className="mt-1 text-sm font-semibold text-slate-800">{currency.format(invoice.balance_due)}</p>{invoice.overdue_days && invoice.overdue_days > 0 && <p className="mt-1 text-[11px] text-rose-600">{invoice.overdue_days} hari terlambat</p>}</>}</div>{canViewInvoices && canViewFinancialMetrics && <button type="button" onClick={() => requestPrint(`/invoices/${invoice.id}${warehouseId ? `?warehouse_id=${encodeURIComponent(warehouseId)}` : ''}`, 'Invoice penjualan', (data: PrintableInvoice) => ({ title: 'Invoice Penjualan', code: data.code, subtitle: `Status ${data.status ?? '—'}`, details: [['Pelanggan', `${data.customer_code ?? '—'} · ${data.customer_name ?? '—'}`], ['Alamat pelanggan', data.customer_address ?? '—'], ['Email / telepon', [data.customer_email, data.customer_phone].filter(Boolean).join(' · ')], ['Sales order', data.sales_order_code ?? '—'], ['Surat jalan', data.shipment_code ?? '—'], ['Gudang', data.warehouse_name ?? '—'], ['Tanggal terbit', formatDate(data.created_at)], ['Jatuh tempo', formatDate(data.due_date)]], columns: ['No.', 'Produk', 'Jumlah', 'Satuan', 'Harga satuan', 'Subtotal'], rows: printLines(data.items, true), totals: [['Total invoice', currency.format(data.total_amount)], ['Pembayaran diterima', currency.format(data.amount_paid)], ['Sisa tagihan', currency.format(data.balance_due)]], note: 'Mohon mencantumkan nomor invoice pada bukti pembayaran.', }), onNotice)} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"><Printer size={14} /> Cetak invoice</button>}</div>)}{!loading && invoices.length === 0 && !error && <EmptyState title="Tidak ada invoice" description="Invoice akan tampil setelah pengiriman ditagihkan." />}</div>
        </>}
      </section>
      {canCreateInvoices && <section className="mt-5 overflow-hidden rounded-xl border border-slate-200/80 bg-white"><div className="border-b border-slate-100 px-5 py-4"><h2 className="text-sm font-semibold text-slate-900">Pengiriman siap ditagihkan</h2><p className="mt-1 text-xs text-slate-500">Shipment yang sudah diposting dan belum memiliki invoice.</p></div><div className="divide-y divide-slate-100">{shipments.filter((shipment) => !shipment.invoice_id).map((shipment) => <div key={shipment.id} className="flex flex-wrap items-center gap-3 px-4 py-4 sm:px-5"><div className="min-w-[150px] flex-1"><p className="text-sm font-semibold text-slate-800">{shipment.code}</p><p className="mt-1 text-xs text-slate-500">{shipment.customer_name} · SO {shipment.sales_order_code}</p></div><StatusBadge status={shipment.status} /><button type="button" onClick={() => void createInvoice(shipment)} className="rounded-lg border border-emerald-200 px-3 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-50">Buat invoice</button></div>)}{!loading && shipments.filter((shipment) => !shipment.invoice_id).length === 0 && <EmptyState title="Tidak ada shipment yang perlu ditagihkan" description="Shipment yang diposting tanpa invoice akan muncul di sini." />}</div></section>}
      {canViewVendorBills && <section className="mt-5 overflow-hidden rounded-xl border border-slate-200/80 bg-white"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4"><div><h2 className="text-sm font-semibold text-slate-900">Tagihan supplier</h2><p className="mt-1 text-xs text-slate-500">Tagihan dibuat otomatis dari penerimaan barang yang diposting.</p></div>{canCreateSupplierPayments && canPostSupplierPayments && canAllocateSupplierPayments && <button type="button" onClick={() => setPaymentDialog('supplier')} className="rounded-lg bg-[#087e63] px-3 py-2 text-xs font-semibold text-white hover:bg-[#066b55]">Catat pembayaran supplier</button>}</div><div className="divide-y divide-slate-100">{vendorBills.map((bill) => <div key={bill.id} className="flex flex-wrap items-center gap-3 px-4 py-4 sm:px-5"><div className="min-w-[150px] flex-1"><p className="text-sm font-semibold text-slate-800">{bill.code}</p><p className="mt-1 text-xs text-slate-500">Supplier #{bill.supplier_id} · {formatDate(bill.created_at)}</p></div><StatusBadge status={bill.status} />{canViewFinancialMetrics && <div className="text-right text-xs"><p className="font-semibold text-slate-800">Sisa {currency.format(bill.balance_due)}</p><p className="mt-1 text-slate-500">Total {currency.format(bill.total_amount)}</p></div>}</div>)}{!loading && vendorBills.length === 0 && <EmptyState title="Belum ada tagihan supplier" description="Vendor bill akan muncul setelah goods receipt diposting." />}</div></section>}
      {canViewPayments && (
        <section className="mt-5 overflow-hidden rounded-xl border border-slate-200/80 bg-white">
          <div className="border-b border-slate-100 px-5 py-4"><h2 className="text-sm font-semibold text-slate-900">Pembayaran pelanggan</h2><p className="mt-1 text-xs text-slate-500">{payments.length} transaksi pembayaran terbaru</p></div>
          <div className="divide-y divide-slate-100">
            {payments.map((payment) => <div key={payment.id} className="flex flex-wrap items-center gap-3 px-4 py-4 sm:px-5"><div className="min-w-[140px] flex-1"><p className="text-sm font-semibold text-slate-800">{payment.customer_name ?? `Pelanggan #${payment.customer_id}`}{payment.invoice_code ? ` · ${payment.invoice_code}` : ''}</p><p className="mt-1 text-xs text-slate-500">{formatDateTime(payment.payment_date)}{canViewFinancialMetrics && payment.payment_method ? ` · ${payment.payment_method}` : ''}</p></div>{canViewFinancialMetrics && <span className="text-sm font-semibold">{currency.format(payment.amount)}</span>}<StatusBadge status={payment.status} />{payment.status === 'DRAFT' && canCreateCustomerPayments && canPostCustomerPayments && canAllocateCustomerPayments && <button type="button" onClick={() => void resumePaymentDraft('customer', payment)} className="rounded-lg border border-amber-200 px-3 py-2 text-xs font-semibold text-amber-800">Lanjutkan draft</button>}{canViewFinancialMetrics && <button type="button" onClick={() => { try { printDocument({ title: 'Bukti Pembayaran Pelanggan', code: `PAY-${payment.id}`, subtitle: `Status ${payment.status}`, details: [['Pelanggan', `${payment.customer_code ?? `#${payment.customer_id}`} · ${payment.customer_name ?? ''}`], ['Alamat pelanggan', payment.customer_address ?? '—'], ['Email / telepon', [payment.customer_email, payment.customer_phone].filter(Boolean).join(' · ')], ['Tanggal pembayaran', formatDateTime(payment.payment_date)], ['Metode', payment.payment_method]], columns: ['Invoice', 'Jumlah alokasi'], rows: (payment.allocations ?? []).map((allocation) => [allocation.invoice_code ?? `Invoice #${allocation.invoice_id ?? '—'}`, currency.format(allocation.amount)]), totals: [['Nilai pembayaran', currency.format(payment.amount)]], signatures: ['Diterima oleh', 'Dibayarkan oleh'], }) } catch (failure) { onNotice(getErrorMessage(failure)) } }} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"><Printer size={14} /> Cetak bukti</button>}</div>)}
            {payments.length === 0 && <EmptyState title="Belum ada pembayaran pelanggan" description="Transaksi pembayaran akan tampil di sini." />}
          </div>
        </section>
      )}
      {canViewSupplierPayments && (
        <section className="mt-5 overflow-hidden rounded-xl border border-slate-200/80 bg-white">
          <div className="border-b border-slate-100 px-5 py-4"><h2 className="text-sm font-semibold text-slate-900">Status pembayaran supplier</h2></div>
          <div className="divide-y divide-slate-100">{supplierPayments.map((payment) => <div key={payment.id} className="flex items-center gap-3 px-4 py-4 sm:px-5"><div className="min-w-[140px] flex-1"><p className="text-sm font-semibold text-slate-800">{payment.code} · {payment.supplier_name}</p><p className="mt-1 text-xs text-slate-500">{formatDateTime(payment.payment_date)}</p></div><StatusBadge status={payment.status} />{payment.status === 'DRAFT' && canCreateSupplierPayments && canPostSupplierPayments && canAllocateSupplierPayments && <button type="button" onClick={() => void resumePaymentDraft('supplier', payment)} className="rounded-lg border border-amber-200 px-3 py-2 text-xs font-semibold text-amber-800">Lanjutkan draft</button>}</div>)}{!loading && supplierPayments.length === 0 && <EmptyState title="Belum ada pembayaran supplier" description="Status pembayaran akan tampil di sini." />}</div>
        </section>
      )}
      {paymentDialog && <FinancePaymentDialog kind={paymentDialog} warehouseId={warehouseId} invoices={invoices.filter((invoice) => invoice.balance_due > 0)} vendorBills={vendorBills.filter((bill) => bill.balance_due > 0)} draft={draftToResume} onClose={() => { setPaymentDialog(null); setDraftToResume(null) }} onCreated={() => { setPaymentDialog(null); setDraftToResume(null); setReload((value) => value + 1); onNotice('Pembayaran dialokasikan dan diposting.') }} />}
    </>
  )
}

function FinancePaymentDialog({ kind, warehouseId, invoices, vendorBills, draft, onClose, onCreated }: {
  kind: 'customer' | 'supplier'
  warehouseId: string
  invoices: InvoiceRecord[]
  vendorBills: VendorBillRecord[]
  draft: { kind: 'customer' | 'supplier'; id: number; amount: number; partyId: number } | null
  onClose: () => void
  onCreated: () => void
}) {
  const [targetId, setTargetId] = useState('')
  const [amount, setAmount] = useState('')
  const [method, setMethod] = useState(kind === 'customer' ? 'BANK_TRANSFER' : 'BANK_TRANSFER')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const targets = kind === 'customer' ? invoices : vendorBills
  const availableTargets = targets.filter((item) => !draft || (draft.kind === kind && (kind === 'customer' ? (item as InvoiceRecord).customer_id : (item as VendorBillRecord).supplier_id) === draft.partyId))
  const target = availableTargets.find((item) => item.id === Number(targetId))

  useEffect(() => {
    if (availableTargets.length && !targetId) {
      setTargetId(String(availableTargets[0].id))
      setAmount(String(draft?.amount ?? availableTargets[0].balance_due))
    }
  }, [availableTargets, targetId, draft])

  async function savePayment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const numericAmount = Number(amount)
    if (!target || !Number.isFinite(numericAmount) || numericAmount <= 0 || numericAmount > target.balance_due) {
      setError('Pilih tagihan dan isi alokasi positif yang tidak melebihi saldo tagihan.')
      return
    }
    setSaving(true)
    setError('')
    let paymentId: number | undefined
    try {
      if (!draft) {
        const endpoint = kind === 'customer' ? '/customer-payments/record-and-post' : '/supplier-payments/record-and-post'
        const payload = kind === 'customer'
          ? { invoice_id: target.id, amount: numericAmount, payment_method: method, ...(warehouseId ? { warehouse_id: Number(warehouseId) } : {}) }
          : { vendor_bill_id: target.id, amount: numericAmount, payment_method: method, ...(warehouseId ? { warehouse_id: Number(warehouseId) } : {}) }
        await apiRequest(endpoint, { method: 'POST', body: JSON.stringify(payload) })
        onCreated()
        return
      }
      paymentId = draft.id
      const allocationPath = kind === 'customer' ? `/customer-payments/${paymentId}/allocations` : `/supplier-payments/${paymentId}/allocations`
      const allocation = kind === 'customer' ? { invoice_id: target.id, amount: numericAmount } : { vendor_bill_id: target.id, amount: numericAmount }
      if (draft && numericAmount > draft.amount) throw new Error('Alokasi melebihi nilai draft pembayaran.')
      await apiRequest(allocationPath, { method: 'POST', body: JSON.stringify({ allocations: [allocation], ...(warehouseId ? { warehouse_id: Number(warehouseId) } : {}) }) })
      const postPath = kind === 'customer' ? `/customer-payments/${paymentId}/post` : `/supplier-payments/${paymentId}/post`
      await apiRequest(postPath, { method: 'POST' })
      onCreated()
    } catch (failure) {
      const message = getErrorMessage(failure)
      setError(paymentId ? `${message} Pembayaran draft #${paymentId} sudah dibuat; periksa daftar pembayaran sebelum mencoba ulang.` : message)
    } finally { setSaving(false) }
  }

  return <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 p-0 sm:items-center sm:p-5" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><form onSubmit={(event) => void savePayment(event)} className="w-full max-w-lg rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl"><div className="flex items-start justify-between border-b border-slate-100 px-5 py-4"><div><p className="text-[11px] font-bold tracking-widest text-emerald-700">FINANCE</p><h2 className="mt-1 text-lg font-semibold text-slate-900">Pembayaran {kind === 'customer' ? 'pelanggan' : 'supplier'}</h2><p className="mt-1 text-xs text-slate-500">Pembayaran dibuat sebagai draft, dialokasikan ke tagihan, lalu diposting.</p></div><button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Tutup dialog"><X size={18} /></button></div><div className="space-y-4 p-5"><label className="block text-xs font-semibold text-slate-600">{kind === 'customer' ? 'Invoice' : 'Vendor bill'}<select required value={targetId} onChange={(event) => { setTargetId(event.target.value); const chosen = targets.find((item) => item.id === Number(event.target.value)); setAmount(chosen ? String(chosen.balance_due) : '') }} className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal"><option value="">Pilih tagihan</option>{kind === 'customer' ? invoices.map((invoice) => <option key={invoice.id} value={invoice.id}>{invoice.code} · {invoice.customer_name} · sisa {currency.format(invoice.balance_due)}</option>) : vendorBills.map((bill) => <option key={bill.id} value={bill.id}>{bill.code} · Supplier #{bill.supplier_id} · sisa {currency.format(bill.balance_due)}</option>)}</select></label><label className="block text-xs font-semibold text-slate-600">Jumlah alokasi<input required type="number" min="0.01" max={target?.balance_due} step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label><label className="block text-xs font-semibold text-slate-600">Metode<select value={method} onChange={(event) => setMethod(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal"><option value="BANK_TRANSFER">Transfer bank</option><option value="CASH">Tunai</option><option value="CREDIT_CARD">Kartu kredit</option></select></label>{error && <p role="alert" className="rounded-lg border border-rose-100 bg-rose-50 px-3 py-2.5 text-sm text-rose-700">{error}</p>}{!targets.length && <EmptyState title="Tidak ada tagihan terbuka" description="Tagihan akan tersedia setelah invoice atau goods receipt dibuat." />}</div><div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-4"><button type="button" onClick={onClose} className="rounded-lg px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-100">Batal</button><button disabled={saving || !target} className="rounded-lg bg-[#087e63] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{saving ? 'Memproses…' : 'Alokasikan & posting'}</button></div></form></div>
}

interface AuditLogRecord {
  id: number
  user_id: number | null
  username?: string | null
  action: string
  endpoint: string
  resource_id: string | null
  status_code: number
  ip_address: string | null
  created_at: string | null
}

function AuditLogsPage() {
  const [rows, setRows] = useState<AuditLogRecord[]>([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [userId, setUserId] = useState('')
  const [action, setAction] = useState('')
  const [endpoint, setEndpoint] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    const params = new URLSearchParams({ page: String(page), per_page: '25' })
    if (userId) params.set('user_id', userId)
    if (action) params.set('action', action)
    if (endpoint.trim()) params.set('endpoint', endpoint.trim())
    setLoading(true)
    setError('')
    apiRequest<PageResult<AuditLogRecord>>(`/audit-logs?${params.toString()}`)
      .then((response) => { if (active) { setRows(response.data); setTotal(response.total); setPages(Math.max(response.pages, 1)) } })
      .catch((failure: unknown) => { if (active) setError(getErrorMessage(failure)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [page, refresh])

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPage(1)
    setRefresh((value) => value + 1)
  }

  return <>
    <PageHeading eyebrow="PENGATURAN" title="Audit log" description="Telusuri aktivitas API yang tercatat, termasuk pengguna, endpoint, hasil, dan waktu permintaan." />
    <form onSubmit={applyFilters} className="mb-5 grid gap-3 rounded-xl border border-slate-200/80 bg-white p-4 sm:grid-cols-2 lg:grid-cols-[180px_180px_minmax(220px,1fr)_auto] sm:p-5">
      <label className="text-xs font-semibold text-slate-600">ID pengguna<input type="number" min="1" value={userId} onChange={(event) => setUserId(event.target.value)} placeholder="Semua pengguna" className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
      <label className="text-xs font-semibold text-slate-600">Metode<select value={action} onChange={(event) => setAction(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal"><option value="">Semua metode</option>{['GET', 'POST', 'PATCH', 'PUT', 'DELETE'].map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
      <label className="text-xs font-semibold text-slate-600">Endpoint<input value={endpoint} onChange={(event) => setEndpoint(event.target.value)} placeholder="Contoh: sales.create_sales_order" className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
      <button className="self-end rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800">Terapkan filter</button>
    </form>
    <section className="overflow-hidden rounded-xl border border-slate-200/80 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4"><div><h2 className="text-sm font-semibold text-slate-900">Aktivitas tercatat</h2><p className="mt-1 text-xs text-slate-500">{numberFormat.format(total)} catatan · terbaru lebih dahulu</p></div><button type="button" onClick={() => setRefresh((value) => value + 1)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50">Muat ulang</button></div>
      {error ? <div className="p-5"><ErrorPanel message={error} /></div> : <>{loading && <LoadingBar />}<div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left"><thead className="bg-slate-50 text-[11px] font-semibold uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3">Waktu</th><th className="px-4 py-3">Pengguna</th><th className="px-4 py-3">Aksi</th><th className="px-4 py-3">Endpoint</th><th className="px-4 py-3">Resource</th><th className="px-4 py-3">Hasil</th><th className="px-5 py-3">IP</th></tr></thead><tbody className="divide-y divide-slate-100">{rows.map((row) => <tr key={row.id} className="hover:bg-slate-50/70"><td className="whitespace-nowrap px-5 py-3.5 text-xs text-slate-600">{formatDateTime(row.created_at)}</td><td className="px-4 py-3.5 text-xs text-slate-700">{row.username ?? (row.user_id ? `#${row.user_id}` : 'Sistem')}</td><td className="px-4 py-3.5"><span className="rounded-md bg-slate-100 px-2 py-1 text-[10px] font-bold text-slate-700">{row.action}</span></td><td className="px-4 py-3.5 font-mono text-xs text-slate-700">{row.endpoint}</td><td className="px-4 py-3.5 text-xs text-slate-600">{row.resource_id ?? '—'}</td><td className="px-4 py-3.5"><span className={`rounded-md px-2 py-1 text-[10px] font-bold ${row.status_code < 400 ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>{row.status_code}</span></td><td className="px-5 py-3.5 text-xs text-slate-500">{row.ip_address ?? '—'}</td></tr>)}</tbody></table></div>{!rows.length && !loading && <EmptyState title="Tidak ada catatan audit" description="Coba ubah filter untuk melihat aktivitas lainnya." />}<div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 sm:px-5"><p className="text-xs text-slate-500">Halaman {page} dari {pages}</p><div className="flex gap-2"><button type="button" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs disabled:opacity-40">Sebelumnya</button><button type="button" disabled={page >= pages || loading} onClick={() => setPage((value) => value + 1)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs disabled:opacity-40">Berikutnya</button></div></div></>}
    </section>
  </>
}

function MasterDataPage({ permissions }: { permissions: string[] }) {
  const [resource, setResource] = useState('products')
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [editingProduct, setEditingProduct] = useState<ProductRecord | null>(null)
  const [productDialogOpen, setProductDialogOpen] = useState(false)
  const [editingCustomer, setEditingCustomer] = useState<PartnerRecord | null>(null)
  const [customerDialogOpen, setCustomerDialogOpen] = useState(false)
  const [editingSupplier, setEditingSupplier] = useState<PartnerRecord | null>(null)
  const [supplierDialogOpen, setSupplierDialogOpen] = useState(false)
  const [editingReference, setEditingReference] = useState<Record<string, unknown> | null>(null)
  const [referenceDialogOpen, setReferenceDialogOpen] = useState(false)
  const allResourceOptions = [
    ['products', 'Produk', Package],
    ['customers', 'Pelanggan', Users],
    ['suppliers', 'Supplier', Truck],
    ['warehouses', 'Gudang', WarehouseIcon],
    ['categories', 'Kategori', Boxes],
    ['units', 'Satuan', ClipboardList],
  ] as const
  const canReadMasterData = permissions.includes('master_data.read')
  const canManage = permissions.includes('master_data.manage')
  const resourceOptions = allResourceOptions.filter(([key]) => {
    if (key === 'customers') return permissions.includes('customers.read')
    if (key === 'suppliers') return permissions.includes('suppliers.read')
    return canReadMasterData
  })
  const visibleResource = resourceOptions.some(([key]) => key === resource)

  useEffect(() => {
    if (!visibleResource && resourceOptions[0]) setResource(resourceOptions[0][0])
  }, [visibleResource, resourceOptions])

  useEffect(() => {
    if (!visibleResource) return
    let active = true
    apiRequest<{ data: Array<Record<string, unknown>> }>(`/${resource}?per_page=100`)
      .then((response) => { if (active) setRows(response.data) })
      .catch((failure: unknown) => { if (active) setError(getErrorMessage(failure)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [resource, refreshKey, visibleResource])

  const canManageResource = resource === 'customers'
    ? permissions.includes('customers.manage')
    : resource === 'suppliers'
      ? permissions.includes('suppliers.manage')
      : canManage

  async function deactivateReference(row: Record<string, unknown>) {
    if (!window.confirm(`Nonaktifkan ${String(row.name ?? row.code ?? 'data master')}?`)) return
    try {
      await apiRequest(`/${resource}/${row.id}`, { method: 'DELETE' })
      setLoading(true)
      setRefreshKey((value) => value + 1)
    } catch (failure) { setError(getErrorMessage(failure)) }
  }

  async function deactivateProduct(product: ProductRecord) {
    if (!window.confirm(`Nonaktifkan produk ${product.sku} — ${product.name}?`)) return
    setError('')
    try {
      await apiRequest(`/products/${product.id}`, { method: 'DELETE' })
      setLoading(true)
      setRefreshKey((value) => value + 1)
    } catch (failure) {
      setError(getErrorMessage(failure))
    }
  }

  const columns = resource === 'products'
    ? [['sku', 'SKU'], ['name', 'Nama'], ['sales_price', 'Harga jual'], ['min_stock', 'Minimum stok'], ['is_active', 'Status'], ...(canManageResource ? [['actions', 'Aksi']] : [])]
    : resource === 'warehouses'
      ? [['code', 'Kode'], ['name', 'Nama gudang'], ['address', 'Alamat'], ['is_active', 'Status'], ...(canManageResource ? [['actions', 'Aksi']] : [])]
      : resource === 'categories'
        ? [['name', 'Kategori'], ['description', 'Deskripsi'], ['is_active', 'Status'], ...(canManageResource ? [['actions', 'Aksi']] : [])]
        : resource === 'units'
          ? [['name', 'Satuan'], ['symbol', 'Simbol'], ['is_active', 'Status'], ...(canManageResource ? [['actions', 'Aksi']] : [])]
      : resource === 'customers'
        ? [['code', 'Kode'], ['name', 'Nama pelanggan'], ['email', 'Email'], ['phone', 'Telepon'], ['is_active', 'Status'], ...(canManageResource ? [['actions', 'Aksi']] : [])]
        : [['code', 'Kode'], ['name', 'Nama supplier'], ['email', 'Email'], ['phone', 'Telepon'], ['is_active', 'Status'], ...(canManageResource ? [['actions', 'Aksi']] : [])]

  function renderMasterDataCell(row: Record<string, unknown>, key: string) {
    if (key === 'is_active') return <StatusBadge status={row[key] === true ? 'ACTIVE' : 'INACTIVE'} />
    if (key === 'sales_price') return row[key] == null ? 'Belum diatur' : currency.format(Number(row[key]))
    if (key === 'actions' && resource === 'products' && canManage) {
      return <div className="flex items-center gap-2"><button type="button" onClick={() => { setEditingProduct(row as unknown as ProductRecord); setProductDialogOpen(true) }} className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold hover:bg-slate-50"><Pencil size={13} /> Ubah</button><button type="button" onClick={() => void deactivateProduct(row as unknown as ProductRecord)} className="rounded-md border border-rose-200 px-2.5 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50">Nonaktifkan</button></div>
    }
    if (key === 'actions' && resource === 'customers' && canManageResource) {
      return <button type="button" onClick={() => { setEditingCustomer(row as unknown as PartnerRecord); setCustomerDialogOpen(true) }} className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"><Pencil size={13} /> Ubah</button>
    }
    if (key === 'actions' && resource === 'suppliers' && canManageResource) {
      return <button type="button" onClick={() => { setEditingSupplier(row as unknown as PartnerRecord); setSupplierDialogOpen(true) }} className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"><Pencil size={13} /> Ubah</button>
    }
    if (key === 'actions' && ['warehouses', 'categories', 'units'].includes(resource) && canManageResource) {
      return <div className="flex items-center gap-2"><button type="button" onClick={() => { setEditingReference(row); setReferenceDialogOpen(true) }} className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"><Pencil size={13} /> Ubah</button>{row.is_active !== false && <button type="button" onClick={() => void deactivateReference(row)} className="rounded-md border border-rose-200 px-2.5 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50">Nonaktifkan</button>}</div>
    }
    return String(row[key] ?? '—')
  }

  return (
    <>
      <PageHeading eyebrow="MASTER DATA" title="Data master" description="Referensi produk, pelanggan, supplier, dan gudang untuk transaksi ERP." />
      {resource === 'products' && canManageResource && (
        <div className="mb-4 flex justify-end">
          <button type="button" onClick={() => { setEditingProduct(null); setProductDialogOpen(true) }} className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800"><Plus size={16} /> Produk baru</button>
        </div>
      )}
      {resource === 'customers' && canManageResource && (
        <div className="mb-4 flex justify-end">
          <button type="button" onClick={() => { setEditingCustomer(null); setCustomerDialogOpen(true) }} className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800"><Plus size={16} /> Pelanggan baru</button>
        </div>
      )}
      {resource === 'suppliers' && canManageResource && (
        <div className="mb-4 flex justify-end">
          <button type="button" onClick={() => { setEditingSupplier(null); setSupplierDialogOpen(true) }} className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800"><Plus size={16} /> Supplier baru</button>
        </div>
      )}
      {['warehouses', 'categories', 'units'].includes(resource) && canManageResource && <div className="mb-4 flex justify-end"><button type="button" onClick={() => { setEditingReference(null); setReferenceDialogOpen(true) }} className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800"><Plus size={16} />Tambah {resource === 'warehouses' ? 'gudang' : resource === 'categories' ? 'kategori' : 'satuan'}</button></div>}
      <div className="mb-4 flex gap-2 overflow-x-auto pb-1">
        {resourceOptions.map(([key, label, Icon]) => <button key={key} onClick={() => { setLoading(true); setError(''); setResource(key) }} className={`inline-flex shrink-0 items-center gap-2 rounded-lg border px-3.5 py-2.5 text-xs font-semibold transition ${resource === key ? 'border-emerald-700 bg-emerald-700 text-white' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'}`}><Icon size={15} />{label}</button>)}
      </div>
      {visibleResource && <section className="overflow-hidden rounded-xl border border-slate-200/80 bg-white">
        <div className="border-b border-slate-100 px-5 py-4"><h2 className="text-sm font-semibold text-slate-900">{resourceOptions.find(([key]) => key === resource)?.[1]}</h2><p className="mt-1 text-xs text-slate-500">{rows.length} data ditampilkan</p></div>
        {error ? <div className="p-5"><ErrorPanel message={error} /></div> : <>
          {loading && <LoadingBar />}
          <div className="overflow-x-auto"><table className="w-full min-w-[520px] text-left">
            <thead className="bg-slate-50/80 text-[11px] font-semibold uppercase tracking-wide text-slate-500"><tr>{columns.map(([key, label]) => <th key={key} className="px-5 py-3.5">{label}</th>)}</tr></thead>
            <tbody className="divide-y divide-slate-100">{rows.map((row, index) => <tr key={String(row.id ?? index)} className="hover:bg-slate-50/70">{columns.map(([key]) => <td key={key} className="px-5 py-3.5 text-sm text-slate-600">{renderMasterDataCell(row, key)}</td>)}</tr>)}</tbody>
          </table></div>
          {!loading && rows.length === 0 && <EmptyState title="Data belum tersedia" description="Belum ada catatan untuk kategori ini." />}
        </>}
      </section>}
      {productDialogOpen && (
        <ProductEditorDialog
          product={editingProduct ?? undefined}
          onClose={() => setProductDialogOpen(false)}
          onSaved={() => { setProductDialogOpen(false); setLoading(true); setRefreshKey((value) => value + 1) }}
        />
      )}
      {customerDialogOpen && (
        <CustomerEditorDialog
          customer={editingCustomer ?? undefined}
          onClose={() => setCustomerDialogOpen(false)}
          onSaved={() => { setCustomerDialogOpen(false); setLoading(true); setRefreshKey((value) => value + 1) }}
        />
      )}
      {supplierDialogOpen && (
        <SupplierEditorDialog
          supplier={editingSupplier ?? undefined}
          onClose={() => setSupplierDialogOpen(false)}
          onSaved={() => { setSupplierDialogOpen(false); setLoading(true); setRefreshKey((value) => value + 1) }}
        />
      )}
      {referenceDialogOpen && <ReferenceDataDialog kind={resource as 'warehouses' | 'categories' | 'units'} record={editingReference ?? undefined} onClose={() => setReferenceDialogOpen(false)} onSaved={() => { setReferenceDialogOpen(false); setLoading(true); setRefreshKey((value) => value + 1) }} />}
    </>
  )
}

function ReferenceDataDialog({ kind, record, onClose, onSaved }: {
  kind: 'warehouses' | 'categories' | 'units'
  record?: Record<string, unknown>
  onClose: () => void
  onSaved: () => void
}) {
  const [code, setCode] = useState(String(record?.code ?? ''))
  const [name, setName] = useState(String(record?.name ?? ''))
  const [description, setDescription] = useState(String(record?.description ?? ''))
  const [symbol, setSymbol] = useState(String(record?.symbol ?? ''))
  const [address, setAddress] = useState(String(record?.address ?? ''))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const title = kind === 'warehouses' ? 'Gudang' : kind === 'categories' ? 'Kategori' : 'Satuan'

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    if (!name.trim() || (kind === 'warehouses' && !record && !code.trim())) {
      setError(kind === 'warehouses' && !record ? 'Kode dan nama gudang wajib diisi.' : 'Nama wajib diisi.')
      return
    }
    const body = kind === 'warehouses'
      ? { ...(record ? {} : { code: code.trim() }), name: name.trim(), address: address.trim() }
      : kind === 'categories'
        ? { name: name.trim(), description: description.trim() }
        : { name: name.trim(), symbol: symbol.trim() }
    setSaving(true)
    try {
      await apiRequest(record ? `/${kind}/${record.id}` : `/${kind}`, { method: record ? 'PATCH' : 'POST', body: JSON.stringify(body) })
      onSaved()
    } catch (failure) { setError(getErrorMessage(failure)) }
    finally { setSaving(false) }
  }

  return <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 p-0 sm:items-center sm:p-5" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><form onSubmit={(event) => void save(event)} className="w-full max-w-xl rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl"><div className="flex items-start justify-between border-b border-slate-100 px-5 py-4"><div><p className="text-[11px] font-bold tracking-widest text-emerald-700">DATA MASTER</p><h2 className="mt-1 text-lg font-semibold text-slate-900">{record ? 'Ubah' : 'Tambah'} {title.toLowerCase()}</h2></div><button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Tutup dialog"><X size={18} /></button></div><div className="grid gap-4 p-5 sm:grid-cols-2">{kind === 'warehouses' && !record && <label className="text-xs font-semibold text-slate-600">Kode gudang<input required value={code} onChange={(event) => setCode(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>}<label className={`text-xs font-semibold text-slate-600 ${kind === 'categories' ? 'sm:col-span-2' : ''}`}>Nama<input required value={name} onChange={(event) => setName(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>{kind === 'categories' && <label className="text-xs font-semibold text-slate-600 sm:col-span-2">Deskripsi<textarea rows={3} value={description} onChange={(event) => setDescription(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>}{kind === 'units' && <label className="text-xs font-semibold text-slate-600">Simbol<input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="Contoh: pcs, kg" className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>}{kind === 'warehouses' && <label className="text-xs font-semibold text-slate-600 sm:col-span-2">Alamat<textarea rows={3} value={address} onChange={(event) => setAddress(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>}{error && <p role="alert" className="rounded-lg border border-rose-100 bg-rose-50 px-3 py-2.5 text-sm text-rose-700 sm:col-span-2">{error}</p>}</div><div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-4"><button type="button" onClick={onClose} className="rounded-lg px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-100">Batal</button><button disabled={saving} className="rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{saving ? 'Menyimpan…' : 'Simpan'}</button></div></form></div>
}

function CustomerEditorDialog({
  customer,
  onClose,
  onSaved,
}: {
  customer?: PartnerRecord
  onClose: () => void
  onSaved: () => void
}) {
  const [name, setName] = useState(customer?.name ?? '')
  const [email, setEmail] = useState(customer?.email ?? '')
  const [phone, setPhone] = useState(customer?.phone ?? '')
  const [address, setAddress] = useState(customer?.address ?? '')
  const [isActive, setIsActive] = useState(customer?.is_active ?? true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function saveCustomer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    if (!name.trim()) {
      setError('Nama pelanggan wajib diisi.')
      return
    }
    setSaving(true)
    try {
      await apiRequest(customer ? `/customers/${customer.id}` : '/customers', {
        method: customer ? 'PATCH' : 'POST',
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim() || null,
          phone: phone.trim() || null,
          address: address.trim() || null,
          ...(customer ? { is_active: isActive } : {}),
        }),
      })
      onSaved()
    } catch (failure) {
      setError(getErrorMessage(failure))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 p-0 sm:items-center sm:p-5" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <form onSubmit={(event) => void saveCustomer(event)} className="max-h-[92vh] w-full max-w-xl overflow-y-auto rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl">
        <div className="flex items-start justify-between border-b border-slate-100 px-5 py-4 sm:px-6">
          <div><p className="text-[11px] font-bold tracking-widest text-emerald-700">DATA PELANGGAN</p><h2 className="mt-1 text-lg font-semibold text-slate-900">{customer ? 'Ubah pelanggan' : 'Tambah pelanggan'}</h2><p className="mt-1 text-xs text-slate-500">{customer ? `Kode ${customer.code}` : 'Kode pelanggan akan dibuat otomatis saat disimpan.'}</p></div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Tutup dialog"><X size={18} /></button>
        </div>
        <div className="grid grid-cols-1 gap-4 px-5 py-5 sm:grid-cols-2 sm:px-6">
          <label className="text-xs font-semibold text-slate-600 sm:col-span-2">Nama pelanggan<input required maxLength={100} autoFocus value={name} onChange={(event) => setName(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" /></label>
          <label className="text-xs font-semibold text-slate-600">Email<input type="email" maxLength={120} value={email} onChange={(event) => setEmail(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" /></label>
          <label className="text-xs font-semibold text-slate-600">Nomor telepon<input type="tel" maxLength={20} value={phone} onChange={(event) => setPhone(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" /></label>
          <label className="text-xs font-semibold text-slate-600 sm:col-span-2">Alamat<textarea rows={3} value={address} onChange={(event) => setAddress(event.target.value)} className="mt-2 w-full resize-y rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" /></label>
          {customer && <label className="flex items-center gap-2 text-sm text-slate-700 sm:col-span-2"><input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} className="accent-emerald-700" />Pelanggan aktif</label>}
          {error && <p role="alert" className="rounded-lg border border-rose-100 bg-rose-50 px-3 py-2.5 text-sm text-rose-700 sm:col-span-2">{error}</p>}
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-4 sm:px-6"><button type="button" onClick={onClose} className="rounded-lg px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100">Batal</button><button disabled={saving} className="rounded-lg bg-[#087e63] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#066b55] disabled:opacity-50">{saving ? 'Menyimpan…' : 'Simpan pelanggan'}</button></div>
      </form>
    </div>
  )
}

function SupplierEditorDialog({
  supplier,
  onClose,
  onSaved,
}: {
  supplier?: PartnerRecord
  onClose: () => void
  onSaved: () => void
}) {
  const [name, setName] = useState(supplier?.name ?? '')
  const [email, setEmail] = useState(supplier?.email ?? '')
  const [phone, setPhone] = useState(supplier?.phone ?? '')
  const [address, setAddress] = useState(supplier?.address ?? '')
  const [isActive, setIsActive] = useState(supplier?.is_active ?? true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function saveSupplier(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    if (!name.trim()) { setError('Nama supplier wajib diisi.'); return }
    setSaving(true)
    try {
      await apiRequest(supplier ? `/suppliers/${supplier.id}` : '/suppliers', {
        method: supplier ? 'PATCH' : 'POST',
        body: JSON.stringify({ name: name.trim(), email: email.trim() || null, phone: phone.trim() || null, address: address.trim() || null, ...(supplier ? { is_active: isActive } : {}) }),
      })
      onSaved()
    } catch (failure) {
      setError(getErrorMessage(failure))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 p-0 sm:items-center sm:p-5" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <form onSubmit={(event) => void saveSupplier(event)} className="max-h-[92vh] w-full max-w-xl overflow-y-auto rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl">
        <div className="flex items-start justify-between border-b border-slate-100 px-5 py-4 sm:px-6"><div><p className="text-[11px] font-bold tracking-widest text-emerald-700">DATA SUPPLIER</p><h2 className="mt-1 text-lg font-semibold text-slate-900">{supplier ? 'Ubah supplier' : 'Tambah supplier'}</h2><p className="mt-1 text-xs text-slate-500">{supplier ? `Kode ${supplier.code}` : 'Kode supplier akan dibuat otomatis saat disimpan.'}</p></div><button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Tutup dialog"><X size={18} /></button></div>
        <div className="grid grid-cols-1 gap-4 px-5 py-5 sm:grid-cols-2 sm:px-6">
          <label className="text-xs font-semibold text-slate-600 sm:col-span-2">Nama supplier<input required maxLength={100} autoFocus value={name} onChange={(event) => setName(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" /></label>
          <label className="text-xs font-semibold text-slate-600">Email<input type="email" maxLength={120} value={email} onChange={(event) => setEmail(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" /></label>
          <label className="text-xs font-semibold text-slate-600">Nomor telepon<input type="tel" maxLength={20} value={phone} onChange={(event) => setPhone(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" /></label>
          <label className="text-xs font-semibold text-slate-600 sm:col-span-2">Alamat<textarea rows={3} value={address} onChange={(event) => setAddress(event.target.value)} className="mt-2 w-full resize-y rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" /></label>
          {supplier && <label className="flex items-center gap-2 text-sm text-slate-700 sm:col-span-2"><input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} className="accent-emerald-700" />Supplier aktif</label>}
          {error && <p role="alert" className="rounded-lg border border-rose-100 bg-rose-50 px-3 py-2.5 text-sm text-rose-700 sm:col-span-2">{error}</p>}
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-4 sm:px-6"><button type="button" onClick={onClose} className="rounded-lg px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100">Batal</button><button disabled={saving} className="rounded-lg bg-[#087e63] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#066b55] disabled:opacity-50">{saving ? 'Menyimpan…' : 'Simpan supplier'}</button></div>
      </form>
    </div>
  )
}

function ProductEditorDialog({
  product,
  onClose,
  onSaved,
}: {
  product?: ProductRecord
  onClose: () => void
  onSaved: () => void
}) {
  const [sku, setSku] = useState(product?.sku ?? '')
  const [name, setName] = useState(product?.name ?? '')
  const [salesPrice, setSalesPrice] = useState(product?.sales_price == null ? '' : String(product.sales_price))
  const [minStock, setMinStock] = useState(String(product?.min_stock ?? 0))
  const [categoryId, setCategoryId] = useState(product?.category_id == null ? '' : String(product.category_id))
  const [unitId, setUnitId] = useState(product?.unit_id == null ? '' : String(product.unit_id))
  const [categories, setCategories] = useState<CategoryOption[]>([])
  const [units, setUnits] = useState<UnitOption[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([
      apiRequest<{ data: CategoryOption[] }>('/categories?per_page=100'),
      apiRequest<{ data: UnitOption[] }>('/units?per_page=100'),
    ]).then(([categoryResponse, unitResponse]) => {
      if (!active) return
      setCategories(categoryResponse.data)
      setUnits(unitResponse.data)
    }).catch((failure: unknown) => {
      if (active) setError(getErrorMessage(failure))
    })
    return () => { active = false }
  }, [])

  async function saveProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    const price = Number(salesPrice)
    const stock = Number(minStock)
    if (!Number.isFinite(price) || price < 0 || !Number.isFinite(stock) || stock < 0) {
      setError('Harga jual dan minimum stok harus berupa angka nol atau lebih.')
      return
    }
    setSaving(true)
    try {
      await apiRequest(product ? `/products/${product.id}` : '/products', {
        method: product ? 'PATCH' : 'POST',
        body: JSON.stringify({
          sku: sku.trim(),
          name: name.trim(),
          sales_price: price,
          min_stock: stock,
          category_id: categoryId ? Number(categoryId) : null,
          unit_id: unitId ? Number(unitId) : null,
        }),
      })
      onSaved()
    } catch (failure) {
      setError(getErrorMessage(failure))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 p-0 sm:items-center sm:p-5" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <form onSubmit={(event) => void saveProduct(event)} className="max-h-[92vh] w-full max-w-xl overflow-y-auto rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl">
        <div className="flex items-start justify-between border-b border-slate-100 px-5 py-4 sm:px-6">
          <div><p className="text-[11px] font-bold tracking-widest text-emerald-700">KATALOG PRODUK</p><h2 className="mt-1 text-lg font-semibold text-slate-900">{product ? 'Ubah produk' : 'Tambah produk'}</h2></div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Tutup dialog"><X size={18} /></button>
        </div>
        <div className="grid grid-cols-1 gap-4 px-5 py-5 sm:grid-cols-2 sm:px-6">
          <label className="text-xs font-semibold text-slate-600">SKU<input required maxLength={50} value={sku} onChange={(event) => setSku(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
          <label className="text-xs font-semibold text-slate-600">Nama produk<input required maxLength={100} value={name} onChange={(event) => setName(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
          <label className="text-xs font-semibold text-slate-600">Harga jual default<input required type="number" min="0" step="0.01" value={salesPrice} onChange={(event) => setSalesPrice(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
          <label className="text-xs font-semibold text-slate-600">Minimum stok<input required type="number" min="0" step="0.0001" value={minStock} onChange={(event) => setMinStock(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal" /></label>
          <label className="text-xs font-semibold text-slate-600">Kategori<select value={categoryId} onChange={(event) => setCategoryId(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal"><option value="">Tanpa kategori</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
          <label className="text-xs font-semibold text-slate-600">Satuan<select value={unitId} onChange={(event) => setUnitId(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal"><option value="">Tanpa satuan</option>{units.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}{unit.symbol ? ` (${unit.symbol})` : ''}</option>)}</select></label>
          {error && <p role="alert" className="rounded-lg border border-rose-100 bg-rose-50 px-3 py-2.5 text-sm text-rose-700 sm:col-span-2">{error}</p>}
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-4 sm:px-6"><button type="button" onClick={onClose} className="rounded-lg px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100">Batal</button><button disabled={saving} className="rounded-lg bg-[#087e63] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#066b55] disabled:opacity-50">{saving ? 'Menyimpan…' : 'Simpan produk'}</button></div>
      </form>
    </div>
  )
}

function AccountSettingsPage({
  session,
  warehouses,
  onProfileUpdated,
}: {
  session: AuthSession
  warehouses: WarehouseRecord[]
  onProfileUpdated: (session: AuthSession) => void
}) {
  const [username, setUsername] = useState(session.username)
  const [email, setEmail] = useState(session.email)
  const [profilePassword, setProfilePassword] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [profileSaving, setProfileSaving] = useState(false)
  const [passwordSaving, setPasswordSaving] = useState(false)
  const [profileError, setProfileError] = useState('')
  const [passwordError, setPasswordError] = useState('')

  async function updateProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setProfileError('')
    setProfileSaving(true)
    try {
      const response = await apiRequest<{ data: Partial<AuthSession> }>('/auth/me', {
        method: 'PATCH',
        body: JSON.stringify({
          username: username.trim(),
          email: email.trim(),
          current_password: profilePassword,
        }),
      })
      onProfileUpdated({ ...session, ...response.data })
      setProfilePassword('')
    } catch (failure) {
      setProfileError(getErrorMessage(failure))
    } finally {
      setProfileSaving(false)
    }
  }

  async function updatePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPasswordError('')
    if (newPassword !== confirmPassword) {
      setPasswordError('Konfirmasi kata sandi baru tidak cocok.')
      return
    }
    setPasswordSaving(true)
    try {
      const response = await apiRequest<{ data: Partial<AuthSession> }>('/auth/me', {
        method: 'PATCH',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          refresh_token: session.refresh_token,
        }),
      })
      onProfileUpdated({ ...session, ...response.data })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setPasswordError('')
    } catch (failure) {
      setPasswordError(getErrorMessage(failure))
    } finally {
      setPasswordSaving(false)
    }
  }

  const accessibleWarehouseNames = session.all_warehouses
    ? 'Semua gudang'
    : warehouses
        .filter((warehouse) => session.warehouse_ids.includes(warehouse.id))
        .map((warehouse) => warehouse.name)
        .join(', ') || 'Belum ditetapkan'

  return (
    <>
      <PageHeading
        eyebrow="PREFERENSI AKUN"
        title="Akun & keamanan"
        description="Perbarui identitas login dan jaga keamanan akun Anda."
      />

      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <StatCard title="Role" value={roleNames[session.role] ?? session.role} detail="Role akses akun" icon={ShieldCheck} tone="blue" />
        <StatCard title="Cakupan gudang" value={session.all_warehouses ? 'Semua gudang' : numberFormat.format(session.warehouse_ids.length)} detail={accessibleWarehouseNames} icon={WarehouseIcon} tone="green" />
        <StatCard title="Email akun" value={session.email} detail="Digunakan untuk identifikasi akun" icon={Users} tone="purple" />
      </div>

      <div className="grid items-start gap-5 xl:grid-cols-2">
        <form onSubmit={(event) => void updateProfile(event)} className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="border-b border-slate-100 px-5 py-4">
            <h2 className="text-sm font-semibold text-slate-900">Informasi akun</h2>
            <p className="mt-1 text-xs text-slate-500">Perubahan username dan email memerlukan konfirmasi kata sandi saat ini.</p>
          </div>
          <div className="space-y-4 px-5 py-5">
            <label className="block text-xs font-semibold text-slate-600">
              Username
              <input required minLength={1} maxLength={50} autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Email
              <input required type="email" maxLength={100} autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Kata sandi saat ini
              <input required type="password" autoComplete="current-password" value={profilePassword} onChange={(event) => setProfilePassword(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" />
            </label>
            {profileError && <ErrorPanel message={profileError} />}
          </div>
          <div className="flex justify-end border-t border-slate-100 px-5 py-4">
            <button disabled={profileSaving} className="rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">
              {profileSaving ? 'Menyimpan…' : 'Simpan profil'}
            </button>
          </div>
        </form>

        <form onSubmit={(event) => void updatePassword(event)} className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="border-b border-slate-100 px-5 py-4">
            <h2 className="text-sm font-semibold text-slate-900">Ubah kata sandi</h2>
            <p className="mt-1 text-xs text-slate-500">Gunakan minimal 12 karakter. Sesi ini akan diperbarui setelah berhasil.</p>
          </div>
          <div className="space-y-4 px-5 py-5">
            <label className="block text-xs font-semibold text-slate-600">
              Kata sandi saat ini
              <input required type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Kata sandi baru
              <input required type="password" minLength={12} autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Konfirmasi kata sandi baru
              <input required type="password" minLength={12} autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" />
            </label>
            {passwordError && <ErrorPanel message={passwordError} />}
          </div>
          <div className="flex justify-end border-t border-slate-100 px-5 py-4">
            <button disabled={passwordSaving} className="rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">
              {passwordSaving ? 'Memperbarui…' : 'Ubah kata sandi'}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}

function AccessManagementPage({
  onNotice,
  onRolePermissionsSaved,
}: {
  onNotice: (message: string) => void
  onRolePermissionsSaved: (roleCode: string, permissions: string[]) => void
}) {
  const [tab, setTab] = useState<'users' | 'roles'>('users')
  const [users, setUsers] = useState<ManagedUser[]>([])
  const [warehouses, setWarehouses] = useState<WarehouseRecord[]>([])
  const [roles, setRoles] = useState<RoleRecord[]>([])
  const [permissions, setPermissions] = useState<PermissionRecord[]>([])
  const [selectedRole, setSelectedRole] = useState('viewer')
  const selectedRoleRef = useRef(selectedRole)
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<ManagedUser | null>(null)
  const [selectedWarehouseIds, setSelectedWarehouseIds] = useState<number[]>([])
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('viewer')

  const loadAccessData = useCallback(async () => {
    try {
      const [userResult, roleResult, permissionResult, warehouseResult] = await Promise.all([
        apiRequest<PageResult<ManagedUser>>('/users?per_page=100'),
        getApiData<RoleRecord[]>('/roles'),
        getApiData<PermissionRecord[]>('/permissions'),
        getApiData<WarehouseRecord[]>('/warehouses?per_page=100'),
      ])
      setUsers(userResult.data)
      setRoles(roleResult.data)
      setPermissions(permissionResult.data)
      setWarehouses(warehouseResult.data.filter((warehouse) => warehouse.is_active !== false))
      const currentRole = roleResult.data.find((item) => item.code === selectedRoleRef.current)
        ?? roleResult.data[0]
      if (currentRole) {
        selectedRoleRef.current = currentRole.code
        setSelectedRole(currentRole.code)
        setSelectedPermissions(currentRole.permissions)
      }
      setError('')
    } catch (failure) {
      setError(getErrorMessage(failure))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void Promise.resolve().then(loadAccessData)
  }, [loadAccessData])

  function selectRole(roleCode: string) {
    selectedRoleRef.current = roleCode
    setSelectedRole(roleCode)
    setSelectedPermissions(roles.find((item) => item.code === roleCode)?.permissions ?? [])
  }

  function togglePermission(code: string) {
    setSelectedPermissions((current) =>
      current.includes(code)
        ? current.filter((permission) => permission !== code)
        : [...current, code],
    )
  }

  function openCreateUser() {
    setError('')
    setUsername('')
    setEmail('')
    setPassword('')
    setRole('viewer')
    setSelectedWarehouseIds([])
    setCreateOpen(true)
  }

  function openWarehouseScopeEditor(user: ManagedUser) {
    setError('')
    setSelectedWarehouseIds(user.warehouse_ids)
    setEditingUser(user)
  }

  function toggleWarehouse(id: number) {
    setSelectedWarehouseIds((current) => current.includes(id)
      ? current.filter((warehouseId) => warehouseId !== id)
      : [...current, id])
  }

  async function createUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (role !== 'admin' && selectedWarehouseIds.length === 0) {
      setError('Pilih minimal satu gudang untuk akun ini.')
      return
    }
    setSaving(true)
    setError('')
    try {
      await apiRequest('/users', {
        method: 'POST',
        body: JSON.stringify({
          username: username.trim(),
          email: email.trim(),
          password,
          role,
          all_warehouses: role === 'admin',
          warehouse_ids: role === 'admin' ? [] : selectedWarehouseIds,
        }),
      })
      setCreateOpen(false)
      setUsername('')
      setEmail('')
      setPassword('')
      setRole('viewer')
      setSelectedWarehouseIds([])
      setLoading(true)
      await loadAccessData()
      onNotice('Pengguna baru berhasil ditambahkan.')
    } catch (failure) {
      setError(getErrorMessage(failure))
    } finally {
      setSaving(false)
    }
  }

  async function saveWarehouseScope(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editingUser) return
    if (selectedWarehouseIds.length === 0) {
      setError('Pilih minimal satu gudang untuk akun ini.')
      return
    }
    setSaving(true)
    setError('')
    try {
      const result = await apiRequest<{ data: ManagedUser }>(`/users/${editingUser.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ warehouse_ids: selectedWarehouseIds, all_warehouses: false }),
      })
      setUsers((current) => current.map((user) => user.id === result.data.id ? result.data : user))
      setEditingUser(null)
      onNotice(`Cakupan gudang ${result.data.username} berhasil diperbarui.`)
    } catch (failure) {
      setError(getErrorMessage(failure))
    } finally {
      setSaving(false)
    }
  }

  async function savePermissions() {
    setSaving(true)
    setError('')
    try {
      const result = await apiRequest<{ data: RoleRecord }>(
        `/roles/${encodeURIComponent(selectedRole)}/permissions`,
        {
          method: 'PUT',
          body: JSON.stringify({ permissions: selectedPermissions }),
        },
      )
      setRoles((current) => current.map((item) => item.code === result.data.code ? result.data : item))
      setSelectedPermissions(result.data.permissions)
      onRolePermissionsSaved(result.data.code, result.data.permissions)
      onNotice(`Permission role ${result.data.name} berhasil diperbarui.`)
    } catch (failure) {
      setError(getErrorMessage(failure))
    } finally {
      setSaving(false)
    }
  }

  const permissionsByModule = permissions.reduce<Record<string, PermissionRecord[]>>((grouped, permission) => {
    grouped[permission.module] = [...(grouped[permission.module] ?? []), permission]
    return grouped
  }, {})

  return (
    <>
      <PageHeading
        eyebrow="PENGATURAN AKSES"
        title="Pengguna & role"
        description="Kelola akun yang dapat masuk ke DistribuFlow dan atur izin setiap role."
        action={
          tab === 'users' ? (
            <button onClick={openCreateUser} className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-800">
              <Plus size={16} /> Tambah pengguna
            </button>
          ) : undefined
        }
      />

      <div className="mb-5 flex gap-2 border-b border-slate-200">
        {[
          { id: 'users' as const, label: 'Pengguna', icon: Users },
          { id: 'roles' as const, label: 'Role & permission', icon: ShieldCheck },
        ].map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => { setTab(id); setError('') }} className={`inline-flex items-center gap-2 border-b-2 px-3 py-3 text-sm font-semibold transition ${tab === id ? 'border-emerald-700 text-emerald-800' : 'border-transparent text-slate-500 hover:text-slate-800'}`}>
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>

      {error && <div className="mb-4"><ErrorPanel message={error} /></div>}
      {loading ? <LoadingBar /> : tab === 'users' ? (
        <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-4 sm:px-5">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Daftar pengguna</h2>
              <p className="mt-1 text-xs text-slate-500">{users.length} akun ditampilkan</p>
            </div>
            <Users size={18} className="text-slate-400" />
          </div>
          {users.length ? (
            <>
              <div className="hidden overflow-x-auto md:block">
                <table className="w-full min-w-[860px] text-left">
                  <thead className="bg-slate-50 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-5 py-3">Pengguna</th>
                      <th className="px-4 py-3">Role</th>
                      <th className="px-4 py-3">Cakupan gudang</th>
                      <th className="px-5 py-3">Status</th>
                      <th className="px-5 py-3 text-right">Pengaturan</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {users.map((user) => (
                      <tr key={user.id}>
                        <td className="px-5 py-3.5">
                          <p className="text-sm font-semibold text-slate-800">{user.username}</p>
                          <p className="mt-0.5 text-xs text-slate-500">{user.email}</p>
                        </td>
                        <td className="px-4 py-3.5"><StatusBadge status={user.role} /></td>
                        <td className="px-4 py-3.5 text-xs text-slate-600">{user.all_warehouses ? 'Semua gudang' : user.warehouse_ids.map((id) => warehouses.find((warehouse) => warehouse.id === id)?.code ?? `#${id}`).join(', ') || 'Belum ditetapkan'}</td>
                        <td className="px-5 py-3.5"><StatusBadge status={user.is_active ? 'ACTIVE' : 'INACTIVE'} /></td>
                        <td className="px-5 py-3.5 text-right">{!user.all_warehouses && <button type="button" onClick={() => openWarehouseScopeEditor(user)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-800">Atur gudang</button>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="divide-y divide-slate-100 md:hidden">
                {users.map((user) => (
                  <div key={user.id} className="space-y-2 px-4 py-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-slate-800">{user.username}</p>
                        <p className="truncate text-xs text-slate-500">{user.email}</p>
                      </div>
                      <StatusBadge status={user.is_active ? 'ACTIVE' : 'INACTIVE'} />
                    </div>
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <StatusBadge status={user.role} />
                      <span>{user.all_warehouses ? 'Semua gudang' : user.warehouse_ids.map((id) => warehouses.find((warehouse) => warehouse.id === id)?.code ?? `#${id}`).join(', ') || 'Belum ditetapkan'}</span>
                    </div>
                    {!user.all_warehouses && <button type="button" onClick={() => openWarehouseScopeEditor(user)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-800">Atur gudang</button>}
                  </div>
                ))}
              </div>
            </>
          ) : <EmptyState title="Belum ada pengguna" description="Buat akun pengguna pertama untuk mulai mengelola akses." />}
        </section>
      ) : (
        <div className="grid items-start gap-5 lg:grid-cols-[260px_1fr]">
          <section className="rounded-xl border border-slate-200 bg-white p-3">
            <p className="px-2 pb-2 pt-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">Pilih role</p>
            <div className="space-y-1">
              {roles.map((item) => (
                <button key={item.code} onClick={() => selectRole(item.code)} className={`flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm transition ${selectedRole === item.code ? 'bg-emerald-50 font-semibold text-emerald-800' : 'text-slate-600 hover:bg-slate-50'}`}>
                  <span>{item.name}</span>
                  <span className="text-[10px] text-slate-400">{item.permissions.length}</span>
                </button>
              ))}
            </div>
          </section>
          <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <div className="flex flex-col gap-3 border-b border-slate-100 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">{roles.find((item) => item.code === selectedRole)?.name ?? 'Permission role'}</h2>
                <p className="mt-1 text-xs text-slate-500">{roles.find((item) => item.code === selectedRole)?.description ?? 'Pilih izin yang tersedia untuk role ini.'}</p>
              </div>
              <button disabled={saving || !selectedRole} onClick={() => void savePermissions()} className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-700 px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-emerald-800 disabled:opacity-50">
                <ShieldCheck size={14} /> {saving ? 'Menyimpan…' : 'Simpan permission'}
              </button>
            </div>
            <div className="divide-y divide-slate-100">
              {Object.entries(permissionsByModule).map(([module, modulePermissions]) => (
                <div key={module} className="px-4 py-4 sm:px-5">
                  <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-500">{module.replaceAll('_', ' ')}</h3>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {modulePermissions.map((permission) => (
                      <label key={permission.code} className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-100 px-3 py-2.5 transition hover:border-emerald-200 hover:bg-emerald-50/40">
                        <input
                          type="checkbox"
                          checked={selectedRole === 'admin' || selectedPermissions.includes(permission.code)}
                          onChange={() => togglePermission(permission.code)}
                          disabled={permission.code === 'profile.read' || selectedRole === 'admin'}
                          className="mt-0.5 accent-emerald-700"
                        />
                        <span className="min-w-0">
                          <span className="block text-xs font-medium text-slate-700">{permission.name}</span>
                          <span className="mt-0.5 block break-all text-[10px] text-slate-400">{permission.code}{permission.warehouse_scoped ? ' · cakupan gudang' : ''}</span>
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}

      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 p-0 sm:items-center sm:p-5" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) setCreateOpen(false) }}>
          <form onSubmit={(event) => void createUser(event)} className="max-h-[92vh] w-full max-w-xl overflow-y-auto rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl">
            <div className="flex items-start justify-between border-b border-slate-100 px-5 py-4 sm:px-6">
              <div>
                <p className="text-[10px] font-bold tracking-widest text-emerald-700">MANAJEMEN AKSES</p>
                <h2 className="mt-1 text-lg font-semibold text-slate-900">Tambah pengguna</h2>
                <p className="mt-1 text-xs text-slate-500">Buat akun dan tentukan role serta cakupan gudangnya.</p>
              </div>
              <button type="button" disabled={saving} onClick={() => setCreateOpen(false)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 disabled:opacity-50" aria-label="Tutup dialog"><X size={18} /></button>
            </div>
            <div className="space-y-4 px-5 py-5 sm:px-6">
              <label className="block text-xs font-semibold text-slate-600">Username
                <input required maxLength={50} autoComplete="off" value={username} onChange={(event) => setUsername(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" />
              </label>
              <label className="block text-xs font-semibold text-slate-600">Email
                <input required type="email" maxLength={100} autoComplete="off" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" />
              </label>
              <label className="block text-xs font-semibold text-slate-600">Password sementara
                <input required type="password" minLength={12} autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" />
                <span className="mt-1 block text-[10px] font-normal text-slate-400">Minimal 12 karakter. Sampaikan secara aman kepada pengguna.</span>
              </label>
              <label className="block text-xs font-semibold text-slate-600">Role
                <select value={role} onChange={(event) => { setRole(event.target.value); if (event.target.value === 'admin') setSelectedWarehouseIds([]) }} className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500">
                  {roles.map((item) => <option key={item.code} value={item.code}>{item.name}</option>)}
                </select>
              </label>
              {role === 'admin' ? (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-xs leading-5 text-emerald-900">Admin otomatis mendapat akses ke semua gudang.</div>
              ) : (
                <fieldset className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <legend className="px-1 text-xs font-semibold text-slate-700">Cakupan gudang</legend>
                  <p className="mb-3 text-xs leading-5 text-slate-500">Pilih gudang yang boleh diakses pengguna. Untuk membuat atau menyetujui transfer, akun perlu mencakup gudang asal dan tujuan.</p>
                  <div className="grid max-h-44 gap-2 overflow-y-auto sm:grid-cols-2">
                    {warehouses.map((warehouse) => (
                      <label key={warehouse.id} className="flex min-w-0 cursor-pointer items-start gap-2.5 rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-xs text-slate-700 transition hover:border-emerald-300">
                        <input type="checkbox" checked={selectedWarehouseIds.includes(warehouse.id)} onChange={() => toggleWarehouse(warehouse.id)} className="mt-0.5 accent-emerald-700" />
                        <span className="min-w-0"><span className="block truncate font-semibold">{warehouse.code}</span><span className="mt-0.5 block truncate text-slate-500">{warehouse.name}</span></span>
                      </label>
                    ))}
                    {warehouses.length === 0 && <p className="text-xs text-slate-500">Tidak ada gudang aktif.</p>}
                  </div>
                  <p className="mt-3 text-[11px] font-medium text-slate-600">{selectedWarehouseIds.length} gudang dipilih</p>
                </fieldset>
              )}
              {error && <p role="alert" className="rounded-lg border border-rose-100 bg-rose-50 px-3 py-2.5 text-sm text-rose-700">{error}</p>}
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-4 sm:px-6">
              <button type="button" disabled={saving} onClick={() => setCreateOpen(false)} className="rounded-lg px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100">Batal</button>
              <button disabled={saving} className="rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">{saving ? 'Menyimpan…' : 'Buat pengguna'}</button>
            </div>
          </form>
        </div>
      )}
      {editingUser && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/45 p-0 backdrop-blur-[2px] sm:items-center sm:p-5" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) setEditingUser(null) }}>
          <form onSubmit={(event) => void saveWarehouseScope(event)} className="max-h-[92vh] w-full max-w-xl overflow-y-auto rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl">
            <div className="flex items-start justify-between border-b border-slate-100 px-5 py-4 sm:px-6">
              <div>
                <p className="text-[10px] font-bold tracking-widest text-emerald-700">CAKUPAN AKSES</p>
                <h2 className="mt-1 text-lg font-semibold text-slate-900">Gudang untuk {editingUser.username}</h2>
                <p className="mt-1 text-xs text-slate-500">Pilih gudang yang boleh dilihat dan diproses oleh akun ini.</p>
              </div>
              <button type="button" disabled={saving} onClick={() => setEditingUser(null)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 disabled:opacity-50" aria-label="Tutup dialog"><X size={18} /></button>
            </div>
            <div className="space-y-4 px-5 py-5 sm:px-6">
              <div className="rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-xs leading-5 text-emerald-900">
                Untuk transfer antargudang, staf yang membuat/mem-posting dan Manager yang menyetujui perlu memiliki akses ke gudang asal serta tujuan.
              </div>
              <fieldset className="rounded-xl border border-slate-200 p-4">
                <legend className="px-1 text-xs font-semibold text-slate-700">Gudang yang diizinkan</legend>
                <div className="grid max-h-64 gap-2 overflow-y-auto sm:grid-cols-2">
                  {warehouses.map((warehouse) => (
                    <label key={warehouse.id} className="flex min-w-0 cursor-pointer items-start gap-2.5 rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-xs text-slate-700 transition hover:border-emerald-300 hover:bg-emerald-50/40">
                      <input type="checkbox" checked={selectedWarehouseIds.includes(warehouse.id)} onChange={() => toggleWarehouse(warehouse.id)} className="mt-0.5 accent-emerald-700" />
                      <span className="min-w-0"><span className="block truncate font-semibold">{warehouse.code}</span><span className="mt-0.5 block truncate text-slate-500">{warehouse.name}</span></span>
                    </label>
                  ))}
                  {warehouses.length === 0 && <p className="text-xs text-slate-500">Tidak ada gudang aktif.</p>}
                </div>
                <p className="mt-3 text-[11px] font-medium text-slate-600">{selectedWarehouseIds.length} gudang dipilih</p>
              </fieldset>
              {error && <p role="alert" className="rounded-lg border border-rose-100 bg-rose-50 px-3 py-2.5 text-sm text-rose-700">{error}</p>}
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-4 sm:px-6">
              <button type="button" disabled={saving} onClick={() => setEditingUser(null)} className="rounded-lg px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100">Batal</button>
              <button disabled={saving || selectedWarehouseIds.length === 0} className="rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">{saving ? 'Menyimpan…' : 'Simpan cakupan'}</button>
            </div>
          </form>
        </div>
      )}
    </>
  )
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toUpperCase()
  const labels: Record<string, string> = {
    DRAFT: 'Draf',
    PENDING: 'Menunggu proses',
    SUBMITTED: 'Diajukan',
    APPROVED: 'Disetujui',
    REJECTED: 'Ditolak',
    RESERVED: 'Stok dipesan',
    PARTIALLY_SHIPPED: 'Terkirim sebagian',
    SHIPPED: 'Terkirim',
    INVOICED: 'Sudah ditagih',
    PARTIALLY_RECEIVED: 'Diterima sebagian',
    RECEIVED: 'Diterima',
    POSTED: 'Diposting',
    IN_TRANSIT: 'Dalam perjalanan',
    CLOSED: 'Selesai',
    COMPLETED: 'Selesai',
    CANCELLED: 'Dibatalkan',
    OPEN: 'Belum lunas',
    PARTIALLY_PAID: 'Dibayar sebagian',
    PAID: 'Lunas',
    OVERDUE: 'Jatuh tempo',
    ACTIVE: 'Aktif',
    INACTIVE: 'Nonaktif',
  }
  const styles: Record<string, string> = {
    RESERVED: 'bg-blue-50 text-blue-700 ring-blue-600/10',
    SUBMITTED: 'bg-amber-50 text-amber-700 ring-amber-600/10',
    APPROVED: 'bg-indigo-50 text-indigo-700 ring-indigo-600/10',
    PARTIALLY_SHIPPED: 'bg-orange-50 text-orange-700 ring-orange-600/10',
    SHIPPED: 'bg-emerald-50 text-emerald-700 ring-emerald-600/10',
    INVOICED: 'bg-violet-50 text-violet-700 ring-violet-600/10',
    CLOSED: 'bg-slate-100 text-slate-700 ring-slate-600/10',
    CANCELLED: 'bg-rose-50 text-rose-700 ring-rose-600/10',
    REJECTED: 'bg-rose-50 text-rose-700 ring-rose-600/10',
    DRAFT: 'bg-slate-100 text-slate-600 ring-slate-500/10',
    OPEN: 'bg-amber-50 text-amber-700 ring-amber-600/10',
    PARTIALLY_PAID: 'bg-orange-50 text-orange-700 ring-orange-600/10',
    PAID: 'bg-emerald-50 text-emerald-700 ring-emerald-600/10',
    ACTIVE: 'bg-emerald-50 text-emerald-700 ring-emerald-600/10',
    INACTIVE: 'bg-slate-100 text-slate-500 ring-slate-500/10',
  }
  return <span className={`inline-flex whitespace-nowrap rounded-full px-2.5 py-1 text-[10px] font-semibold ring-1 ring-inset ${styles[normalized] ?? 'bg-slate-100 text-slate-600 ring-slate-500/10'}`} title={normalized.replaceAll('_', ' ')}>{labels[normalized] ?? normalized.replaceAll('_', ' ')}</span>
}

function LoadingBar() {
  return <div className="h-0.5 w-full overflow-hidden bg-emerald-50"><div className="h-full w-1/3 animate-pulse bg-emerald-500" /></div>
}

function ErrorPanel({ message }: { message: string }) {
  return <div role="alert" className="rounded-lg border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700">{message}</div>
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="flex flex-col items-center px-5 py-10 text-center">
    <div className="flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-400"><ClipboardList size={20} /></div>
    <p className="mt-3 text-sm font-semibold text-slate-700">{title}</p>
    <p className="mt-1 max-w-xs text-xs leading-5 text-slate-500">{description}</p>
  </div>
}

export default App
