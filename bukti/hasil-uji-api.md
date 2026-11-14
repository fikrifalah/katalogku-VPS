# Hasil uji API KatalogKu

Waktu UTC: 2026-11-08T15:35:05.427151+00:00

Gateway: `http://127.0.0.1:8080`. Runtime: STB ARM64; Docker 26.1.4; PocketBase 0.40.5; Nginx 1.28.3; 3 containers after recreate.

| Skenario | Diharapkan | Aktual | Status |
|---|---|---|---|
| GET /api/health | 200; gateway=ok | HTTP 200 | PASS |
| GET /api/products | 200; items, page, totalItems; lima produk seed | HTTP 200; totalItems=5 | PASS |
| Pagination dan query string | 200; page=2; perPage=2; dua item | HTTP 200; totalItems=5 | PASS |
| GET /api/products/:id | 200; id dan title cocok | HTTP 200 | PASS |
| Pencarian kopi | 200; seluruh hasil memuat kopi | HTTP 200; totalItems=1 | PASS |
| Produk tidak ditemukan | 404; error PocketBase | HTTP 404; error fields= | PASS |
| Batas route produk | 404 | HTTP 404 | PASS |
| Favorit tanpa login | 200; daftar kosong menurut listRule PocketBase | HTTP 200; totalItems=0 | PASS |
| Create produk anonim | 403; superuser diperlukan | HTTP 403; error fields= | PASS |
| Update produk anonim | 403; data tetap | HTTP 403; error fields= | PASS |
| Delete produk anonim | 403; produk tetap | HTTP 403; error fields= | PASS |
| Produk tidak berubah setelah akses ditolak | 200; seluruh field sama | HTTP 200 | PASS |
| Registrasi user A | 200; id tersedia; password/tokenKey tidak bocor | HTTP 200 | PASS |
| Login user A | 200; token dan record cocok | HTTP 200 | PASS |
| Login password salah A | 400; tidak ada token | HTTP 400; error fields= | PASS |
| Registrasi user B | 200; id tersedia; password/tokenKey tidak bocor | HTTP 200 | PASS |
| Login user B | 200; token dan record cocok | HTTP 200 | PASS |
| Login password salah B | 400; tidak ada token | HTTP 400; error fields= | PASS |
| Create favorit anonim | 400; createRule menolak | HTTP 400; error fields= | PASS |
| Tambah favorit A | 200; pemilik dan product_id cocok | HTTP 200 | PASS |
| List favorit A | 200; tepat satu record milik A | HTTP 200; totalItems=1 | PASS |
| View favorit A | 200; id cocok | HTTP 200 | PASS |
| Favorit duplikat | 400; unique index menolak | HTTP 400; error fields=product_id,user | PASS |
| List favorit B terisolasi | 200; kosong | HTTP 200; totalItems=0 | PASS |
| B membaca favorit A | 404; data tidak bocor | HTTP 404; error fields= | PASS |
| Anonim membaca favorit A | 404; data tidak bocor | HTTP 404; error fields= | PASS |
| B membuat favorit atas nama A | 400; createRule menolak | HTTP 400; error fields= | PASS |
| B menghapus favorit A | 404; data tetap ada | HTTP 404; error fields= | PASS |
| Update favorit terkunci | 403; updateRule null | HTTP 403; error fields= | PASS |
| B membaca user A | 404; data privat | HTTP 404; error fields= | PASS |
| List user hanya diri sendiri | 200; hanya user B | HTTP 200; totalItems=1 | PASS |
| Create produk user biasa | 403 | HTTP 403; error fields= | PASS |
| Update produk user biasa | 403 | HTTP 403; error fields= | PASS |
| Hapus favorit sendiri | 204; body kosong | HTTP 204 | PASS |
| Favorit sudah terhapus | 404 | HTTP 404; error fields= | PASS |
| List favorit setelah hapus | 200; kosong | HTTP 200; totalItems=0 | PASS |
| Delete user dan cascade favorit | 204 | HTTP 204 | PASS |
| Favorit cascade tidak dapat diakses | 404 | HTTP 404; error fields= | PASS |
| Superuser membuat produk harga nol | 200; price=0 | HTTP 200 | PASS |
| Harga wajib | 400; error field price | HTTP 400; error fields=price | PASS |
| Harga negatif | 400; error field price | HTTP 400; error fields=price | PASS |
| Harga bukan angka | 400; error field price | HTTP 400; error fields=price | PASS |
| Title wajib | 400; error field title | HTTP 400; error fields=title | PASS |
| Category wajib | 400; error field category | HTTP 400; error fields=category | PASS |
| Rating di atas 5 | 400; error field rating | HTTP 400; error fields=rating | PASS |
| Rating negatif | 400; error field rating | HTTP 400; error fields=rating | PASS |
| Stock pecahan | 400; error field stock | HTTP 400; error fields=stock | PASS |
| Stock negatif | 400; error field stock | HTTP 400; error fields=stock | PASS |
| Thumbnail bukan URL | 400; error field thumbnail | HTTP 400; error fields=thumbnail | PASS |
| Superuser update produk | 200; price=1.5; rating=5; stock=2 | HTTP 200 | PASS |
| Update harga invalid | 400; error field price | HTTP 400; error fields=price | PASS |
| Update harga menjadi nol | 200; price=0 | HTTP 200 | PASS |
| Update parsial tanpa price | 200; description berubah; price tetap 0 | HTTP 200 | PASS |
| Update harga null | 400; error field price | HTTP 400; error fields=price | PASS |
| Superuser delete produk pengujian | 204 | HTTP 204 | PASS |

55 dari 55 pemeriksaan lulus.
