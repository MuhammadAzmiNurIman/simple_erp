# PRODUCT REQUIREMENTS DOCUMENT (PRD)
## DistribuFlow ERP

**Versi:** 1.1  
**Status:** Draft — revisi berdasarkan keputusan produk  
**Jenis Produk:** Web-based Enterprise Resource Planning  
**Target Pengguna:** Perusahaan distributor kecil hingga menengah  
**Tujuan:** Proyek portofolio Full-Stack Developer

**Perubahan utama versi 1.1**
- Database ditetapkan menggunakan MySQL.
- Sistem mendukung beberapa gudang dalam satu perusahaan.
- Modul keuangan dibatasi pada simple-finance.
- Relasi produk, gudang, stok, dan transaksi diperjelas.
- API, permission, dan laporan disesuaikan untuk multi-warehouse.
- Batasan migrasi dan perlindungan data diperjelas.

---

# 1. Ringkasan Produk

## 1.1 Deskripsi

DistribuFlow ERP adalah aplikasi ERP berbasis web untuk mengelola proses bisnis perusahaan distributor secara terintegrasi, meliputi pengadaan barang, penerimaan dan penyimpanan barang, penjualan, pengiriman, penagihan, pembayaran, serta pelaporan operasional.

Aplikasi mendukung satu perusahaan dengan beberapa gudang. Setiap gudang mempunyai saldo inventaris sendiri, sedangkan data produk, pelanggan, supplier, pengguna, dan transaksi dikelola secara terpusat.

Sistem dibangun menggunakan React.js dan TypeScript, Python Flask, SQLAlchemy, dan MySQL.

## 1.2 Tujuan

1. Mengintegrasikan purchasing, inventory, sales, dan simple-finance.
2. Menyediakan informasi stok yang akurat per gudang.
3. Memastikan transaksi pembelian dan penjualan memperbarui inventaris melalui proses yang tervalidasi.
4. Menyediakan informasi piutang, utang, dan pembayaran.
5. Menerapkan kontrol akses berbasis role dan permission.
6. Menyediakan laporan berdasarkan data transaksi aktual.
7. Menjadi proyek portofolio yang menunjukkan kemampuan frontend, backend, database, business logic, dan automated testing.

## 1.3 Prinsip Produk

- Satu perusahaan, banyak gudang.
- Saldo inventaris dipisahkan berdasarkan produk dan gudang.
- Semua perubahan stok harus memiliki referensi transaksi.
- Transaksi yang diposting tidak dapat diproses ulang sehingga menggandakan dampaknya.
- Nilai transaksi dihitung dan divalidasi oleh backend.
- Pengguna hanya dapat menjalankan tindakan sesuai permission.
- Data transaksi yang sudah diposting dikoreksi melalui proses yang tercatat.
- Laporan harus dapat ditelusuri ke data sumber.

---

# 2. Asumsi dan Keputusan Final

| Aspek | Keputusan |
|---|---|
| Model perusahaan | Satu perusahaan |
| Gudang | Mendukung beberapa gudang |
| Database | MySQL |
| Backend | Python Flask REST API |
| ORM | SQLAlchemy |
| Frontend | React.js + TypeScript |
| Finance | Simple-finance |
| Metode valuasi stok | Weighted average cost |
| Mata uang | Satu mata uang operasional |
| Pajak | Belum dihitung otomatis sebelum dikonfigurasi |
| Penerimaan pembelian | Mendukung penerimaan parsial |
| Pengiriman penjualan | Mendukung pengiriman parsial |
| Tagihan supplier | Satu vendor bill per Goods Receipt pada MVP |
| Invoice pelanggan | Satu sales invoice per shipment pada MVP |
| General Ledger | Tidak termasuk MVP |
| Multi-company | Tidak termasuk MVP |

Asumsi ini menjadi dasar perancangan database dan API. Perubahan terhadap asumsi yang memengaruhi transaksi harus melalui revisi persyaratan dan evaluasi dampaknya.

---

# 3. Batasan Ruang Lingkup

## 3.1 Fitur yang Termasuk dalam MVP

### A. Authentication dan User Management
- Login dan logout.
- Profil pengguna.
- Pengelolaan pengguna.
- Role dan permission.
- Aktivasi dan penonaktifan akun.
- Audit log aktivitas penting.

### B. Master Data
- Produk dan SKU.
- Kategori.
- Satuan.
- Supplier.
- Pelanggan.
- Gudang.
- Status aktif/nonaktif.
- Pencarian, filter, dan pagination.

### C. Inventory Management
- Saldo stok per produk dan gudang.
- Kartu stok.
- Penerimaan dan pengeluaran barang.
- Reservasi stok.
- Penyesuaian stok.
- Transfer antargudang.
- Peringatan stok minimum.
- Pencegahan stok negatif.
- Weighted average cost.
- Laporan nilai persediaan.

