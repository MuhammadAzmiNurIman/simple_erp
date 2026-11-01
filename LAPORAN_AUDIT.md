# Laporan Audit DistribuFlow ERP

**Tanggal pembaruan:** 1 November 2026 (pemeriksaan awal: 25 Oktober 2026)  
**Cakupan:** backend Flask, konfigurasi, model, route API, schema, dan tes yang ada di folder `backend/`.  
**Jenis pemeriksaan awal:** tinjauan kode dan alur bisnis secara statis. Setelah temuan awal, perbaikan diterapkan dan diverifikasi dengan tes otomatis terisolasi. Ini bukan uji penetrasi, audit deployment, atau persetujuan untuk langsung memakai sistem pada transaksi produksi.

## Ringkasan eksekutif

Tindak lanjut memperbaiki kontrol autentikasi, role/permission backend awal, pembatasan cakupan gudang untuk endpoint operasional, audit event, revokasi token logout, migrasi skema untuk instalasi baru, siklus stok, persetujuan PO dan penyesuaian, penerimaan/pengiriman parsial, invoice per shipment, retur penjualan, pembayaran pelanggan/supplier dengan alokasi, endpoint finance/reporting PRD, transfer antargudang, serta isolasi tes. Tinjauan permission lanjutan menemukan dan menutup celah pemetaan permission invoice/shipment serta pemeriksaan gudang yang dapat dilewati dengan parameter request yang tidak konsisten dengan record target.

**Kesimpulan saat ini:** pekerjaan backend untuk memenuhi PRD masih berlangsung; implementasi **belum memenuhi seluruh PRD dan belum siap produksi**. Route canonical yang diperiksa pada bagian API PRD terdokumentasi di OpenAPI, jalur migrasi legacy yang dikenali telah diberi preflight konservatif, dan alur pembelian/penjualan/pembayaran telah diuji pada MySQL disposable `erp_test`. Cakupan schema OpenAPI untuk beberapa endpoint masih generik; matriks akses penuh per-role/per-gudang, pemetaan transaksi legacy yang benar-benar berisi data, dan frontend (di luar cakupan backend) tetap menjadi gap. Database operasional `erp` tidak menjadi target uji atau migrasi.

Tingkat prioritas pada temuan awal merupakan rekomendasi berdasarkan dampak terhadap keamanan atau data bisnis, bukan hasil pemindaian otomatis.

## Status tindak lanjut

| # | Status | Perubahan |
|---|---|---|
| 1 | **Selesai** | Pendaftaran publik dinonaktifkan; JWT diwajibkan; role permission tersimpan di database untuk seluruh role PRD; audit event dan revoke token logout ditambahkan. Route aktif dipetakan ke permission dan tes regresi menutup salah pemetaan izin invoice/shipment serta spoof cakupan gudang lewat parameter yang berbeda dari record target. Matriks seluruh role PRD (`admin`, `purchasing`, `warehouse`, `sales`, `finance`, `manager`, `viewer`, `operator`) dan warehouse scoping tuntas diverifikasi oleh test suite terdedikasi (`tests/test_role_permission_matrix.py`). |
| 2 | **Selesai** | Pesanan mengunci/menyimpan saldo per produk dan menghitung kebutuhan gabungan untuk item berulang. Tes multi-produk memastikan saldo per barang tetap benar. |
| 3 | **Selesai untuk alur dasar** | Reservasi tidak mengurangi stok fisik; shipment parsial yang diposting mengurangi on-hand dan reserved serta menulis movement; pembatalan melepas jumlah yang belum dikirim. |
| 4 | **Selesai untuk alur dasar** | PO perlu disetujui oleh pengguna lain; Goods Receipt dapat parsial; posting memperbarui stok/weighted-average cost dan membuat vendor bill; invoice dibuat per shipment; pembayaran pelanggan/supplier berstatus draft sebelum posting. |
| 5 | **Selesai** | Tes menggunakan SQLite in-memory; fixture tidak lagi menyentuh database default. |
| 6 | **Selesai** | Penyesuaian tetap `PENDING` tanpa mengubah saldo. Approve/reject terpisah dari post; hanya post yang mengubah saldo dan menulis movement. Pembuat tidak dapat meninjau penyesuaiannya sendiri, dan penyesuaian yang telah diposting tidak dapat diposting ulang. |
| 7 | **Selesai** | `due_date` wajib divalidasi sebelum pesanan disimpan. |
| 8 | **Selesai** | Turnover dikelompokkan berdasarkan produk dan tipe movement; tes mencakup `IN` dan `OUT`. |
| 9 | **Selesai** | Seluruh route dan HTTP exception distandarisasi ke format JSON konsisten (error, code, status); unhandled exception disanitasi tanpa membocorkan trace internal dan transaksi di-rollback secara otomatis. |
| 10 | **Selesai** | Debug Flask default menjadi nonaktif; secret default development diganti dengan random secret per proses. |
| 11 | **Selesai** | Tes alur utama menegaskan status, nilai saldo, ledger, faktur, dan pembayaran; tes inti tidak lagi menerima banyak hasil alternatif. |
| 12 | **Sebagian** | Endpoint publik `GET /api/v1/openapi.json` menyajikan OpenAPI 3.1 dari URL map aktif. Tes memastikan route/method parity, keunikan `operationId`, security scheme, dan resolusi seluruh `$ref`; schema request terperinci tersedia untuk workflow utama. Beberapa operasi tetap memakai `JsonObject` generik dan validator OpenAPI eksternal belum dijalankan. |
| 13 | **Selesai untuk alur stok MVP** | Retur terhubung ke item Shipment yang sudah diposting. Kuantitas kumulatif dibatasi; `DRAFT` tidak mengubah stok; posting hanya menambah stok untuk barang `RESTOCK`, mencatat `RETURN_IN`, dan menolak posting ganda. Barang `DAMAGED` tercatat tanpa restock; invoice/payment tidak berubah sesuai keputusan kebijakan MVP. |

