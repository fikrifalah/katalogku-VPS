# Pengoperasian STB

Pengujian dilakukan pada Armbian/Debian 13 ARM64 dengan Docker 26.1.4 dan Compose 2.28.1.
Proyek berada di `/opt/katalogku-pocketbase`. Gunakan `uname -m` untuk memastikan arsitektur
perangkat lain sebelum memakai aset ARM64.

## Docker Engine

Pada host pengujian, file unit vendor docker.service dan containerd.service kosong sehingga
dianggap masked. Unit tersebut dipertahankan. Docker dijalankan oleh unit terpisah
`katalogku-docker.service` dengan data pada `/opt/katalogku-runtime/docker`.

File service pada direktori ini khusus untuk kondisi tersebut. Jangan memasangnya jika Docker
Engine lain sudah berjalan atau memakai socket `/var/run/docker.sock`. Periksa juga agar subnet
172.29.0.0/16 tidak bertabrakan dengan jaringan host.

Pada host dengan binary Docker statis dan kondisi yang sama:

```sh
sudo install -d -m 700 /opt/katalogku-runtime
sudo install -m 644 deploy/stb/katalogku-docker.service /etc/systemd/system/katalogku-docker.service
sudo systemctl daemon-reload
sudo systemctl enable --now katalogku-docker.service
docker info
```

Service memakai containerd internal yang dijalankan dockerd dan storage driver overlay2.
Docker menambahkan aturan bridge/NAT yang dibutuhkannya. Pada host pengujian, aturan INPUT
tetap identik dan Nginx aaPanel tetap merespons HTTP 200 setelah deployment.

## Build offline

STB pengujian memiliki DNS yang bekerja, tetapi koneksi HTTPS keluar timeout. Dependency
diunduh pada komputer lain, kemudian ditransfer lewat SSH. Arsip distribusi terpisah
`katalogku-arm64-offline.zip` menyediakan kedua image ARM64, ZIP PocketBase, dan checksum rilis.
Arsip binary tidak masuk Git.

Untuk menyiapkan image sendiri pada komputer dengan internet dan Docker yang berfungsi:

```sh
docker pull --platform linux/arm64 alpine:3.22
docker pull --platform linux/arm64 nginx:1.28-alpine
docker save -o alpine-arm64.tar alpine:3.22
docker save -o nginx-arm64.tar nginx:1.28-alpine
```

Unduh `pocketbase_0.40.5_linux_arm64.zip` dan `checksums.txt` dari
[rilis PocketBase 0.40.5](https://github.com/pocketbase/pocketbase/releases/tag/v0.40.5).
Cocokkan SHA256 ZIP dengan checksum sebelum mengekstraknya. Pada PowerShell gunakan
`Get-FileHash -Algorithm SHA256 pocketbase_0.40.5_linux_arm64.zip`.

Setelah file ditransfer, jalankan dari direktori proyek di STB. Ganti `/path/to/assets` dengan
lokasi hasil ekstraksi arsip offline:

```sh
docker load -i /path/to/assets/alpine-arm64.tar
docker load -i /path/to/assets/nginx-arm64.tar
mkdir -p pocketbase/.offline
python3 -m zipfile -e /path/to/assets/pocketbase_0.40.5_linux_arm64.zip pocketbase/.offline
cp /etc/ssl/certs/ca-certificates.crt pocketbase/.offline/ca-certificates.crt
chmod 755 pocketbase/.offline/pocketbase
DOCKER_BUILDKIT=0 docker compose -f docker-compose.yml -f compose.offline.yml up -d --build --pull never
```

`DOCKER_BUILDKIT=0` digunakan karena host pengujian tidak memiliki plugin Buildx.
Base image, binary PocketBase, dan CA bundle sudah tersedia secara lokal sehingga build
tidak memerlukan internet. Kedua service tetap memiliki volume dan port internal terpisah.

## Setup dan pemeriksaan

Gunakan `scripts/manage.py superusers` dan `scripts/manage.py bootstrap` seperti pada README utama.
Untuk deployment pengujian, kredensial superuser acak disimpan pada
`/opt/katalogku-runtime/admin.json`, hanya dapat dibaca root, dan tidak berada di repository.
Tidak ada password administrator yang dicantumkan di dokumentasi.

```sh
docker compose -f docker-compose.yml -f compose.offline.yml ps
curl http://127.0.0.1:8080/api/health
python3 scripts/test_api.py --admin-tests
docker compose -f docker-compose.yml -f compose.offline.yml restart
```

Untuk membuka API dan dashboard melalui laptop:

```sh
ssh -N -L 18080:127.0.0.1:8080 -L 8091:127.0.0.1:8091 -L 8092:127.0.0.1:8092 USER@SERVER
```

API berada di `http://localhost:18080/api`, dashboard produk di `http://localhost:8091/_/`,
dan dashboard akun di `http://localhost:8092/_/`. Biarkan sesi SSH forwarding terbuka.
Backup database ditempatkan di media lain sesuai kapasitas disk host. Jangan menghapus volume
untuk menguji persistensi.