### D. Purchasing
- Purchase Order (PO).
- Persetujuan PO.
- Goods Receipt.
- Penerimaan parsial.
- Riwayat pembelian.
- Vendor bill.
- Pembatalan dan koreksi sesuai aturan.

### E. Sales
- Sales Order (SO).
- Pemeriksaan ketersediaan stok.
- Reservasi stok.
- Pengiriman parsial.
- Sales invoice.
- Retur penjualan sederhana.
- Pemantauan status pesanan dan pengiriman.

### F. Simple-Finance
- Tagihan pelanggan.
- Tagihan supplier.
- Pembayaran pelanggan.
- Pembayaran supplier.
- Alokasi pembayaran.
- Perhitungan piutang dan utang.
- Ringkasan kas masuk dan keluar.

### G. Dashboard dan Reporting
- Ringkasan penjualan dan pembelian.
- Stok per gudang.
- Stok minimum.
- Nilai persediaan.
- Piutang dan utang.
- Laporan pengiriman.
- Laporan pembayaran.
- Export CSV atau Excel.
- Audit log.

## 3.2 Fitur di Luar MVP

- General Ledger lengkap.
- Chart of Accounts dan jurnal akuntansi.
- Trial Balance dan laporan keuangan formal.
- Payroll dan HR.
- Manufaktur dan Bill of Materials.
- Multi-company.
- Multi-currency.
- Integrasi bank atau payment gateway.
- Perhitungan pajak otomatis.
- Integrasi perpajakan eksternal.
- Aplikasi mobile native.
- Sinkronisasi offline.

---

# 4. Pengguna dan Hak Akses

## 4.1 Role

### Administrator
Mengelola pengguna, role, permission, dan master data sesuai otorisasi.

### Purchasing
Mengelola PO, pengajuan persetujuan, dan pemantauan penerimaan barang.

### Warehouse
Mengelola penerimaan, pengiriman, stok, penyesuaian, dan transfer gudang.

### Sales
Mengelola pelanggan, SO, reservasi, dan pemantauan pengiriman.

### Finance
Mengelola vendor bill, invoice pelanggan, pembayaran, alokasi pembayaran, piutang, dan utang.

### Manager
Memantau laporan dan menyetujui transaksi sesuai permission.

## 4.2 Permission Khusus Gudang

Selain permission berdasarkan modul, sistem harus dapat membatasi akses berdasarkan gudang.

Contoh:
- `inventory.read`
- `inventory.read.warehouse`
- `inventory.adjust.create`
- `inventory.adjust.approve`
- `inventory.transfer.create`
- `inventory.transfer.post`
- `goods_receipts.post`
- `shipments.post`

Jika pengguna hanya memiliki akses ke Gudang A, pengguna tersebut tidak boleh membaca atau memodifikasi data operasional Gudang B melalui manipulasi parameter API.

Permission global dan cakupan gudang harus diperiksa di backend.

## 4.3 Pemisahan Tugas

- Pembuat PO tidak otomatis berhak menyetujui PO yang sama.
- Pembuat penyesuaian stok tidak otomatis berhak menyetujui penyesuaian tersebut.
- Administrator tidak otomatis memperoleh izin posting transaksi keuangan.
- Hak approve, post, cancel, dan reverse dipisahkan jika dibutuhkan oleh kebijakan.

---

# 5. Persyaratan Fungsional

## 5.1 Master Data

**FR-MASTER-01:** Sistem menyediakan CRUD produk, kategori, satuan, supplier, pelanggan, dan gudang.

**FR-MASTER-02:** SKU dan kode master data harus unik.

**FR-MASTER-03:** Produk dan gudang yang telah digunakan transaksi tidak boleh dihapus permanen dengan cara yang merusak histori.

**FR-MASTER-04:** Produk harus dapat digunakan pada beberapa gudang.

**FR-MASTER-05:** Sistem harus mendukung pencarian, filter, pagination, dan status aktif.

**FR-MASTER-06:** Gudang nonaktif tidak dapat digunakan untuk transaksi baru, tetapi transaksi historisnya tetap dapat dibaca sesuai permission.

## 5.2 Inventory

**FR-INV-01:** Saldo inventaris disimpan berdasarkan kombinasi produk dan gudang.

**FR-INV-02:** Sistem harus mencatat pergerakan stok pada stock ledger.

**FR-INV-03:** Penerimaan yang diposting menambah stok gudang tujuan.

**FR-INV-04:** Shipment yang diposting mengurangi stok gudang sumber.