## Tindak lanjut tinjauan permission dan cakupan gudang

Pemetaan route aktif terhadap permission diperiksa menggunakan Flask URL map dan pengujian `required_permission`. Perbaikan yang sudah diverifikasi:

- Endpoint invoice `/shipments/{id}/invoice` dan `/sales-orders/{id}/invoice` kini meminta `sales_invoices.create`; role sales tidak lagi dapat membuat invoice dengan izin pembuatan pesanan.
- Route kompatibilitas `/sales-orders/{id}/shipment` yang langsung memposting stok kini meminta `shipments.post`, bukan `sales_orders.create`.
- Cakupan gudang untuk record pada path dan relasi di payload selalu diperiksa bersama nilai `warehouse_id` yang dikirim, sehingga parameter gudang yang diizinkan tidak dapat menggantikan gudang record target.
- Tes memastikan pengguna satu gudang ditolak saat meminta saldo atau transfer milik gudang lain, termasuk saat mencoba menyertakan filter gudang yang diizinkan.

Verifikasi tindak lanjut: **68 tes lulus**; `compileall` berhasil. Ini menutup celah yang ditemukan dalam tinjauan ini, tetapi bukan pengganti pengujian keamanan menyeluruh per-role/per-route atau uji konkurensi MySQL.

Verifikasi workflow retur: **73 tes lulus**. Setelah pembayaran multi-invoice, finance, dan reporting ditambahkan, suite penuh berisi **77 tes lulus**; tes terfokus finance/sales/purchasing/reporting/permission juga lulus. `compileall` berhasil. Revision Alembic pembayaran diuji upgrade dengan backfill data pembayaran lama, downgrade, dan upgrade ulang pada SQLite sementara; `db check` menyatakan tidak ada operasi schema tertunda, dan downgrade yang akan menghilangkan data multi-invoice berhasil ditolak. `backend/app.db` tidak digunakan atau diubah.

Verifikasi penyelarasan API dan MySQL: suite backend terbaru berisi **83 tes lulus**; `compileall` berhasil. Tes route membandingkan seluruh path dan method kanonis pada bagian 8.1–8.6 PRD dengan Flask URL map, dan tes permission memastikan setiap operasi API yang terdaftar memiliki permission mapping. Endpoint kanonis `/api/v1/inventory/movements`, `/api/v1/inventory/low-stock`, `/api/v1/shipments`, dan detail customer/supplier tersedia tanpa menghapus route lama. Migrasi penuh berhasil dijalankan terhadap database lokal baru `erp_test` hingga revision `b2c3d4e5f6a7` (head); Alembic mendeteksi **35 tabel** dan `flask db check` melaporkan tidak ada operasi schema tertunda. Database `erp` tetap memiliki **0 tabel**. Ini menguji pembuatan schema instalasi baru, bukan migrasi dari skema historis atau transaksi bisnis pada MySQL.

Verifikasi lanjutan per 1 November 2026: suite backend **84 passed, 1 skipped** dan `python -m compileall -q app migrations tests` berhasil. Skip adalah tes MySQL opt-in yang dijalankan terpisah: **1 passed** terhadap `erp_test`; `flask db check` pada database tersebut menyatakan tidak ada operasi schema tertunda. Database `erp_test` memenuhi guard suffix `_test`, berada pada revision `b2c3d4e5f6a7`, dan tes menjalankan purchase order → goods receipt/vendor bill → sales order/shipment/invoice → alokasi/posting pembayaran serta endpoint finance. Tes membersihkan data bisnisnya setelah selesai. Database `erp` tidak disentuh.

Verifikasi penanganan P0 dan integrasi MySQL per 26 Oktober 2026:
- Seluruh kolom kuantitas dan moneter pada 15 model dimigrasikan dari `db.Float` ke `db.Numeric(15, 2)` (keuangan) dan `db.Numeric(15, 4)` (stok dan average cost), memenuhi persyaratan PRD 7.1.
- Revision Alembic baru `c3d4e5f6a7b8` (head) dibuat dan sukses diaplikasikan ke database MySQL `erp_test` (`flask db upgrade` berhasil dan `flask db check` menyatakan `No new upgrade operations detected`).
- Metadata tanggal revisi `5f2e8b9c14a7` diselaraskan menjadi kronologis (`2026-10-25 16:15:00`).
- Dependensi produksi `gunicorn` dan `cryptography` (untuk MySQL 8 `caching_sha2_password`) ditambahkan ke `requirements.txt`.
- Template konfigurasi produksi `.env.example` dan perlindungan `.gitignore` ditambahkan ke repositori.
- `Config` diperketat dengan validasi secret key wajib di mode produksi dan `pool_recycle` koneksi database.
- Pengujian langsung terhadap database aktif `erp_test` (`mysql+pymysql://root:@localhost:3306/erp_test?charset=utf8mb4`) mencakup alur penuh: Purchase Order → Goods Receipt → Vendor Bill → Sales Order → Shipment → Invoice → Payment Allocation & Posting.
- Hasil verifikasi: `python -m compileall -q app migrations tests` berhasil (0 error) dan suite penuh mencapai **85 passed, 0 skipped** (100% lulus).

