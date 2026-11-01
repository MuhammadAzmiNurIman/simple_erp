# Catatan Perubahan

## 2026-10-26 — Pengelolaan pelanggan untuk Sales

- Role Sales dapat menambahkan pelanggan dari **Data master → Pelanggan**; kode pelanggan dibuat otomatis oleh backend.
- Sales dapat mengubah nama, email, telepon, alamat, dan status aktif pelanggan. Deaktivasi melalui status mempertahankan histori transaksi.
- Aksi hanya ditampilkan jika akun memiliki `customers.manage`; akses tetap dibatasi oleh permission backend.

## 2026-10-26 — Cakupan Finance per gudang

- Pembacaan invoice, pembayaran, tagihan supplier, piutang, utang, dan ringkasan kas kini mengikuti cakupan gudang akun Finance.
- Halaman Finance memakai daftar gudang yang memang ditugaskan ke akun. Akun non-Admin tanpa gudang tidak lagi mengirim permintaan tanpa filter dan menampilkan arahan agar Admin menetapkan gudang melalui **Pengguna → Atur gudang**.
- Daftar gudang memiliki permission baca tersendiri dan hanya mengembalikan gudang dalam cakupan akun. Ini memungkinkan Finance membuka pemilih gudang tanpa memberi akses baca ke seluruh master data.
- ID gudang pertama yang ditugaskan dipilih saat akun dimuat agar dashboard tidak membuat permintaan awal tanpa `warehouse_id`.
- Permintaan daftar pembayaran supplier pada halaman Purchasing meneruskan filter gudang yang sedang dipilih.
- Migrasi `e1f2a3b4c5d6` memperbarui metadata permission Finance lama; `e2f3a4b5c6d7` menambahkan permission `warehouses.read` beserta grant role bawaan.

## 2026-10-26 — Filter gudang di halaman Finance

- Endpoint Finance menerima parameter `warehouse_id` untuk memfilter data per gudang.
- Pemilihan gudang memfilter daftar invoice, ringkasan piutang, pembayaran pelanggan, dan pembayaran supplier melalui parameter `warehouse_id`.
- Pembayaran pelanggan ditampilkan jika terhubung langsung atau dialokasikan ke invoice pada gudang terpilih. Pembayaran supplier ditampilkan jika memiliki alokasi ke tagihan dari penerimaan pada gudang terpilih.
- Cakupan frontend dan backend kini mengikuti penugasan gudang akun Finance seperti dijelaskan pada pembaruan di atas.

## 2026-10-26 — Workflow gudang, karantina, dan perapian frontend

### Cakupan gudang pengguna

- Form **Tambah pengguna** kini memungkinkan Admin memilih satu atau beberapa gudang untuk akun non-Admin.
- Admin dapat mengubah pilihan gudang untuk akun lama melalui tombol **Atur gudang** pada daftar pengguna.
- Cakupan disimpan melalui `warehouse_ids` yang sudah didukung backend dan tabel `user_warehouse_access`; perubahan ini tidak memerlukan migrasi database.
- Akun Admin tetap otomatis mencakup seluruh gudang. Pengguna perlu memuat ulang aplikasi atau masuk kembali agar daftar gudang pada sesinya ikut diperbarui.

### Transfer antargudang

- Alur di **Workflow operasional → Transfer gudang** mencakup pembuatan draft, pengajuan, persetujuan Manager, dan posting oleh Warehouse.
- Pembuat dan pem-posting transfer serta Manager yang menyetujui perlu memiliki cakupan akses ke gudang asal dan tujuan.
- Pada posting, kuantitas berkurang dari gudang asal dan bertambah di gudang tujuan, dengan pergerakan stok tercatat.
- Pilihan gudang tujuan hanya menampilkan gudang aktif yang termasuk dalam cakupan akun. Jika gudang tujuan belum terdaftar, Admin perlu menambahkannya di **Data master → Gudang**.

### Retur rusak dan karantina

- Item retur dengan kondisi `DAMAGED` masuk ke stok karantina saat retur diposting; barang tidak langsung menambah stok tersedia.
- Tab **Karantina & barang rusak** menampilkan catatan karantina dan riwayat tindakannya.
- Warehouse dapat mengajukan pelepasan kembali ke stok atau scrap. Manager dapat menyetujui atau menolak pengajuan. Warehouse dapat mem-posting keputusan yang disetujui.
- Pelepasan menambah stok tersedia dan mencatat pergerakan stok. Scrap menutup status barang karantina; pencatatan jurnal atau koreksi nilai finansial belum termasuk dalam lingkup ini.
- Migrasi `d0e1f2a3b4c5` membuat tabel karantina dan aksi, menambahkan permission untuk Admin/Warehouse/Manager, serta mengimpor retur rusak terdahulu yang sudah diposting. Migrasi telah diterapkan pada database aktif.

### Tampilan frontend

- Sidebar, area kerja, kartu, form, dan panel workflow memakai gaya visual yang lebih konsisten.
- Navigasi gudang menyesuaikan breakpoint layar; tab workflow dan laporan dapat digeser di layar kecil.
- Ditambahkan indikator fokus keyboard dan penyesuaian sentuhan untuk penggunaan mobile.

### Pemeriksaan

- `npm run build` pada frontend berhasil.
- Pemeriksaan sintaks Python backend berhasil.
- Migrasi database berakhir pada revisi `d0e1f2a3b4c5`.

### Batasan yang diketahui

- Aplikasi saat ini mengelola gudang untuk satu konteks perusahaan. Belum ada model multi-perusahaan; data perusahaan yang masing-masing memiliki gudang sendiri memerlukan pengembangan terpisah.
- Pengguna baru non-Admin sekarang harus diberi setidaknya satu gudang melalui form. Untuk transfer, pilih seluruh gudang yang perlu diakses oleh staf Warehouse dan Manager terkait.