**FR-INV-05:** Reservasi mengurangi stok tersedia tanpa langsung mengurangi stok fisik.

**FR-INV-06:** Sistem harus mencegah stok negatif dan reservasi berlebih.

**FR-INV-07:** Penyesuaian stok memerlukan alasan dan otorisasi.

**FR-INV-08:** Transfer antargudang harus mencatat gudang asal, gudang tujuan, kuantitas, dan status.

**FR-INV-09:** Transfer yang diposting harus mengurangi saldo gudang asal dan menambah saldo gudang tujuan secara konsisten.

**FR-INV-10:** Sistem harus mendukung laporan stok per gudang dan gabungan seluruh gudang.

**FR-INV-11:** Valuasi inventaris menggunakan weighted average cost dengan kebijakan biaya yang terdokumentasi.

**FR-INV-12:** Seluruh perubahan saldo dan ledger harus dilakukan secara atomik.

## 5.3 Purchasing

**FR-PUR-01:** Purchasing dapat membuat PO yang terhubung dengan supplier dan gudang tujuan.

**FR-PUR-02:** PO dapat diajukan, disetujui, ditolak, atau dibatalkan sesuai aturan status.

**FR-PUR-03:** Goods Receipt harus mengacu pada PO yang valid.

**FR-PUR-04:** Penerimaan parsial harus didukung.

**FR-PUR-05:** Kuantitas penerimaan tidak boleh melebihi kuantitas yang masih dapat diterima, kecuali kebijakan khusus ditambahkan secara eksplisit.

**FR-PUR-06:** Posting Goods Receipt memperbarui stok gudang tujuan.

**FR-PUR-07:** Posting ulang tidak boleh menggandakan penerimaan.

**FR-PUR-08:** Vendor bill harus mempunyai referensi penerimaan yang valid.

**FR-PUR-09:** Untuk MVP, satu Goods Receipt hanya dapat menjadi sumber satu vendor bill.

## 5.4 Sales

**FR-SALES-01:** Sales Order harus terhubung dengan pelanggan dan gudang sumber.

**FR-SALES-02:** Sistem memeriksa stok tersedia pada gudang sumber.

**FR-SALES-03:** Sistem menyediakan reservasi stok berdasarkan pesanan.

**FR-SALES-04:** Pengiriman parsial harus didukung.

**FR-SALES-05:** Shipment yang diposting mengurangi stok gudang sumber.

**FR-SALES-06:** Sistem harus mencegah pengiriman melebihi kuantitas yang dapat dipenuhi.

**FR-SALES-07:** Invoice harus mengacu pada shipment yang valid.

**FR-SALES-08:** Untuk MVP, satu shipment hanya dapat menjadi sumber satu sales invoice.

**FR-SALES-09:** Pembatalan pesanan harus melepaskan reservasi yang belum digunakan.

**FR-SALES-10:** Retur penjualan harus tercatat sebagai transaksi terpisah.

Untuk MVP, retur harus mengacu pada Shipment yang sudah diposting dan item
Shipment terkait. Kuantitas kumulatif retur yang diposting tidak boleh melebihi
kuantitas yang dikirim. Retur berstatus `DRAFT` sebelum diposting; barang dengan
kondisi `RESTOCK` menambah stok gudang asal Shipment, sedangkan barang
`DAMAGED` hanya dicatat dan tidak menambah stok. Retur tidak mengubah invoice
atau pembayaran pelanggan pada MVP.

## 5.5 Simple-Finance

**FR-FIN-01:** Sistem menyediakan vendor bill dan sales invoice.

**FR-FIN-02:** Sistem menyediakan pembayaran pelanggan dan pembayaran supplier.

**FR-FIN-03:** Pembayaran harus dapat dialokasikan ke tagihan yang sesuai.

**FR-FIN-04:** Pembayaran sebagian harus didukung.

**FR-FIN-05:** Sistem menghitung sisa tagihan berdasarkan jumlah yang diposting dan alokasi yang sah.

**FR-FIN-06:** Alokasi tidak boleh melebihi sisa tagihan atau jumlah pembayaran yang belum dialokasikan.

**FR-FIN-07:** Pembayaran yang belum diposting tidak boleh mengurangi saldo piutang atau utang.

**FR-FIN-08:** Pembayaran yang diposting tidak boleh dihapus tanpa mekanisme koreksi.

**FR-FIN-09:** Sistem menyediakan ringkasan kas masuk dan keluar dari pembayaran yang telah diposting.

**FR-FIN-10:** Modul keuangan tidak boleh mengklaim menghasilkan laporan akuntansi lengkap karena General Ledger tidak termasuk MVP.

---

# 6. Aturan Bisnis Multi-Warehouse

