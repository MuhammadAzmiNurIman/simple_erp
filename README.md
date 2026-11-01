# DistribuFlow ERP

DistribuFlow ERP adalah aplikasi ERP berbasis web untuk membantu usaha mengelola persediaan dan proses operasional dalam satu sistem. Aplikasi ini mencakup data master, gudang, pembelian, penjualan, keuangan sederhana, pelaporan, serta kontrol akses berbasis role dan cakupan gudang.

> **Status:** proyek ini dikembangkan sebagai aplikasi ERP modular dan portofolio. Sebelum digunakan untuk transaksi bisnis nyata, lakukan deployment staging/UAT, uji integrasi pada database target, serta siapkan backup dan pemulihan database.

## Fitur

- **Autentikasi dan akses:** login berbasis token, role/permission, pembatasan akses gudang, dan audit log untuk aktivitas penting.
- **Data master:** produk, kategori, satuan, pelanggan, supplier, dan gudang.
- **Persediaan:** saldo stok per gudang, pergerakan stok, stok minimum, reservasi, transfer antar-gudang, penyesuaian stok, dan pencatatan retur.
- **Pembelian:** Purchase Order (PO), persetujuan, penerimaan barang (Goods Receipt), tagihan supplier, dan pembayaran supplier.
- **Penjualan:** Sales Order (SO), persetujuan/reservasi, shipment, invoice, retur penjualan, dan pembayaran pelanggan.
- **Keuangan sederhana:** pemantauan piutang dan utang, alokasi pembayaran terhadap dokumen, serta ringkasan kas. Aplikasi ini tidak menyediakan General Ledger atau jurnal akuntansi lengkap.
- **Dashboard dan laporan:** ringkasan operasional, laporan persediaan, pergerakan stok, penjualan, pembelian, piutang, dan utang; laporan mendukung ekspor CSV.
- **API:** REST API versi `/api/v1` dengan spesifikasi OpenAPI di `/api/v1/openapi.json`.

### Aturan penting workflow

- Dokumen operasional mengikuti status draft, pengajuan/persetujuan bila diwajibkan, lalu posting sesuai permission.
- Persetujuan dan posting adalah tindakan berbeda. Persetujuan penyesuaian stok, misalnya, belum mengubah saldo sampai transaksi diposting.
- Barang retur berstatus `RESTOCK` menambah kembali stok saat retur diposting; barang `DAMAGED` tercatat sebagai rusak dan tidak dikembalikan ke stok tersedia.
- Sesuai lingkup MVP, retur penjualan belum mengubah saldo invoice atau pembayaran. Credit note/refund merupakan pengembangan lanjutan.
- Akses gudang mengikuti cakupan yang diberikan kepada pengguna. Pengguna yang perlu bekerja di gudang harus diberi penugasan gudang yang sesuai.

## Role pengguna

| Role | Tanggung jawab umum |
|---|---|
| `admin` | Administrasi sistem, pengguna, role/permission, master data, seluruh modul dan audit log. |
| `manager` | Pemantauan dan persetujuan transaksi sesuai kewenangan; tidak mengubah isi atau mem-posting transaksi operasional. |
| `purchasing` | Supplier, PO, pengajuan pembelian, dan proses terkait pembelian sesuai permission. |
| `warehouse` | Penerimaan, pengiriman, saldo dan mutasi stok, transfer serta pengajuan penyesuaian sesuai cakupan gudang. |
| `sales` | Pelanggan, SO, dan pemantauan proses pemenuhan pesanan sesuai permission. |
| `finance` | Invoice/tagihan, pembayaran, alokasi, piutang, utang, dan ringkasan keuangan sederhana. |
| `operator`, `viewer` | Role kompatibilitas yang masih tersedia; akses aktual mengikuti grant permission dan cakupan gudang pada sistem. |

> Permission efektif berasal dari grant role dan cakupan gudang akun. Jangan mengandalkan nama role saja untuk memutuskan akses.

## Teknologi

- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Lucide.
- **Backend:** Python, Flask, Flask-SQLAlchemy, Flask-Migrate/Alembic, Flask-Smorest.
- **Database deployment:** MySQL 8/InnoDB dengan driver PyMySQL.
- **Autentikasi:** JWT; access dan refresh token frontend disimpan dalam `sessionStorage`.
- **Rate limiting:** Flask-Limiter; Redis disarankan sebagai storage bersama saat aplikasi berjalan pada beberapa instance.

## Struktur repository

```text
.
├── backend/
│   ├── app/                 # Model, API routes, authorization, dan aplikasi Flask
│   ├── migrations/          # Migrasi schema Alembic
│   ├── tests/               # Test backend
│   ├── docs/                # Panduan deployment dan roadmap finansial
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── src/                 # Aplikasi React/TypeScript
│   └── package.json
├── docs/                    # Panduan pengujian manual
├── prd.md                   # Product Requirements Document
└── render.yaml              # Blueprint layanan Render
```

## Persyaratan lokal

- Python 3.10 atau lebih baru.
- Node.js dan npm yang mendukung versi Vite di `frontend/package.json`.
- MySQL 8 dengan InnoDB untuk menjalankan aplikasi sesuai konfigurasi deployment.
- Database terpisah untuk development, test integrasi, staging, dan produksi.

## Menjalankan aplikasi secara lokal

### 1. Siapkan backend

