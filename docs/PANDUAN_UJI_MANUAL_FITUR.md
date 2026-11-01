# Panduan Uji Manual DistribuFlow ERP

Panduan ini untuk memeriksa aplikasi melalui browser secara langsung. Jalankan alur pada database lokal atau salinan uji, bukan data operasional, karena posting transaksi mengubah saldo stok, invoice, pembayaran, dan audit log.

## 1. Menjalankan aplikasi

Pastikan konfigurasi backend pada `backend/.env` menunjuk database yang memang akan dipakai untuk uji. Jangan menjalankan migrasi terhadap `backend/app.db` lama atau database operasional tanpa backup dan pemeriksaan migrasi terlebih dahulu.

Buka dua terminal:

**Terminal backend**

```powershell
cd "E:\Muhammad Azmi Nur Iman\portofolio\erp\backend"
python -m flask --app run run --debug
```

**Terminal frontend**

```powershell
cd "E:\Muhammad Azmi Nur Iman\portofolio\erp\frontend"
npm run dev
```

Buka alamat lokal yang dicetak Vite (biasanya `http://localhost:5173`). Periksa backend di `http://127.0.0.1:5000/api/v1/health`; respons sehat seharusnya HTTP 200. Jika dependensi belum terpasang, backend memakai `requirements.txt` dan frontend memakai `npm install` di folder masing-masing.

Login menggunakan akun yang sudah ada. Proyek tidak menetapkan password demo tetap. Jika belum memiliki admin, buat akun dengan CLI `python -m flask --app run create-admin` dari folder backend; perintah ini meminta username, email, dan password secara interaktif. Jangan membuat akun baru atau menjalankan seed/migrasi pada database yang tidak diketahui isinya.

## 2. Siapkan data dan akun uji

Gunakan **Data master** sebagai Admin untuk menyiapkan data yang belum tersedia:

1. Buat minimal dua gudang aktif, misalnya `JKT` dan `BDG`, agar uji transfer dan cakupan gudang dapat dilakukan.
2. Siapkan kategori, satuan, produk aktif, supplier aktif, dan pelanggan aktif.
3. Catat stok awal produk di gudang sumber melalui fitur saldo awal jika akun memiliki izin tersebut. Pastikan produk memiliki stok yang cukup untuk pengiriman dan transfer.
4. Di **Pengguna & role**, buat akun uji dengan password sementara minimal 12 karakter, pilih role, lalu pilih cakupan gudang. Admin mendapat akses semua gudang; role lain perlu diberi minimal satu gudang. Untuk transfer, pelaku yang membuat/mem-posting dan Manager yang menyetujui harus memiliki cakupan ke gudang asal dan tujuan.
5. Siapkan akun terpisah untuk pembuat dan penyetuju. Sistem menolak persetujuan oleh pembuat transaksi pada workflow yang menerapkan pemisahan tugas.

Jika pilihan gudang kosong atau muncul `A permitted warehouse scope is required`, kembali ke **Pengguna & role → Atur gudang** pada akun itu, pilih gudang aktif, simpan, lalu logout/login ulang. Pastikan gudang yang dipilih benar-benar ada dan akun tidak sedang memakai session lama.

## 3. Pemeriksaan menu dan batas role

Menu yang tersedia antara lain **Ringkasan**, **Pesanan penjualan**, **Persediaan**, **Workflow operasional**, **Laporan**, **Pembelian**, **Tagihan & pembayaran**, **Data master**, **Audit log**, dan **Pengguna & role**. Menu/tombol dapat berbeda menurut permission; backend tetap menjadi pemeriksa akses utama.