## 6.1 Saldo Inventaris

Setiap saldo inventaris diidentifikasi oleh kombinasi:

`product_id + warehouse_id`

Kombinasi tersebut harus unik pada tabel `inventory_balances`.

Rumus:

**Available = On Hand − Reserved**

Contoh:

- Produk: Kertas A4.
- Gudang A: 100 unit on hand, 20 reserved.
- Gudang B: 50 unit on hand, 5 reserved.

Maka:
- Gudang A memiliki 80 unit available.
- Gudang B memiliki 45 unit available.
- Total on hand perusahaan adalah 150 unit.
- Total available perusahaan adalah 125 unit.

Stok tersedia pada gudang berbeda tidak otomatis dapat digunakan untuk memenuhi pesanan dari gudang lain. Pemindahan stok harus melalui transfer yang sah.

## 6.2 Transfer Antargudang

Alur transfer:

1. Pengguna memilih gudang asal dan tujuan.
2. Sistem memvalidasi kedua gudang aktif dan berbeda.
3. Pengguna memasukkan produk dan kuantitas.
4. Sistem memvalidasi stok tersedia di gudang asal.
5. Transfer diajukan atau disetujui sesuai kebijakan.
6. Transfer diposting dan saldo kedua gudang diperbarui.
7. Sistem mencatat pergerakan keluar dan masuk dengan referensi transfer yang sama.

Untuk MVP, transfer dianggap langsung selesai saat diposting. Fitur barang dalam perjalanan atau *in-transit inventory* tidak termasuk versi pertama.

## 6.3 Penyesuaian Stok

Penyesuaian wajib menyertakan gudang, produk, kuantitas perubahan, alasan, pembuat, dan penyetuju jika diperlukan.

Penyesuaian hanya boleh diposting satu kali. Dampaknya pada saldo harus tercatat di stock ledger.

## 6.4 Reservasi

Reservasi harus terikat pada item Sales Order dan gudang tertentu.

Sistem tidak boleh:
- Mengreservasi stok dari gudang lain secara otomatis.
- Melebihi available pada gudang sumber.
- Melepaskan reservasi yang telah digunakan untuk shipment.
- Menghitung reservasi yang sudah dibatalkan sebagai stok terpesan aktif.

---

# 7. Rancangan ERD dan Database MySQL

## 7.1 Struktur Master Data

### products
- id
- sku
- name
- category_id
- unit_id
- min_stock
- is_active
- created_at
- updated_at

### warehouses
- id
- code
- name
- address
- is_active
- created_at
- updated_at

### inventory_balances
- id
- product_id
- warehouse_id
- quantity_on_hand
- quantity_reserved
- average_cost
- updated_at

Constraint:
- UNIQUE (`product_id`, `warehouse_id`)
- Foreign key ke `products` dan `warehouses`
- Nilai kuantitas dan biaya menggunakan tipe DECIMAL yang ditetapkan secara konsisten.

### stock_movements
- id
- product_id
- warehouse_id
- movement_type
- quantity_delta
- unit_cost
- reference_type
- reference_id
- created_by
- created_at

Stock movement menjadi histori pergerakan stok. Data ledger tidak boleh dimodifikasi langsung melalui endpoint umum.

## 7.2 Struktur Transfer

### stock_transfers
- id
- transfer_number
- source_warehouse_id
- destination_warehouse_id
- status
- reason
- created_by
- approved_by
- posted_by
- posted_at
- created_at

### stock_transfer_items
- id
- stock_transfer_id
- product_id
- quantity

Relasi:
- Satu transfer memiliki banyak item.
- Setiap item mengacu pada produk.
- Transfer memiliki gudang asal dan gudang tujuan.
- Gudang asal harus berbeda dengan gudang tujuan.

Saat posting, sistem harus membuat pergerakan keluar dari gudang asal dan pergerakan masuk ke gudang tujuan dalam transaksi database yang sama.

## 7.3 Perubahan pada Tabel Purchasing

### purchase_orders
Tambahkan atau pastikan tersedia:
- supplier_id
- warehouse_id
- status
- created_by
- approved_by
- order_date

Gudang tujuan ditetapkan pada PO versi pertama.

### goods_receipts
- purchase_order_id
- warehouse_id
- status
- received_at
- posted_at

Gudang penerimaan harus konsisten dengan gudang tujuan PO. Jika perubahan gudang diperlukan, perubahan harus dilakukan sebelum penerimaan diposting dan mengikuti validasi status.

### goods_receipt_items
- goods_receipt_id
- purchase_order_item_id
- quantity_received
- unit_cost

Penerimaan harus memvalidasi kuantitas total yang sudah diterima dari seluruh Goods Receipt terkait PO.

