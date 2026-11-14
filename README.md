# KatalogKu API

Backend praktikum II3160 Teknologi Sistem Terintegrasi, Week 7 Bagian B.
PocketBase 0.40.5 menyediakan API dan SQLite, sedangkan Nginx 1.28-alpine menjadi gateway.

## Tim

| Nama | NIM |
|---|---|
| Fikrifalah Muslich | 18224069 |
| Haidarrozan Pramasony | 18224103 |

Laporan singkat tersedia pada `18224069_18224103_Pocketbase.pdf`. Folder `bukti/` memuat
hasil pengujian API, Postman, persistensi, dan pemeriksaan container.

## Arsitektur

| Service | Port host default | Data |
|---|---|---|
| product-service | 127.0.0.1:8091 | volume product_data, collection products |
| account-service | 127.0.0.1:8092 | volume account_data, collections users dan favorites |
| gateway | 127.0.0.1:8080 | reverse proxy Nginx |

Favorit hanya menyimpan `user` dan `product_id`. Tidak ada relation database lintas service.
Detail produk diambil melalui product-service. ID produk pada favorit tidak divalidasi lintas service;
klien perlu menangani produk yang sudah dihapus.

## Persyaratan

- Docker Engine/Desktop yang berjalan dan Docker Compose v2.
- Python 3.10 atau lebih baru untuk setup dan pengujian otomatis, tanpa dependency Python tambahan.
- Internet untuk mengunduh base image dan binary PocketBase.
- Port 8080, 8091, dan 8092 tersedia, atau tentukan port alternatif pada `.env`.

Dockerfile memilih binary untuk amd64, arm64, atau arm/v7 dan memeriksa SHA256 rilis.
Periksa `uname -m` pada server sebelum memilih platform. Jalur offline sudah diuji pada STB ARM64;
build ARMv7 dan perangkat tujuan lain tetap perlu diverifikasi.

## Menjalankan

Jalankan perintah dari direktori proyek:

```sh
cp .env.example .env
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Pada PowerShell, gunakan `Copy-Item .env.example .env` untuk menyalin konfigurasi.
Jika 8080 dipakai layanan lain, ubah `GATEWAY_PORT=18080` dalam `.env`.
Gateway menunggu healthcheck kedua PocketBase. Dashboard tersedia pada
`http://localhost:8091/_/` dan `http://localhost:8092/_/`.

Port dashboard selalu terikat ke loopback host. Untuk administrasi remote, gunakan SSH forwarding:

```sh
ssh -L 8091:127.0.0.1:8091 -L 8092:127.0.0.1:8092 USER@SERVER
```

Untuk akses gateway dari LAN, ubah `GATEWAY_BIND=0.0.0.0` dan batasi akses sesuai jaringan server.
Default loopback dapat digunakan oleh Cloudflare Tunnel di jaringan Compose tanpa membuka dashboard.

## Superuser, schema, dan seed

```sh
python scripts/manage.py superusers
python scripts/manage.py bootstrap
```

Perintah pertama meminta email dan password untuk masing-masing service. Gunakan password unik
minimal 10 karakter. Password tidak ditampilkan dan dikirim ke container melalui stdin.
Perintah ini melakukan upsert: gunakan hanya untuk akun administrator yang memang ingin dibuat
atau diperbarui. Secret tidak perlu ditulis dalam `.env` atau file repository.

`bootstrap` meminta login superuser, memeriksa collection yang sudah ada, mengimpor schema
dengan `deleteMissing=false`, mengekspor schema aktual, lalu memasukkan lima produk dari
`seed/products.json`. Import dibatalkan jika schema collection berisi data berbeda dari schema
proyek. Lakukan backup dan tinjau migrasi secara terpisah pada kondisi tersebut.
Collection bawaan `users` yang masih kosong boleh dikonfigurasi pada setup pertama.

Pengulangan seed dan export:

```sh
python scripts/manage.py seed
python scripts/manage.py export
```

Seed memeriksa judul persis sebelum membuat produk. Produk yang sudah ada dilewati dan tidak
ditimpa. Jalankan seed satu proses pada satu waktu. `seed.http` tersedia sebagai alternatif manual
untuk database baru; POST manual yang diulang dapat membuat duplikasi.

Jika port dashboard berubah, tambahkan opsi, misalnya:

```sh
python scripts/manage.py bootstrap --product-url http://127.0.0.1:18091 --account-url http://127.0.0.1:18092
```

Untuk otomasi tersedia environment `KATALOGKU_PRODUCT_EMAIL`, `KATALOGKU_PRODUCT_PASSWORD`,
`KATALOGKU_ACCOUNT_EMAIL`, dan `KATALOGKU_ACCOUNT_PASSWORD`. Gunakan pengelolaan secret lokal;
jangan menulis nilainya ke script, log, atau repository.

## Schema dan akses

- `products`: list/view publik, create/update/delete terkunci untuk superuser.
- `users`: registrasi publik, list/view/update/delete hanya akun sendiri, manage terkunci.
- `favorites`: list/view/delete hanya pemilik, create hanya untuk user yang login dan dirinya sendiri,
  update terkunci. Unique index `(user, product_id)` menolak duplikasi dan relation user memakai cascade delete.

`price` wajib dikirim saat membuat produk, bertipe angka, dan minimal 0. PocketBase mengartikan
`NumberField.required=true` sebagai nilai bukan nol. Karena itu field schema memakai `required=false`
dan hook `pocketbase/pb_hooks/products.pb.js` memeriksa kehadiran serta tipe harga pada API.
Hook dipasang pada product-service melalui Compose dan tidak boleh dilepas saat deployment.
Gunakan nilai `price` langsung pada PATCH. Operasi modifier `price+` atau `price-` tidak didukung hook ini.
Import record langsung lewat SQL atau kode internal harus menjaga validasi harga sendiri.

`rating` dibatasi 0 sampai 5 dan `stock` harus integer nonnegatif. Thumbnail menggunakan URL.
Field data dan API Rules tersedia pada schema hasil export di `pb_schema/`.

## Endpoint gateway

| Method | Endpoint | Autentikasi |
|---|---|---|
| GET | /api/health | publik, `{"gateway":"ok"}` |
| GET | /api/products | publik |
| GET | /api/products/:id | publik |
| GET | /api/products?filter=title~%27kopi%27 | publik |
| POST | /api/auth/records | registrasi publik |
| POST | /api/auth/auth-with-password | email dan password |
| GET | /api/favorites | Bearer token, hasil tersaring berdasarkan pemilik |
| GET | /api/favorites/:id | Bearer token pemilik |
| POST | /api/favorites | Bearer token; body `{"user":"USER_ID","product_id":"PRODUCT_ID"}` |
| DELETE | /api/favorites/:id | Bearer token pemilik |

List mengikuti kontrak PocketBase: `items`, `page`, `perPage`, `totalItems`, `totalPages`.
Login menghasilkan `token` dan `record`. Status create PocketBase adalah 200 dan delete 204.
List favorit anonim menghasilkan **200 dengan daftar kosong**, sesuai filter API Rule.
View/delete record milik orang lain menghasilkan 404; create yang melanggar rule menghasilkan 400;
operasi dengan rule terkunci menghasilkan 403.

## Pengujian

```sh
python scripts/test_api.py --base-url http://127.0.0.1:8080
python scripts/test_api.py --base-url http://127.0.0.1:8080 --admin-tests
```

Mode biasa menguji endpoint, dua akun berbeda, isolasi favorit, duplikasi, dan akses produk.
`--admin-tests` juga meminta superuser product-service dan menguji validasi field serta CRUD admin
melalui gateway. Untuk port dashboard lain gunakan `--product-url`.
Akun, favorit, dan produk yang dibuat pengujian dibersihkan setelah selesai. Data lain tidak dihapus.
Hasil tersimpan pada `test-results.json` dan `test-results.md`, yang diabaikan Git.