Di PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Buat database development MySQL kosong, misalnya `erp_dev`, lalu buat `backend/.env` secara lokal. Contoh variabel:

```dotenv
FLASK_ENV=development
DATABASE_URL=mysql+pymysql://USER:PASSWORD@localhost:3306/erp_dev?charset=utf8mb4
SECRET_KEY=<secret-development>
JWT_SECRET_KEY=<secret-development-berbeda>
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
RATELIMIT_STORAGE_URI=memory://
```

Gunakan kredensial dan secret khusus development. Jangan commit `.env`. Password yang mengandung karakter khusus perlu di-URL-encode pada `DATABASE_URL`.

> **Penting:** jangan arahkan migrasi ke database operasional atau `backend/app.db` lama. Pastikan database development yang dipilih memang database kosong yang ingin disiapkan.

Terapkan schema dan siapkan authorization pada database development baru:

```powershell
python -m flask --app run db upgrade
python -m flask --app run seed-authorization
python -m flask --app run create-admin
```

> `seed-authorization` dijalankan hanya untuk instalasi baru. Buat Admin pertama melalui prompt CLI, kemudian Admin dapat membuat akun dan menetapkan role serta cakupan gudang.

> Catatan: aplikasi memuat file environment dari `backend/.env`. Jangan menggunakan `backend/.env.example` mentah-mentah untuk development; file contoh berisi pola konfigurasi deployment.

Jalankan API:

```powershell
python run.py
```

Backend tersedia secara lokal pada `http://127.0.0.1:5000`.

### 2. Siapkan frontend

Buka terminal PowerShell kedua:

```powershell
cd frontend
npm ci
npm run dev
```

Buka alamat yang ditampilkan Vite, biasanya `http://localhost:5173`. Vite meneruskan request `/api` ke backend lokal. Login menggunakan akun yang dibuat oleh perintah backend `create-admin` atau `create-user`.

## Test dan build

Test backend menggunakan SQLite in-memory dan tidak menginisialisasi `backend/app.db`:

```powershell
cd backend
python -m pytest -q
```

> Test suite SQLite tidak menggantikan verifikasi integrasi pada MySQL/TiDB. Jalankan test integrasi hanya pada database disposable khusus dengan suffix `_test`, sesuai panduan backend. Jangan arahkan test ke database staging berisi data, apalagi database produksi.

Build frontend untuk memeriksa TypeScript dan menghasilkan asset produksi:

```powershell
cd frontend
npm run build
```

## Konfigurasi API dan deployment

- API memiliki prefix `/api/v1`; dokumentasi OpenAPI tersedia melalui `GET /api/v1/openapi.json`.
- Endpoint kesehatan tersedia di `/api/v1/health`.
- Frontend menerima `VITE_API_BASE_URL` saat build. Untuk API pada domain berbeda, isikan base URL penuh, misalnya `https://api.example.com/api/v1`.
- Backend produksi memerlukan `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`, dan `CORS_ORIGINS` eksplisit. Wildcard CORS ditolak dalam mode produksi.
- Simpan semua secret di environment/secret manager platform hosting, bukan di GitHub atau `render.yaml`.
- Untuk Vercel, hubungkan repository GitHub sebagai **dua proyek**: satu dengan Root Directory `backend`, satu lagi dengan Root Directory `frontend`. `backend/index.py` mengekspos aplikasi Flask sebagai WSGI function; `backend/vercel.json` dan `frontend/vercel.json` berisi konfigurasi build.
- Pada proyek backend Vercel, isi environment `FLASK_ENV=production`, `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, dan `RATELIMIT_STORAGE_URI`. Pada proyek frontend, isi `VITE_API_BASE_URL` dengan URL backend ditambah `/api/v1`. Environment frontend dimasukkan saat build; secret backend hanya berada di proyek backend.
- Aiven URL/credential tidak boleh disimpan di file konfigurasi atau commit. Gunakan connection string baru setelah merotasi credential yang terekspos. Sertifikat CA Aiven yang diperlukan berada di `backend/certs/aiven-ca.pem`; pastikan URL memakai path CA yang benar untuk root project backend.
- File `render.yaml` tetap tersedia sebagai opsi Render. Konfigurasi Render tidak membuat database TiDB/Aiven otomatis.
- Migrasi database adalah langkah deployment terpisah; jangan menjalankannya otomatis dari setiap worker. Backup dan uji pemulihan sebelum migrasi produksi.

> Paket hosting gratis cocok untuk staging/demo dan dapat memiliki keterbatasan uptime, resource, backup, serta penyimpanan. Verifikasi kebijakan provider saat deploy; gunakan layanan database dengan backup/pemulihan yang sesuai sebelum menyimpan transaksi operasional penting.

Panduan tambahan:

- [Panduan backend](backend/README.md)
- [Panduan frontend](frontend/README.md)
- [Deployment](backend/docs/DEPLOYMENT.md)
- [Pengujian manual fitur](docs/PANDUAN_UJI_MANUAL_FITUR.md)
- [PRD](prd.md)

## Catatan ruang lingkup

DistribuFlow ERP berfokus pada persediaan, pembelian, penjualan, multi-gudang, workflow persetujuan, dan simple-finance. Aplikasi ini bukan sistem akuntansi penuh; General Ledger, jurnal akuntansi lengkap, dan koreksi finansial retur melalui credit note/refund berada di luar cakupan MVP saat ini.