## 7.4 Perubahan pada Tabel Sales

### sales_orders
- customer_id
- warehouse_id
- status
- order_date
- created_by
- approved_by

### sales_order_items
- sales_order_id
- product_id
- quantity
- unit_price
- discount_amount
- line_total

### shipments
- sales_order_id
- warehouse_id
- status
- shipped_at
- posted_at

### shipment_items
- shipment_id
- sales_order_item_id
- quantity_shipped

### sales_returns dan sales_return_items
- Setiap retur mengacu pada satu Shipment yang telah diposting.
- Setiap item retur mengacu pada item Shipment yang sama.
- Item menyimpan kuantitas dan kondisi `RESTOCK` atau `DAMAGED`.
- Status retur `DRAFT` tidak mengubah stok; posting mencatat restock sebagai
  stock movement `RETURN_IN` pada gudang asal Shipment.
- Kuantitas retur yang sudah diposting tidak boleh melebihi kuantitas Shipment.
- Retur tidak membuat credit note atau refund pada MVP.

Shipment harus menggunakan gudang sumber yang konsisten dengan SO untuk MVP. Jika suatu pesanan perlu dipenuhi dari beberapa gudang, pengguna membuat Sales Order terpisah untuk masing-masing gudang atau menggunakan desain pemenuhan multi-gudang pada versi berikutnya.

## 7.5 Perubahan pada Tabel Finance

### vendor_bills
- supplier_id
- goods_receipt_id
- status
- total_amount
- due_date

Tambahkan constraint unik pada `goods_receipt_id` untuk menerapkan satu tagihan per penerimaan pada MVP, selama setiap penerimaan memang wajib memiliki paling banyak satu tagihan.

### sales_invoices
- customer_id
- shipment_id
- status
- total_amount
- due_date

Tambahkan constraint unik pada `shipment_id` untuk mencegah invoice sumber yang duplikat.

### customer_payments
- customer_id
- payment_number
- payment_date
- amount
- method
- status

### customer_payment_allocations
- payment_id
- sales_invoice_id
- allocated_amount

### supplier_payments
- supplier_id
- payment_number
- payment_date
- amount
- method
- status

### supplier_payment_allocations
- payment_id
- vendor_bill_id
- allocated_amount

Pembayaran dan alokasinya harus divalidasi terhadap pelanggan atau supplier yang sesuai. Untuk MVP, satu pembayaran tidak boleh dialokasikan lintas pelanggan atau lintas supplier.

## 7.6 ERD Konseptual

Relasi utama:

- Products 1:N Inventory Balances.
- Warehouses 1:N Inventory Balances.
- Products 1:N Stock Movements.
- Warehouses 1:N Stock Movements.
- Warehouses 1:N Purchase Orders.
- Purchase Orders 1:N Goods Receipts.
- Warehouses 1:N Sales Orders.
- Sales Orders 1:N Shipments.
- Warehouses 1:N Stock Transfers sebagai gudang asal dan tujuan.
- Sales Invoices 1:N Customer Payment Allocations.
- Vendor Bills 1:N Supplier Payment Allocations.

Database harus menggunakan foreign key, unique constraint, index, serta transaksi MySQL untuk menjaga konsistensi. Gunakan tabel transaksional yang mendukung transaksi database, seperti InnoDB.

---

# 8. Persyaratan REST API

Seluruh endpoint menggunakan prefix `/api/v1`.

## 8.1 Master Data

- GET, POST `/api/v1/products`
- GET, PATCH `/api/v1/products/{id}`
- GET, POST `/api/v1/categories`
- GET, POST `/api/v1/units`
- GET, POST `/api/v1/suppliers`
- GET, PATCH `/api/v1/suppliers/{id}`
- GET, POST `/api/v1/customers`
- GET, PATCH `/api/v1/customers/{id}`
- GET, POST `/api/v1/warehouses`
- GET, PATCH `/api/v1/warehouses/{id}`

## 8.2 Inventory

- GET `/api/v1/inventory/balances`
- GET `/api/v1/inventory/movements`
- GET `/api/v1/inventory/low-stock`
- GET, POST `/api/v1/inventory/adjustments`
- POST `/api/v1/inventory/adjustments/{id}/approve`
- POST `/api/v1/inventory/adjustments/{id}/post`
- GET, POST `/api/v1/inventory/transfers`
- GET `/api/v1/inventory/transfers/{id}`
- POST `/api/v1/inventory/transfers/{id}/submit`
- POST `/api/v1/inventory/transfers/{id}/approve`
- POST `/api/v1/inventory/transfers/{id}/post`

Filter yang didukung:
- `warehouse_id`
- `product_id`
- `category_id`
- `from_date`
- `to_date`
- `page`
- `per_page`