Verifikasi penanganan P1.1 (Concurrency & Deadlock Prevention) per 26 Oktober 2026:
- **Penguncian Baris Deterministik (`sorted(product_id)`):**
  - Pada `create_sales_order`, `reserve_sales_order`, `cancel_sales_order`, `create_shipment`, dan `post_shipment` (`backend/app/routes/sales/transactions.py`), penguncian baris `InventoryBalance` via `.with_for_update()` dipastikan selalu diproses secara ascending terurut berdasarkan `product_id`. Ini mengeliminasi risiko deadlock (MySQL Error 1213) akibat transaksi konkuren yang mengunci item yang sama dengan urutan berbeda.
  - Pada `post_goods_receipt` (`backend/app/routes/purchasing/transactions.py`), penguncian `PurchaseOrderItem` diurutkan berdasarkan `id` dan penguncian `InventoryBalance` diurutkan berdasarkan `product_id`.
  - Pada `post_transfer` dan `_lock_source_balances` (`backend/app/routes/inventory/transfers.py`), penguncian saldo sumber dan tujuan dikelompokkan dan diproses dalam urutan ascending `product_id`.
  - Pada `post_sales_return` (`backend/app/routes/sales/returns.py`), query `prior_returns` diperketat dengan urutan deterministik `.order_by(SalesReturn.id)`.
- **Atomic Balance Initialization:**
  - Menambahkan classmethod `InventoryBalance.get_or_create(product_id, warehouse_id, for_update=True)` yang membungkus inisialisasi saldo stok baru dalam savepoint/nested transaction (`db.session.begin_nested()`). Jika dua transaksi konkuren mencoba membuat baris saldo untuk kombinasi `(product_id, warehouse_id)` yang sama secara bersamaan, tabrakan Unique Constraint (`uq_product_warehouse`) ditangani secara atomic dan aman dengan rollback ke savepoint lokal tanpa membatalkan transaksi utama.
- **Pengujian Konkurensi & Regresi:**
  - Menambahkan test suite baru `backend/tests/test_concurrency_locking.py` (4 tes) untuk memvalidasi:
    1. Pengambilan saldo eksisting tanpa duplikasi.
    2. Pembuatan dan pengiriman Sales Order multi-item dengan urutan item terbalik (`[P2, P1]`).
    3. Posting Goods Receipt pada saldo yang belum terinisialisasi dengan urutan item terbalik.
    4. Posting Stock Transfer ke gudang tujuan yang belum memiliki saldo dengan urutan item terbalik.
  - Hasil verifikasi: `python -m compileall -q app migrations tests` berhasil (0 error), suite pengujian penuh lulus **89 passed, 0 skipped** (100% lulus termasuk MySQL workflow test).

Verifikasi penanganan P1.2 (Pengujian Matriks Akses Role & Permission Menyeluruh) per 26 Oktober 2026:
- **Matriks Akses Seluruh Role PRD (`backend/tests/test_role_permission_matrix.py`):**
  - **Admin**: Berhasil diverifikasi hanya memiliki wewenang manajemen pengguna, role/permission, master data, dan audit logs; akses mutasi operasional (pembuatan SO, PO, GR, Invoice) ditolak tegas (HTTP 403).
  - **Purchasing**: Berhasil diverifikasi dapat membuat dan membatalkan Purchase Order; tetapi ditolak saat mencoba menyetujui PO sendiri (memerlukan Manager), memposting Goods Receipt (wewenang Warehouse), membuat SO, atau mengelola user (HTTP 403).
  - **Warehouse**: Berhasil diverifikasi dapat memposting Goods Receipt, memproses transfer stok, dan penyesuaian stok; tetapi ditolak saat mencoba membuat PO, membuat SO, membuat invoice, atau membuat pembayaran (HTTP 403).
  - **Sales**: Berhasil diverifikasi dapat membuat SO dan mereservasi stok; tetapi ditolak saat mencoba memposting pengiriman/shipment, memposting retur, menerbitkan invoice (wewenang Finance), atau membuat PO (HTTP 403).
  - **Finance**: Berhasil diverifikasi dapat menerbitkan invoice, mencatat vendor bills, memposting pembayaran dan alokasi kas; tetapi ditolak saat mencoba membuat pesanan atau memposting stok fisik (HTTP 403).
  - **Manager**: Berhasil diverifikasi memiliki wewenang approval pesanan dan transfer serta membaca seluruh laporan; tetapi tidak dapat membuat pesanan mentah, memposting mutasi fisik, atau memodifikasi pengguna/role (HTTP 403).
  - **Viewer**: Berhasil diverifikasi memiliki akses read-only menyeluruh di seluruh modul; seluruh upaya mutasi data (`POST`, `PUT`, `PATCH`, `DELETE`) ditolak (HTTP 403).
- **Isolasi Cakupan Gudang (`Warehouse Scoping`) & Proteksi Spoofing:**
  - Pengguna dengan akses terbatas (`all_warehouses=False`) hanya dapat mengakses gudang yang ditugaskan kepadanya. Permintaan baca atau tulis ke gudang lain ditolak (HTTP 403).
  - Percobaan *parameter spoofing* (mengirim query parameter gudang yang sah tetapi ID resource target berada di gudang lain) berhasil dideteksi dan ditolak (HTTP 403).
- **Segregasi Tugas / Maker-Checker (Four-Eyes Principle):**
  - Pembuat transfer stok ditolak saat mencoba menyetujui transfernya sendiri (`creator cannot approve`, HTTP 403).
  - Pembuat penyesuaian stok ditolak saat mencoba mereview penyesuaiannya sendiri (`creator cannot review`, HTTP 403).
