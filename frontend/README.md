# DistribuFlow ERP frontend

Frontend React 19, TypeScript, Vite, Tailwind CSS v4, dan Lucide icons. UI saat ini mencakup login, dashboard, daftar sales order (termasuk pembuatan pesanan), inventory, purchase order, piutang, serta data master. Tampilan menyesuaikan perangkat mobile, tablet, dan desktop.

## Menjalankan aplikasi

1. Jalankan backend Flask di `http://127.0.0.1:5000`.
2. Dari folder `frontend`, pasang dependensi dan jalankan Vite:

   ```powershell
   npm install
   npm run dev
   ```

3. Buka alamat yang dicetak oleh Vite dan masuk menggunakan akun yang sudah dibuat melalui perintah CLI backend (`flask create-admin` atau `flask create-user`).

Vite meneruskan `/api/*` ke backend di `http://127.0.0.1:5000` secara default. Untuk backend di alamat berbeda, atur `VITE_API_PROXY_TARGET`, misalnya `http://localhost:5000`. Untuk mengakses API tanpa proxy, atur `VITE_API_BASE_URL` ke base URL lengkap, misalnya `https://erp.example.com/api/v1`.

Access dan refresh token hanya disimpan dalam `sessionStorage` dan dibuang saat logout atau ketika refresh token tidak lagi valid. Daftar sales order tanpa filter gudang menampilkan seluruh order yang berada dalam cakupan gudang pengguna; pembatasan otorisasi tetap diterapkan di backend.