Semua filter gudang harus divalidasi terhadap permission pengguna.

## 8.3 Purchasing

- GET, POST `/api/v1/purchase-orders`
- GET `/api/v1/purchase-orders/{id}`
- POST `/api/v1/purchase-orders/{id}/submit`
- POST `/api/v1/purchase-orders/{id}/approve`
- POST `/api/v1/purchase-orders/{id}/cancel`
- GET, POST `/api/v1/goods-receipts`
- GET `/api/v1/goods-receipts/{id}`
- POST `/api/v1/goods-receipts/{id}/post`
- GET, POST `/api/v1/vendor-bills`

PO dan Goods Receipt harus menyimpan referensi gudang tujuan dan divalidasi pada setiap transisi status yang relevan.

## 8.4 Sales

- GET, POST `/api/v1/sales-orders`
- GET `/api/v1/sales-orders/{id}`
- POST `/api/v1/sales-orders/{id}/submit`
- POST `/api/v1/sales-orders/{id}/approve`
- POST `/api/v1/sales-orders/{id}/reserve`
- POST `/api/v1/sales-orders/{id}/cancel`
- GET, POST `/api/v1/shipments`
- GET `/api/v1/shipments/{id}`
- POST `/api/v1/shipments/{id}/post`
- GET, POST `/api/v1/sales-invoices`
- GET, POST `/api/v1/sales-returns`
- GET `/api/v1/sales-returns/{id}`
- POST `/api/v1/sales-returns/{id}/post`

Sales Order dan Shipment harus menggunakan gudang sumber yang sesuai dan tidak boleh melewati pemeriksaan stok.

## 8.5 Finance

- GET `/api/v1/finance/receivables`
- GET `/api/v1/finance/payables`
- GET, POST `/api/v1/customer-payments`
- POST `/api/v1/customer-payments/{id}/post`
- POST `/api/v1/customer-payments/{id}/allocations`
- GET, POST `/api/v1/supplier-payments`
- POST `/api/v1/supplier-payments/{id}/post`
- POST `/api/v1/supplier-payments/{id}/allocations`
- GET `/api/v1/finance/cash-summary`

Customer payment dibuat sebagai `DRAFT` dengan `customer_id`, `amount`, dan
`payment_method`. Alokasi dikirim sebagai array `allocations` yang berisi
`invoice_id` dan `amount`; seluruh invoice harus dimiliki pelanggan yang sama.
Jumlah alokasi tidak boleh melebihi pembayaran maupun sisa tagihan, dan saldo
invoice baru berubah setelah pembayaran diposting. Posting memvalidasi ulang
seluruh alokasi dan memperbarui invoice terkait dalam satu transaksi. Endpoint
lama `/api/v1/payments` tetap didukung untuk integrasi satu invoice.

Supplier payment mengikuti pola yang sama dengan `supplier_id`, `amount`, dan
`payment_method`; alokasinya memakai `vendor_bill_id` dan `amount`. Pembayaran
yang telah diposting dihitung pada ringkasan kas berdasarkan seluruh nilai
pembayaran, sedangkan saldo tagihan berubah hanya sebesar alokasi yang diposting.
Piutang dihitung dari invoice dikurangi alokasi pembayaran pelanggan berstatus
`POSTED`; utang memakai aturan yang sama terhadap vendor bill. Sales report
menggunakan tanggal pembuatan invoice dan purchases report menggunakan tanggal
pembuatan vendor bill. Filter periode bersifat inklusif. Inventory report
menghitung nilai stok per gudang dari kuantitas dikali average cost, dan untuk
gabungan gudang menghitung average cost tertimbang, bukan menjumlahkan average
cost antar gudang.

Dashboard summary secara default menggunakan periode bulan berjalan; `from_date`
dan `to_date` dapat dikirim untuk periode lain. Nilai stok/piutang/utang mengikuti
filter gudang bila diberikan. Ringkasan kas tetap company-wide karena pembayaran
dapat dialokasikan lintas gudang dan tidak selalu memiliki alokasi penuh.

## 8.6 Dashboard dan Reporting

- GET `/api/v1/dashboard/summary`
- GET `/api/v1/reports/sales`
- GET `/api/v1/reports/purchases`
- GET `/api/v1/reports/inventory`
- GET `/api/v1/reports/stock-movements`
- GET `/api/v1/reports/receivables`
- GET `/api/v1/reports/payables`
- GET `/api/v1/audit-logs`

Laporan inventaris harus mendukung filter per gudang dan ringkasan seluruh gudang. Ringkasan perusahaan tidak boleh dihitung dengan menjumlahkan nilai yang tidak sebanding atau menghitung stok yang sama lebih dari sekali.