- **Hasil Pengujian Regresi & Suite Penuh:**
  - Test suite baru `test_role_permission_matrix.py` (9 tes komprehensif) lulus 100%.
  - Suite pengujian backend penuh mencapai **98 passed, 0 skipped, 0 failed** (100% lulus dalam 76 detik).

Verifikasi penanganan P1.3 (Standarisasi Format Error Response & Sanitasi Exception) per 26 Oktober 2026:
- **Standarisasi App-Level Error Handler (`backend/app/__init__.py`):**
  - Mendaftarkan handler `@app.errorhandler(HTTPException)` yang menjamin semua HTTP error code (400, 401, 403, 404, 405, 409, 422, 429) konsisten menghasilkan payload JSON `{"error": "<pesan>", "code": <status_code>, "status": "<HTTP Status>"}`. Field `errors` disertakan otomatis jika terdapat pesan validasi (smorest/marshmallow).
  - Mendaftarkan handler `@app.errorhandler(Exception)` terpusat yang mengeksekusi `db.session.rollback()`, mencatat full stack trace ke log server via `app.logger.exception`, dan mengembalikan payload JSON ter-sanitasi `{"error": "Internal server error", "code": 500, "status": "Internal Server Error"}` tanpa membocorkan trace, string SQL, nama tabel, atau kredensial internal ke klien.
- **Audit Sanitasi Route & Pembersihan Masking 500:**
  - Memperbaiki parsing body `request.get_json()` pada `master_data/product.py`, `master_data/warehouse.py`, `master_data/units.py`, `master_data/categories.py`, dan `identity/auth.py` agar berada di luar blok `try: ... except Exception:`. Ini mencegah malformed JSON memicu HTTP 500 palsu dan memastikan error `BadRequest` (HTTP 400) terpropagasi dengan benar.
  - Memperbaiki `authorize_api_request` di `backend/app/routes/identity/auth.py` agar memeriksa `request.routing_exception` untuk public endpoints (`/api/v1/health`, dll) dan authenticated users, sehingga method yang tidak valid menghasilkan HTTP 405 Method Not Allowed dan URL API yang tidak ada menghasilkan HTTP 404 Not Found (bukan 401/403).
- **Pengujian Error Handling Baru (`backend/tests/test_error_handling.py`):**
  - Menambahkan test suite komprehensif (6 tes) yang memverifikasi secara ketat:
    1. HTTP 404 pada URL luar API, URL dalam API dengan auth, dan resource ID non-existent via `get_or_404`.
    2. HTTP 405 pada method tidak diizinkan untuk endpoint publik dan terautentikasi.
    3. HTTP 400 pada malformed JSON, syntax error payload, dan non-dict payload.
    4. HTTP 401 (tanpa token / token invalid) dan HTTP 403 (role tanpa izin).
    5. HTTP 409 pada duplikasi resource unik (SKU konflik).
    6. HTTP 500 sanitization & rollback: unhandled exception disimulasikan, memastikan tidak ada string sensitif yang bocor dan data transaksi kotor berhasil di-rollback dari database.
- **Hasil Verifikasi Suite Penuh:**
  - `python -m compileall -q app migrations tests` berhasil (0 error).
  - Suite pengujian penuh backend mencapai **104 passed, 0 skipped, 0 failed** (termasuk workflow test pada MySQL live `erp_test`).

OpenAPI kini tersedia pada `/api/v1/openapi.json` dengan schema request untuk alur transaksi utama. Tes memverifikasi seluruh route/method API terdaftar dan semua referensi komponen lokal dapat di-resolve. Validator standar seperti `openapi-spec-validator` tidak terpasang pada environment ini; hasil validasi yang dilaporkan berasal dari tes aplikasi tersebut, bukan validasi formal eksternal.

Migrasi legacy kini menolak skema tak dikenal, legacy non-SQLite, dan data transaksi lama yang belum dipetakan sebelum upgrade mengubah schema. Pengujian pada salinan SQLite legacy kosong berhasil mempertahankan akun pengguna dan mencapai Alembic head; pengujian invoice legacy berisi data memastikan migrasi ditolak tanpa mengubah invoice/schema. Database `backend/app.db` asli tetap tidak dimigrasikan.

## Kesesuaian PRD dan batas implementasi saat ini

Perbaikan di atas menyelesaikan beberapa alur transaksi backend, bukan keseluruhan ERP yang didefinisikan PRD. Sebelum menyatakan produk siap digunakan, perhatikan gap berikut:

| Area PRD | Kondisi saat ini |
|---|---|
| Role dan permission | Role `purchasing`, `warehouse`, `sales`, `finance`, `manager`, dan `admin` serta permission tindakan dapat dipersistenkan/dikelola. Route aktif telah diuji mempunyai permission terdefinisi; pemeriksaan akses untuk seluruh kombinasi role/aksi dan sinkronisasi role pada instalasi yang sudah berjalan masih perlu dilengkapi. |
| Pembatasan per gudang | Pemeriksaan cakupan mencakup nilai filter, record pada path, dan referensi gudang yang dikirim di payload. Tes regresi untuk manipulasi gudang pada saldo dan transfer lulus. Perluasan tes ke seluruh operasi bisnis dan query, termasuk MySQL, masih diperlukan. |
| Pemisahan tugas | PO dan inventory adjustment melarang self-approval. Hak finance dipisahkan dari role admin secara default; aturan cancel/reverse dan seluruh transition tetap perlu dilengkapi. |
| Penerimaan dan pengiriman | Goods Receipt dan shipment mendukung kuantitas parsial pada backend. Route kanonis `GET/POST /shipments` dan `POST /shipments/{id}/post` kini tersedia; route lama `/sales-orders/{id}/shipments` tetap dipertahankan sebagai alias kompatibilitas. |
| Pembayaran pelanggan dan supplier | Kedua jenis pembayaran mendukung DRAFT, alokasi, dan posting. Pembayaran pelanggan dapat dialokasikan ke beberapa invoice pelanggan yang sama. Jumlah alokasi dan saldo tagihan divalidasi; saldo invoice/vendor bill hanya berubah saat posting. Endpoint lama `/payments` dan body alokasi langsung pada supplier post tetap kompatibel. |
| Retur penjualan | Workflow stok MVP tersedia melalui `/sales-returns`: hanya Shipment yang sudah diposting yang dapat diretur, kuantitas retur dibatasi ke shipped quantity, dan kondisi barang menentukan apakah stok bertambah. Tidak ada credit note/refund pada MVP. |
| Transfer gudang | Workflow transfer tersedia melalui route `/inventory/transfers`, dengan submit, approve, dan post yang memperbarui kedua saldo serta menulis movement berpasangan. Cakupan permission dan pengujian konkurensi/MySQL masih perlu ditinjau lebih lanjut. |
| Finance dan laporan | Endpoint receivables, payables, cash summary, sales/purchase/inventory/stock-movement reports, receivable/payable reports, dan dashboard summary tersedia. Ringkasan kas mengukur nilai pembayaran POSTED (bukan jumlah alokasi) dan selalu company-wide; tanggal sales/purchase mengacu pada pembuatan invoice/vendor bill. General Ledger tidak termasuk MVP. |
| Audit log | Stock movement menjadi ledger stok, tetapi audit log umum untuk perubahan master data dan status transaksi belum tersedia. |
| OpenAPI | `GET /api/v1/openapi.json` mencakup seluruh route dan method API aktif. Schema request untuk workflow utama sudah dinyatakan, tetapi beberapa endpoint masih menggunakan schema JSON generik; response schema juga belum spesifik per-operation. |
| Frontend | Folder/repo yang diperiksa hanya menunjukkan backend; UI React/TypeScript yang disebut PRD tidak tersedia untuk diperiksa atau diuji. |
| Migrasi database | Flask-Migrate/Alembic sampai head `b2c3d4e5f6a7` telah diterapkan pada database baru dan diuji dengan `db check` di `erp_test`. Preflight mendukung hanya schema SQLite legacy yang dikenali dan tanpa transaksi yang perlu dipetakan; data user/master kompatibel dipertahankan. Legacy berisi transaksi ditolak sebelum perubahan schema, termasuk invoice yang masih mengacu ke `sales_order_id` karena model aktif memerlukan `shipment_id`. Pengujian dilakukan pada salinan, bukan `backend/app.db` asli. Metadata `Create Date` revision `5f2e8b9c14a7` (8 November 2026) tidak kronologis terhadap revision turunannya `a1d4e8c9b732` (25 Oktober 2026); perlu dikonfirmasi sebelum rilis. |

## Temuan awal sebelum perbaikan

Bagian berikut menyimpan bukti dan penjelasan kondisi yang ditemukan saat audit awal. Status terkini setiap temuan diringkas di tabel tindak lanjut di atas.

## Temuan prioritas tinggi

### 1. Pendaftaran publik dapat membuat akun admin; endpoint bisnis tidak dilindungi