| Role | Periksa hal berikut |
| --- | --- |
| Admin | Dapat membuka seluruh modul, seluruh gudang, pengguna/role, dan audit log. Aksi penting tercatat di audit log. |
| Operator | Bisa melihat dan menyiapkan transaksi operasional yang diizinkan. Tidak melihat pengelolaan pengguna, permission, atau audit log; tidak memiliki akses finance berdasarkan profil default; tidak boleh menyetujui/posting tanpa permission khusus. |
| Manager | Bisa melihat laporan/status dan menyetujui transaksi yang menunggu otorisasi dalam cakupan gudangnya. Tidak mengubah isi atau mem-posting transaksi operasional. |
| Viewer | Hanya membaca data yang diizinkan. Pastikan tombol buat/ubah/hapus/setujui/posting tidak tersedia dan aksi langsung melalui API akan ditolak. |
| Purchasing | Mengelola supplier dan PO; mengajukan PO; tidak menyetujui PO sendiri atau mengelola pembayaran supplier. Posting penerimaan bergantung pada izin yang diberikan. |
| Warehouse | Menangani stok fisik, penerimaan, shipment, adjustment, transfer, retur, dan karantina sesuai permission serta cakupan gudang. Tidak mengelola pembayaran. |
| Sales | Mengelola pelanggan dan SO, memantau shipment/invoice sesuai akses; tidak mem-posting shipment atau pembayaran pada profil default. |
| Finance | Mengelola invoice, vendor bill, pembayaran dan alokasi; tidak mengubah penerimaan/pengiriman atau stok yang sudah diposting. |

**Uji penolakan akses:** login sebagai Viewer lalu pastikan tombol transaksi tidak ada. Login sebagai Purchasing dan pastikan menu finance/persetujuan PO tidak terbuka. Login sebagai Manager dan pastikan tidak ada kontrol edit/posting operasional. Munculnya menu saja bukan bukti keamanan; untuk pemeriksaan API, operasi tanpa izin harus menghasilkan HTTP 403.

## 4. Uji siklus pembelian sampai tagihan supplier

1. Login sebagai **Purchasing**. Buka **Pembelian**, buat PO dengan supplier, gudang, produk, kuantitas, dan biaya satuan. Simpan sebagai draft.
2. Periksa PO muncul dengan status `DRAFT`. Jika masih draft, ubah data lalu ajukan. Status seharusnya menjadi `SUBMITTED`.
3. Logout dan login sebagai **Manager** yang memiliki cakupan gudang PO. Setujui PO. Status berubah menjadi `APPROVED`; akun pembuat tidak boleh menyetujui PO sendiri.
4. Login sebagai Purchasing atau Warehouse dengan izin penerimaan. Pada **Pembelian**, pilih PO yang disetujui dan buat draft Goods Receipt (GR) sesuai jumlah fisik yang benar-benar diterima. Periksa GR muncul di daftar penerimaan.
5. Login sebagai **Warehouse** yang memiliki izin posting untuk gudang tersebut. Posting GR. Status berubah menjadi `POSTED`, saldo stok bertambah, dan pergerakan stok tercatat.
6. Login sebagai **Finance**, buka **Tagihan & pembayaran**. Vendor bill untuk GR yang diposting seharusnya muncul otomatis sebagai tagihan supplier dengan saldo terbuka.
7. Catat pembayaran supplier, pilih vendor bill, masukkan jumlah alokasi (boleh sebagian), pilih metode, lalu alokasikan dan posting. Periksa saldo vendor bill berkurang sesuai jumlah yang dibayar dan pembayaran tampil pada riwayat.

**Yang perlu dicatat bila gagal:** PO tidak tersedia untuk GR biasanya belum berstatus `APPROVED`, gudang PO di luar scope, atau akun tidak memiliki `goods_receipts.create`. GR tidak mengubah stok sampai di-posting oleh akun berizin. Vendor bill baru dihasilkan setelah GR diposting.

## 5. Uji siklus penjualan sampai penerimaan pembayaran