## 8.7 Standar API

- Gunakan JSON untuk request dan response.
- Gunakan HTTP status code secara konsisten.
- Terapkan validasi input dan permission di backend.
- Terapkan pagination untuk daftar data.
- Gunakan transaksi database pada operasi posting.
- Cegah posting ganda.
- Terapkan concurrency control untuk stok dan alokasi pembayaran.
- Dokumentasikan endpoint menggunakan OpenAPI/Swagger.

---

# 9. Persyaratan UI/UX

## 9.1 Navigasi

Sidebar utama:
- Dashboard.
- Master Data.
- Inventory.
- Purchasing.
- Sales.
- Finance.
- Reports.
- User Management.

Menu harus menyesuaikan permission pengguna.

## 9.2 Inventory

Halaman inventaris wajib menampilkan:
- Produk.
- Gudang.
- On hand.
- Reserved.
- Available.
- Average cost.
- Nilai persediaan.

Pengguna dapat memfilter stok berdasarkan gudang atau melihat ringkasan gabungan.

## 9.3 Transfer Antargudang

Form transfer harus memuat:
- Gudang asal.
- Gudang tujuan.
- Daftar produk.
- Kuantitas.
- Alasan.
- Status transfer.
- Riwayat persetujuan dan posting.

Sistem harus menampilkan peringatan apabila gudang asal dan tujuan sama atau stok tidak mencukupi.

## 9.4 Dashboard

Dashboard harus menampilkan:
- Total penjualan dalam periode.
- Total pembelian dalam periode.
- Nilai persediaan.
- Jumlah produk dengan stok minimum.
- Piutang pelanggan.
- Utang supplier.
- Ringkasan kas masuk dan keluar.
- Distribusi stok antar gudang.

Semua metrik harus dihitung berdasarkan definisi yang jelas dan sumber data yang dapat ditelusuri.

---

# 10. Persyaratan Nonfungsional

## 10.1 Keamanan
- Password disimpan menggunakan hashing yang sesuai.
- Endpoint dilindungi autentikasi dan authorization.
- Hak akses gudang diperiksa di backend.
- Secret dan kredensial tidak disimpan dalam repository.
- Error tidak membocorkan informasi sensitif.
- Audit log mencatat tindakan penting.

## 10.2 Integritas Data
- Operasi posting menggunakan transaksi MySQL.
- Gunakan foreign key dan unique constraint.
- Gunakan locking atau mekanisme concurrency control untuk pembaruan stok.
- Gunakan idempotency atau pemeriksaan status untuk mencegah posting ganda.
- Saldo inventaris harus konsisten dengan ledger.
- Saldo tagihan harus konsisten dengan alokasi pembayaran.

## 10.3 Database dan Migration
- Gunakan SQLAlchemy dan Flask-Migrate/Alembic.
- Perubahan schema harus menggunakan migration yang dapat ditinjau.
- Uji migration pada database sementara sebelum penerapan.
- Hindari perubahan langsung terhadap data operasional.
- Backup dan prosedur rollback harus ditentukan sebelum deployment.
- Jangan menjalankan migration produksi tanpa persetujuan eksplisit.

## 10.4 Testing
- Unit test untuk perhitungan stok dan keuangan.
- Integration test untuk alur pembelian dan penjualan.
- Pengujian transaksi multi-warehouse.
- Pengujian permission lintas gudang.
- Pengujian posting ganda dan transaksi bersamaan.
- Regression test untuk bug yang diperbaiki.
- Gunakan MySQL test database untuk pengujian yang bergantung pada perilaku khusus MySQL.

---

# 11. Acceptance Criteria

## 11.1 Multi-Warehouse
- Produk yang sama dapat disimpan pada beberapa gudang.
- Saldo masing-masing gudang terpisah.
- Transfer mengurangi stok sumber dan menambah stok tujuan dengan jumlah yang sama.
- Transfer gagal tidak meninggalkan saldo parsial.
- Pengguna tidak dapat mengakses gudang yang tidak diizinkan.
- Laporan gabungan sama dengan agregasi saldo gudang yang valid.

## 11.2 Purchasing
- PO menentukan gudang tujuan.
- Goods Receipt hanya memengaruhi gudang yang benar.
- Penerimaan parsial menghitung sisa kuantitas dengan benar.
- Posting ulang tidak menggandakan stok.

## 11.3 Sales
- SO menentukan gudang sumber.
- Reservasi dihitung terhadap stok gudang tersebut.
- Shipment tidak mengurangi stok gudang lain.
- Pengiriman parsial dan invoice mengikuti status dokumen yang valid.