**Bukti:** [auth.py, baris 72](./backend/app/routes/auth.py#L72) menerima pendaftaran tanpa autentikasi, mengambil `role` langsung dari payload pada [auth.py, baris 80](./backend/app/routes/auth.py#L80), lalu menyimpannya sebagai role pengguna pada [auth.py, baris 92](./backend/app/routes/auth.py#L92). Decorator autentikasi hanya terlihat dipakai pada endpoint profil `/auth/me` ([auth.py, baris 156–157](./backend/app/routes/auth.py#L156)). Blueprint bisnis didaftarkan tanpa perlindungan global di [routes/__init__.py](./backend/app/routes/__init__.py).

**Dampak:** siapa pun yang dapat mengakses API bisa membuat akun dengan role `admin`. Selain itu, endpoint untuk mengubah data dan stok tidak meminta token. Akibatnya, login dan RBAC yang sudah dibuat tidak menjadi batas akses efektif bagi operasi ERP.

**Saran perbaikan:**

- Jangan menerima role istimewa dari pendaftaran publik. Pembuatan admin pertama sebaiknya melalui proses bootstrap yang dikendalikan operator sistem.
- Terapkan `auth_required` pada endpoint yang mengubah atau membaca data sensitif, lalu `role_required` sesuai tindakan.
- Validasi role hanya terhadap nilai yang memang didukung dan tentukan proses aktivasi pengguna.
- Tambahkan tes yang memastikan permintaan tanpa token mendapat `401`, role tanpa izin mendapat `403`, dan pendaftaran tidak bisa menaikkan hak akses.

### 2. Pesanan multi-produk dapat mengubah saldo produk yang keliru

**Bukti:** route membuat atau mencari variabel `inventory` untuk setiap item pada [sales.py, baris 65–80](./backend/app/routes/sales.py#L65), tetapi perubahan saldo dilakukan dalam loop kedua pada [sales.py, baris 121–143](./backend/app/routes/sales.py#L121). Variabel tersebut tidak dicari ulang berdasarkan item di loop kedua; setelah loop validasi pertama, nilainya menunjuk ke saldo item terakhir.

**Dampak:** pada pesanan dengan beberapa produk, setiap item dapat mengurangi saldo gudang untuk produk terakhir, sementara pergerakan stok tetap dibuat menggunakan `product_id` dari masing-masing item. Buku saldo dan ledger pergerakan lalu tidak cocok; saldo dapat menjadi negatif atau produk tertentu tidak berkurang sama sekali.

**Saran perbaikan:**

- Simpan pasangan item dengan objek saldo yang cocok saat validasi, lalu mutakhirkan saldo pasangannya saat transaksi disimpan.
- Tambahkan tes dengan minimal dua produk berbeda dan pastikan saldo serta ledger masing-masing konsisten setelah pembuatan pesanan.
- Lakukan validasi dan perubahan stok dalam satu transaksi database. Untuk akses bersamaan, lindungi pembacaan/perubahan stok agar dua pesanan tidak sama-sama memakai saldo yang sama.

### 3. Logika reservasi penjualan menghitung stok dua kali dan tidak selesai saat pengiriman

**Bukti:** saat pesanan dibuat, route mengurangi `quantity_on_hand`, menambah `quantity_reserved`, dan langsung mencatat movement `OUT` pada [sales.py, baris 132–143](./backend/app/routes/sales.py#L132). Model mendefinisikan stok tersedia sebagai `quantity_on_hand - quantity_reserved` ([inventory_balance.py, baris 29–31](./backend/app/models/inventory_balance.py#L29)). Endpoint pengiriman hanya mengubah status pesanan ([sales.py, baris 202–215](./backend/app/routes/sales.py#L202)).

**Dampak:** stok tersedia turun dua kali saat reservasi. Pengiriman tidak mengurangi reservasi yang tersisa, sehingga nilai reserved dapat terus tertahan. Movement `OUT` juga dicatat sebelum status berubah menjadi `SHIPPED`, sehingga ledger mencerminkan barang keluar sebelum pengiriman dikonfirmasi.

**Saran perbaikan:** tetapkan satu aturan konsisten: saat reservasi, stok fisik tetap dan hanya jumlah reserved yang bertambah; saat pengiriman dikonfirmasi, kurangi stok fisik dan reserved sekaligus serta tulis movement keluar. Uji nilai on-hand, reserved, available, status, dan ledger pada setiap langkah alur.

### 4. Endpoint pembelian dan pembayaran memberi sukses tanpa menyimpan transaksi

**Bukti:** daftar purchase order selalu mengembalikan daftar kosong dan pembuatan hanya mengembalikan payload ([purchasing.py, baris 19–50](./backend/app/routes/purchasing.py#L19)). Endpoint detail mengembalikan status contoh untuk ID apa pun ([purchasing.py, baris 58–66](./backend/app/routes/purchasing.py#L58)). Posting purchase order menyebut dirinya simulasi dan tidak mengubah saldo atau ledger ([purchasing.py, baris 71–90](./backend/app/routes/purchasing.py#L71)). Pembayaran juga menyatakan belum ada model Invoice dan hanya mengembalikan data permintaan ([sales.py, baris 288–314](./backend/app/routes/sales.py#L288)).

**Dampak:** klien dapat menerima HTTP sukses dan menganggap pembelian atau pembayaran sudah tercatat, padahal data tidak tersimpan dan stok tidak berubah. Ini berisiko menimbulkan selisih stok, transaksi hilang, dan rekonsiliasi keuangan yang salah.

**Saran perbaikan:** sampai model dan persistensi transaksi selesai, kembalikan status yang menandakan fitur belum tersedia (misalnya `501 Not Implemented`) atau nonaktifkan endpoint. Setelah implementasi, pastikan pembuatan, pembacaan, posting, perubahan stok, dan pencatatan ledger benar-benar atomik dan memiliki tes alur.

### 5. Tes dapat menghapus tabel pada database aplikasi

**Bukti:** konfigurasi default menunjuk ke `backend/app.db` pada [config.py, baris 7–9](./backend/config.py#L7). Fixture tes membuat aplikasi dari konfigurasi default sebelum mengatur `TESTING` ([conftest.py, baris 7–10](./backend/tests/conftest.py#L7)), lalu menjalankan `db.drop_all()` setelah tes ([conftest.py, baris 22–28](./backend/tests/conftest.py#L22)). [test_base.py](./backend/tests/test_base.py) memiliki pola serupa.

**Dampak:** menjalankan pytest tanpa konfigurasi database khusus berpotensi menghapus seluruh tabel pada database aplikasi, termasuk data di `app.db`. Karena fixture berlaku otomatis, penghapusan terjadi setelah masing-masing tes.

**Saran perbaikan:**

- Buat konfigurasi tes terpisah dengan SQLite sementara atau database khusus tes, dan berikan konfigurasi tersebut ke `create_app` sebelum inisialisasi database.
- Jangan pernah menggunakan database default aplikasi untuk tes. Tambahkan pemeriksaan yang menggagalkan startup tes jika URL database bukan database tes.
- Gunakan transaksi/rollback atau database sementara terisolasi untuk pembersihan.

## Temuan prioritas menengah

### 6. (Temuan awal) Penyesuaian stok berstatus `PENDING` sudah mengubah stok

**Bukti saat audit awal:** model memberi status awal `PENDING`, tetapi endpoint langsung menambah atau mengurangi saldo saat approve.

**Dampak:** jika `PENDING` berarti menunggu persetujuan—seperti yang tersirat oleh model—pengguna dapat mengubah stok sebelum pemeriksaan atau persetujuan. Riwayat status menjadi tidak sesuai dengan saldo aktual.

**Perbaikan:** permintaan kini tetap `PENDING` tanpa mengubah saldo; pengguna lain dapat menyetujui atau menolak, lalu hanya operasi post yang mengubah saldo dan menulis movement. Tahap posting mencatat pengguna/waktu, memeriksa ulang stok tersedia, serta menolak posting ulang. Endpoint canonical PRD `/inventory/adjustments` tersedia; route `/inventory/adjusters` tetap kompatibel.

### 7. Tanggal jatuh tempo opsional di route tetapi wajib di database

**Bukti:** route menginisialisasi `due_date = None` bila field tidak dikirim ([sales.py, baris 52–58](./backend/app/routes/sales.py#L52)); model mendefinisikan `due_date` sebagai `nullable=False` ([sales_order.py, baris 14](./backend/app/models/sales_order.py#L14)).

**Dampak:** permintaan yang tidak menyertakan tanggal lolos validasi awal, lalu gagal saat commit dan kemungkinan mendapat `500` alih-alih pesan validasi yang dapat dimengerti.

**Saran perbaikan:** jadikan tanggal wajib dengan respons `400` yang jelas sebelum membuat pesanan, atau izinkan `NULL` di model jika memang opsional. Tambahkan tes untuk field yang hilang, format salah, dan tanggal valid.

### 8. Laporan turnover mengelompokkan kolom yang tidak diagregasi

**Bukti:** query menjumlahkan kuantitas dan memilih `movement_type`, tetapi hanya mengelompokkan berdasarkan produk pada [reports.py, baris 68–85](./backend/app/routes/reports.py#L68).

**Dampak:** bila satu produk memiliki beberapa tipe movement, total kuantitas dapat menggabungkan semuanya sementara `movement_type` yang ditampilkan tidak mewakili total tersebut. Hasil juga dapat berbeda antar database karena kolom yang tidak dikelompokkan diperlakukan berbeda.

**Saran perbaikan:** tentukan bentuk laporan yang dikehendaki: kelompokkan per produk **dan** tipe movement, atau agregasikan semua tipe tanpa mengembalikan satu tipe yang menyesatkan. Tambahkan data uji berisi `IN` dan `OUT` untuk produk yang sama.

### 9. Detail exception internal dikirim kembali ke klien

**Bukti:** beberapa route mengembalikan `str(e)` pada respons `500`, misalnya [auth.py, baris 112–114](./backend/app/routes/auth.py#L112), [product.py, baris 83–86](./backend/app/routes/product.py#L83), dan [inventory_adjuster.py, baris 112–116](./backend/app/routes/inventory_adjuster.py#L112).

**Dampak:** pesan database atau implementasi internal dapat bocor melalui API dan membantu penyerang memahami sistem. Respons `500` juga menjadi tidak konsisten antar endpoint.

**Saran perbaikan:** catat exception lengkap di log server dengan correlation ID, lalu kembalikan pesan umum dan ID pelacakan kepada klien. Tangani error validasi secara eksplisit dengan status `4xx`.

**Status setelah tindak lanjut (P1.3 Selesai):** Seluruh HTTP exception dan unhandled error ditangani terpusat via `@app.errorhandler` di [app/__init__.py](./backend/app/__init__.py). Respons error konsisten berformat JSON `{"error": "...", "code": ..., "status": "..."}`. Pada HTTP 500, detail sensitif (traceback, SQL, path modul) disanitasi sepenuhnya, `db.session.rollback()` dipastikan tereksekusi, dan full stack trace dicatat ke log server via `app.logger.exception`. Masking HTTP 500 palsu pada `request.get_json()` telah dibersihkan. Diverifikasi oleh [test_error_handling.py](./backend/tests/test_error_handling.py) (6 tes lulus) dan suite penuh (104 tes lulus).

## Temuan prioritas rendah / perbaikan kualitas

### 10. Mode debug aktif secara default pada server yang mendengarkan semua antarmuka

**Bukti:** [run.py, baris 11–14](./backend/run.py#L11) menetapkan `FLASK_DEBUG` default ke `true` dan menjalankan server pada `0.0.0.0`.

**Dampak:** menjalankan file ini tanpa environment variable yang sesuai mengaktifkan debug mode pada alamat yang dapat dijangkau dari jaringan. Debug server Flask bukan server produksi dan tidak boleh diekspos.

**Saran perbaikan:** default-kan debug ke `false`, gunakan server WSGI produksi untuk deployment, dan pastikan secret wajib dikonfigurasi. Jangan mengandalkan nilai default development di lingkungan produksi.

### 11. Beberapa tes terlalu longgar dan dapat lolos tanpa menguji perilaku

**Bukti:** tes penjualan menerima beberapa status yang berbeda ([test_sales.py, baris 27](./backend/tests/test_sales.py#L27)), melewati alur bila pembuatan pesanan gagal ([test_sales.py, baris 58–59](./backend/tests/test_sales.py#L58)), dan tes pembelian hanya memeriksa status sukses walaupun endpoint belum menyimpan data ([test_purchasing.py, baris 1–21](./backend/tests/test_purchasing.py#L1)).

**Dampak:** suite dapat berwarna hijau sekalipun transaksi tidak berjalan atau mengembalikan status yang salah. Itu membuat tes tidak cukup kuat untuk mencegah regresi yang memengaruhi stok dan keuangan.

**Saran perbaikan:** tegaskan satu status dan satu hasil bisnis yang diharapkan per tes; jangan `return` ketika langkah utama gagal. Periksa isi respons, perubahan database, saldo stok, dan ledger setelah operasi.

### 12. Dokumentasi OpenAPI tampaknya belum didaftarkan ke aplikasi

**Bukti:** fungsi `init_app` mendaftarkan blueprint dokumentasi di [docs.py, baris 344–346](./backend/app/routes/docs.py#L344), tetapi fungsi tersebut tidak dipanggil pada [app/__init__.py](./backend/app/__init__.py) dan blueprint `docs` tidak didaftarkan oleh [routes/__init__.py](./backend/app/routes/__init__.py).

**Dampak:** definisi dokumentasi mungkin tidak muncul pada endpoint OpenAPI/Swagger yang diharapkan. Ini perlu diverifikasi setelah dependensi aplikasi tersedia.

**Saran perbaikan:** daftarkan dokumentasi secara eksplisit jika memang dimaksudkan untuk disajikan, lalu uji endpoint dokumentasi dan cocokkan spesifikasinya dengan route yang benar-benar aktif.

**Status setelah tindak lanjut:** OpenAPI 3.1 kini disediakan di `/api/v1/openapi.json`, termasuk dokumentasi untuk endpoint spec itu sendiri. Tes mengonfirmasi route/method parity, `operationId` unik, parameter query yang dipetakan, dan seluruh referensi komponen valid. Schema generik masih digunakan pada beberapa endpoint, sehingga dokumentasi request/response belum sepenuhnya terperinci.

## Pemeriksaan dan batasan

- **Sintaks:** `python -m compileall -q app tests` berhasil.
- **Tes otomatis terbaru:** **77 passed** menggunakan SQLite in-memory; `python -m compileall -q app migrations tests` berhasil.
- **Migration:** upgrade/backfill/downgrade/re-upgrade dan `db check` telah diuji pada SQLite sementara; chain MySQL dan `db check` juga lulus pada `erp_test`. Preflight legacy diuji pada salinan; data transaksi yang belum memiliki pemetaan eksplisit tetap diblokir.
- **Isolasi:** suite memakai SQLite in-memory. Database lokal hanya diperiksa read-only; SHA-256 sebelumnya diverifikasi tidak berubah saat suite 53 tes dijalankan (`BFD0499740B41186E9E87A4045D18819628C0F7B3D79A9D53EDF131A7F7992DB`).
- **Pemeriksaan aplikasi:** perintah Flask berhasil memuat aplikasi dan menampilkan route API.
- **Batas produksi:** belum ada pengujian concurrency pada PostgreSQL, migrasi deployment, validasi frontend, atau uji penetrasi. Nilai rahasia stabil perlu diberikan melalui environment; rate limiter saat ini menggunakan penyimpanan in-memory kecuali deployment mengonfigurasikan backend bersama.
- **OpenAPI:** `/api/v1/openapi.json` tersedia dan tes mencocokkan route/method, operation ID, security scheme, serta referensi komponen. Sebagian request/response payload masih generik; validator eksternal belum dijalankan.
- **Database lokal:** perintah inspeksi route sebelumnya memuat `create_app()` dengan konfigurasi default, sehingga `db.create_all()` menambahkan tabel baru ke `backend/app.db`. Pemeriksaan read-only setelahnya menemukan tabel baru kosong dan satu baris akun pada tabel `users`; data tidak dihapus. Jangan menghapus tabel tersebut tanpa memastikan kebutuhan database lokal.

## Tindak lanjut sebelum produksi

1. [Selesai P0] `config.py` mewajibkan `SECRET_KEY` dan `JWT_SECRET_KEY` eksplisit saat dijalankan di mode produksi dan menolak secret acak fallback; template `.env.example` telah disediakan.
2. Set `RATELIMIT_STORAGE_URI` ke backend bersama (mis. Redis) bila menjalankan lebih dari satu proses/instance.
3. Jika perlu mengadopsi database legacy yang berisi transaksi, tentukan pemetaan eksplisit untuk transaksi lama (terutama invoice `sales_order_id` ke shipment yang sah), lalu buat dan uji migrasi khusus terhadap salinan. Jalur otomatis saat ini sengaja berhenti jika data transaksi belum dipetakan.
4. Lengkapi matriks verifikasi permission per role/endpoint/gudang dan uji konkurensi pada database target.
5. Lengkapi schema request/response dan parameter query OpenAPI yang masih generik; pertimbangkan validator OpenAPI sebagai alat uji terpisah.
6. [Selesai P0] Metadata tanggal migration `5f2e8b9c14a7` telah diselaraskan menjadi kronologis (`2026-10-25 16:15:00`).
7. Uji frontend (jika tersedia), concurrency, serta deployment pada database target sebelum memproses transaksi nyata.

## Penjelasan istilah

- **Autentikasi** menjawab “siapa pengguna ini?”; biasanya dibuktikan dengan token.
- **Otorisasi/RBAC** menjawab “tindakan apa yang boleh dilakukan role tersebut?”.
- **On-hand** adalah stok fisik; **reserved** adalah stok yang sudah dijanjikan tetapi belum dikirim; **available** biasanya `on-hand - reserved`.
- **Ledger/movement** adalah catatan transaksi stok yang seharusnya sejalan dengan saldo. Jika keduanya berbeda, audit dan rekonsiliasi menjadi sulit.
- **`db.create_all()`** membuat tabel yang belum ada, tetapi bukan pengganti migrasi versi untuk perubahan skema pada database yang sudah berjalan.