1. Login sebagai **Sales**. Buka **Data master → Pelanggan** jika perlu menambah/mengubah pelanggan; pastikan akun mendapat izin customers. Buat SO dengan pelanggan, gudang, produk, jumlah, dan harga yang tersedia.
2. SO baru akan langsung mereservasi stok dan tampil berstatus `RESERVED`. Periksa SO tampil pada **Pesanan penjualan**. Uji ubah data sebelum diajukan; lalu ajukan SO dan pastikan status menjadi `SUBMITTED`. Uji pembatalan pada SO uji dan pastikan reservasi yang belum dikirim dilepas.
3. Login sebagai **Manager**, setujui SO yang berstatus menunggu. Pastikan Manager tidak dapat mengubah rincian atau mem-posting shipment.
4. Login sebagai **Warehouse** dengan `shipments.create`. Di **Pesanan penjualan**, pilih SO yang disetujui dan buat shipment; uji pengiriman parsial jika dibutuhkan. Periksa kuantitas tidak melebihi sisa yang dapat dikirim.
5. Posting shipment dengan akun yang memiliki `shipments.post`. Saldo on-hand berkurang dan shipment berstatus `POSTED`.
6. Login sebagai **Finance**, buka **Tagihan & pembayaran → Pengiriman siap ditagihkan**. Buat invoice dari shipment yang sudah diposting. Invoice harus muncul di daftar invoice/piutang.
7. Catat pembayaran pelanggan. Pilih invoice, masukkan nilai penuh atau sebagian, pilih metode, lalu alokasikan dan posting. Periksa jumlah terbayar bertambah dan balance due berkurang. Jangan mengalokasikan lebih dari saldo pembayaran atau saldo invoice.

## 6. Uji transfer gudang dan penyesuaian stok

### Transfer

1. Pastikan ada dua gudang aktif dan produk mempunyai stok tersedia di gudang asal.
2. Login sebagai **Warehouse** dengan scope ke kedua gudang. Buka **Workflow operasional → Transfer gudang**; pilih gudang asal, gudang tujuan (tidak boleh sama dengan asal), produk, kuantitas, dan alasan. Simpan draft.
3. Ajukan transfer. Login sebagai **Manager** dengan akses ke kedua gudang, kemudian setujui transfer. Jangan gunakan akun pembuat sebagai penyetuju.
4. Login kembali sebagai Warehouse yang punya izin posting dan posting transfer.
5. Periksa status `POSTED`: stok asal turun, stok tujuan naik dengan kuantitas sama. Pada daftar transfer, cari transaksi dengan gudang itu sebagai asal maupun tujuan.

Jika hanya ada satu gudang aktif, uji transfer lintas gudang memang belum bisa dilakukan. Buat gudang kedua dahulu dan beri cakupan kedua gudang kepada pelaku serta Manager.

### Penyesuaian stok

1. Di **Workflow operasional → Penyesuaian stok**, pilih saldo produk/gudang, jenis tambah atau kurangi, jumlah, dan keterangan; ajukan.
2. Status awal harus menunggu persetujuan. Login sebagai Manager atau penyetuju lain yang diizinkan dan setujui/tolak pengajuan. Pembuat tidak boleh menyetujui pengajuannya sendiri.
3. Setelah disetujui, login sebagai Warehouse/Admin dengan `inventory.adjust.post`, lalu posting.
4. Pastikan hanya setelah posting saldo berubah dan pergerakan stok tercatat; posting ulang harus ditolak.

## 7. Uji retur dan stok karantina/rusak

1. Retur harus merujuk **shipment yang sudah diposting**. Jika belum ada, selesaikan dahulu siklus penjualan sampai langkah shipment.
2. Login sebagai Sales atau akun dengan izin retur. Buka **Workflow operasional → Retur penjualan**, pilih shipment dan item, masukkan kuantitas, kondisi (`Layak dijual kembali` atau `Rusak`), dan alasan. Simpan draft.
3. Login sebagai Warehouse dengan izin posting retur, lalu posting retur.
4. Untuk item layak jual, saldo stok tersedia bertambah. Untuk item rusak, saldo stok jual tidak bertambah; buka tab **Karantina & barang rusak** untuk memeriksa kuantitas dan asal retur.
5. Untuk mengeluarkan stok dari karantina, Warehouse ajukan keputusan **scrap** atau **pelepasan ke stok** beserta alasan/referensi pemeriksaan. Manager menyetujui; Warehouse yang berizin mem-posting keputusan.
6. Periksa status karantina berubah (`Di-scrap` atau `Dilepas ke stok`) dan stok normal hanya bertambah jika pelepasan diposting.