## 11.4 Simple-Finance
- Pembayaran sebagian menghasilkan sisa tagihan yang benar.
- Pembayaran tidak dapat dialokasikan melebihi nilai yang tersedia.
- Pembayaran yang belum diposting tidak mengubah saldo tagihan.
- Ringkasan kas hanya menghitung pembayaran yang sah dan diposting.
- Laporan keuangan tidak mengklaim sebagai laporan akuntansi lengkap.

## 11.5 Data dan Security
- Endpoint yang tidak diizinkan ditolak.
- Constraint database mencegah duplikasi yang kritis.
- Posting yang gagal di-rollback secara utuh.
- Audit log tersedia untuk tindakan penting.
- Tidak ada perubahan database operasional yang dilakukan tanpa persetujuan.

---

# 12. Tahapan Implementasi

## Phase 1 — Foundation
- Setup repository dan struktur frontend/backend.
- Konfigurasi Flask, SQLAlchemy, dan MySQL.
- Environment configuration.
- Migration setup.
- API health check.
- Test environment.

## Phase 2 — Authentication dan RBAC
- Login/logout.
- User management.
- Role dan permission.
- Audit log.
- Permission berbasis gudang.

## Phase 3 — Master Data
- Produk, kategori, satuan.
- Supplier dan pelanggan.
- Gudang.
- CRUD, pencarian, filter, pagination.

## Phase 4 — Inventory Core
- Inventory balances.
- Stock ledger.
- Reservasi stok.
- Penyesuaian stok.
- Transfer antargudang.
- Weighted average cost.
- Pengujian konsistensi saldo.

## Phase 5 — Purchasing
- Purchase Order.
- Approval.
- Goods Receipt.
- Penerimaan parsial.
- Vendor bill.
- Integrasi stok.

## Phase 6 — Sales
- Sales Order.
- Reservasi.
- Shipment.
- Pengiriman parsial.
- Invoice.
- Retur sederhana.

## Phase 7 — Simple-Finance
- Customer payments.
- Supplier payments.
- Payment allocations.
- Piutang dan utang.
- Ringkasan kas operasional.

## Phase 8 — Reporting dan Release
- Dashboard.
- Laporan multi-warehouse.
- Export CSV/Excel.
- Integration dan regression testing.
- Dokumentasi API.
- README dan data demo.
- Deployment.

Setiap fase harus menghasilkan fitur yang dapat dijalankan dan diuji sebelum fase berikutnya dimulai.

---

# 13. Risiko dan Mitigasi

| Risiko | Mitigasi |
|---|---|
| Stok antar gudang tercampur | Gunakan saldo berdasarkan product_id dan warehouse_id |
| Transfer menggandakan stok | Posting atomik dan validasi status |
| Overselling | Reservasi dan locking yang tepat |
| Akses gudang tidak aman | Permission berbasis gudang di backend |
| Saldo tagihan tidak konsisten | Payment allocation dan constraint |
| Perubahan schema berisiko | Migration yang diuji dan ditinjau |
| Scope melebar menjadi akuntansi penuh | Pertahankan simple-finance pada MVP |
| Laporan gabungan salah | Definisikan sumber dan rumus setiap metrik |

---

# 14. Definition of Done

DistribuFlow ERP versi pertama dinyatakan selesai jika:

1. Seluruh modul MVP berfungsi.
2. Multi-warehouse berjalan pada pembelian, penjualan, dan transfer.
3. Saldo stok konsisten dengan stock ledger.
4. Reservasi tidak menyebabkan stok negatif.
5. Invoice dan pembayaran dapat direkonsiliasi.
6. Permission dan pembatasan gudang diterapkan di backend.
7. Automated tests lulus.
8. Migration dapat diuji secara aman.
9. Dokumentasi ERD dan API tersedia.
10. README berisi instruksi setup dan penggunaan.
11. Data demo ditandai sebagai data contoh.
12. Aplikasi siap didemonstrasikan sebagai proyek portofolio.

---

# 15. Penutup

DistribuFlow ERP versi 1.1 menggunakan MySQL sebagai database, mendukung beberapa gudang dalam satu perusahaan, dan membatasi keuangan pada simple-finance.

Keputusan ini menjaga kompleksitas proyek tetap menengah sambil memberikan ruang untuk menunjukkan business logic yang realistis, terutama pada inventaris multi-warehouse, alur pembelian dan penjualan, kontrol akses, dan rekonsiliasi pembayaran.

Dokumen ini menjadi acuan kebutuhan produk. Sebelum implementasi, rancangan teknis harus menerjemahkan setiap persyaratan ke ERD final, kontrak API, migration, service layer, dan test cases.

Perubahan pada database atau konfigurasi operasional harus melalui proses peninjauan dan persetujuan terlebih dahulu.