REST Client: buka `api.http`, isi environment proses `KATALOGKU_TEST_EMAIL` yang unik dan
`KATALOGKU_TEST_PASSWORD`, lalu jalankan berurutan. `seed.http` memakai environment proses
`KATALOGKU_ADMIN_EMAIL` dan `KATALOGKU_ADMIN_PASSWORD`.

Postman: impor collection dan salah satu environment pada `postman/`, lalu jalankan seluruh collection
berurutan. Akun dan password pengujian dibuat otomatis, kemudian akun dihapus pada request terakhir.
Jika proses terhenti, bersihkan akun pengujian dan kosongkan variabel token/password sebelum export.
Ganti placeholder `SERVER_IP` atau `YOUR_DOMAIN` pada environment remote.

Alternatif menjalankan collection dari terminal:

```sh
npx newman run postman/KatalogKu-PocketBase.postman_collection.json -e postman/KatalogKu-Lokal.postman_environment.json
```

## Operasional dan verifikasi server

```sh
docker compose logs --tail=50 product-service account-service gateway
docker compose exec gateway nginx -t
docker compose restart
python scripts/test_api.py --admin-tests
```

Catat ID produk dan akun sebelum restart lalu pastikan record yang sama tetap tersedia.
Named volume terpisah menyimpan SQLite dan file. Jangan menghapus volume untuk menguji persistensi.
Sebelum backup file database, hentikan penulisan atau gunakan fitur backup bawaan PocketBase.

Jika Docker daemon tidak dapat dihubungi, jalankan/perbaiki Docker Desktop atau gunakan Docker Engine
di server Linux. `docker compose config --quiet` hanya memvalidasi konfigurasi, bukan keberhasilan container.
Jika gateway mengembalikan 502, periksa healthcheck dan log kedua PocketBase.
Perubahan hook membutuhkan restart product-service.

Pengujian pada STB ARM64 memakai Docker 26.1.4, Compose 2.28.1, PocketBase 0.40.5,
dan image nginx:1.28-alpine yang berisi Nginx 1.28.3. Ketiga container sehat, 55 pemeriksaan API
lulus, dan data tetap tersedia setelah restart serta pembuatan ulang ketiga container dengan
named volume yang sama. Pengujian native Windows sebelumnya juga lulus.

STB yang digunakan tidak dapat mengunduh dependency melalui HTTPS. Karena itu build yang diuji
memakai `Dockerfile.offline` dan `compose.offline.yml`, dengan image ARM64 dan binary PocketBase
yang diunduh serta diperiksa dari komputer lain. Jalur build online tetap tersedia pada Dockerfile
utama; pengunduhan online langsung dari STB belum berhasil.

Lihat [pengoperasian STB dan build offline](deploy/stb/README.md) untuk langkah yang benar-benar
digunakan, lokasi data, service Docker tambahan, dan akses administratif.

## Menuju Bagian C

Konfigurasi tunnel opsional dari starter tetap tersedia pada profile `tunnel`.
Masukkan token lokal ke `.env`, kemudian gunakan `docker compose --profile tunnel up -d` setelah
container utama terverifikasi. HTTPS publik dan integrasi aplikasi mobile dikerjakan terpisah.
Tidak ada token, database runtime, atau kredensial administrator dalam repository.

Referensi: [PocketBase v0.40.5](https://github.com/pocketbase/pocketbase/releases/tag/v0.40.5),
[API Rules](https://pocketbase.io/docs/api-rules-and-filters/),
[NumberField v0.40.5](https://github.com/pocketbase/pocketbase/blob/v0.40.5/core/field_number.go),
[Nginx proxy_pass](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass).