Pada kebijakan MVP saat ini, retur tidak membuat credit note/refund dan tidak mengurangi invoice atau pembayaran pelanggan. Retur hanya mencatat kondisi barang dan dampak stok sesuai disposition.

## 8. Uji dashboard, inventaris, laporan, dan audit

1. **Ringkasan:** coba filter gudang dan periode. Cocokkan jumlah on-hand, reservasi, tersedia, serta nilai stok dengan **Persediaan**. Nilai stok saat ini dihitung dari stok fisik/on-hand × biaya rata-rata, sehingga mencakup stok yang sedang direservasi. Perhatikan akses finance dapat menyembunyikan metrik finansial.
2. **Persediaan:** pastikan tabel menampilkan gudang, produk, on-hand, reservasi, tersedia, biaya rata-rata, dan nilai. Cocokkan pergerakan setelah GR, shipment, transfer, retur, dan adjustment.
3. **Laporan:** buka masing-masing laporan **Stok**, **Pergerakan stok**, **Penjualan**, **Pembelian**, **Piutang**, dan **Utang**. Coba tanggal, gudang, produk, status, pelanggan, atau supplier sesuai laporan; klik **Tampilkan**, navigasikan halaman berikut/sebelumnya, lalu **Ekspor CSV**. File CSV harus berisi seluruh hasil filter, bukan hanya halaman yang sedang terlihat, dan dapat dibuka di Excel.
4. Jika filter pelanggan/produk/supplier tampil sebagai ID, bukan nama, akun mungkin tidak memiliki permission baca master terkait. Admin dapat meninjau permission; jangan menambahkan akses lebih luas hanya untuk kenyamanan tanpa memastikan kebijakan.
5. **Audit log:** login sebagai Admin, buka **Audit log**, filter pengguna/aksi/endpoint, dan cari aksi yang baru dilakukan. Waktu, aksi, endpoint/resource, hasil HTTP, serta ID pengguna harus sesuai. Login sebagai role lain dan pastikan halaman tidak tersedia tanpa `audit_logs.read`.
6. **OpenAPI:** buka `http://127.0.0.1:5000/api/v1/openapi.json`. Pastikan dokumen JSON berhasil dimuat; gunakan schema request/response untuk membaca format endpoint. Uji satu endpoint tanpa token/permission hanya jika nyaman memakai browser devtools atau klien API; diharapkan mendapat 401/403, bukan berhasil mengubah data.

## 9. Cek tampilan pada ukuran layar

Ulangi beberapa halaman inti—Ringkasan, Pembelian, Workflow operasional, Finance, Laporan, Data master—pada lebar mobile (sekitar 390 px), tablet (sekitar 768 px), dan desktop. Periksa tidak ada tombol penting terpotong, dialog dapat digulir, form tetap dapat dipakai, tabel bisa digulir horizontal bila memang lebar, dan pesan error/sukses terlihat. Browser DevTools memiliki mode perangkat untuk mengubah viewport.

## 10. Catat hasil pemeriksaan

Gunakan catatan sederhana untuk tiap langkah: **Lulus / Gagal / Tidak dapat diuji**, nama akun dan role, gudang aktif, nomor dokumen, status sebelum/sesudah, pesan error persis, serta screenshot bila ada. Saat menemukan kegagalan, catat apakah terjadi di frontend (tombol/menu tidak ada), API (HTTP 401/403/4xx/5xx), atau hasil data (status/saldo tidak berubah). Jangan mengirim password, token, atau isi secret dalam screenshot/log.

