"""Uji integrasi melalui Nginx dengan akun dan produk sementara."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import sys
from urllib.parse import urlencode

from manage import ApiError, authenticate, credentials, request


def run(base, admin_token=None):
    results, users, products = [], [], []

    def call(path, method='GET', data=None, token=None):
        try:
            return request(base, path, method, data, token)
        except ApiError as error:
            return error.status, error.data

    def check(name, expected, action, predicate):
        status, body = action()
        try:
            passed = bool(predicate(status, body))
        except (TypeError, KeyError, IndexError):
            passed = False
        actual = f'HTTP {status}'
        if isinstance(body, dict) and 'totalItems' in body:
            actual += f'; totalItems={body["totalItems"]}'
        if isinstance(body, dict) and 'data' in body and isinstance(body['data'], dict):
            actual += '; error fields=' + ','.join(body['data'])
        results.append({'scenario': name, 'expected': expected, 'actual': actual,
                        'status': 'PASS' if passed else 'FAIL'})
        print(('PASS' if passed else 'FAIL') + ' ' + name + ': ' + actual)
        if not passed:
            raise AssertionError(name)
        return body

    def error(code, field=None):
        return lambda s, b: s == code and bool(b.get('message')) and b.get('status', b.get('code')) == code and (field is None or field in b.get('data', {}))

    try:
        check('GET /api/health', '200; gateway=ok', lambda: call('/api/health'), lambda s, b: s == 200 and b == {'gateway': 'ok'})
        listing = check('GET /api/products', '200; items, page, totalItems; lima produk seed',
                        lambda: call('/api/products?perPage=50&sort=title'),
                        lambda s, b: s == 200 and b['page'] == 1 and b['totalItems'] >= 5 and
                        {'Kemeja Batik Parang', 'Kopi Gayo 250 gr', 'Teh Hijau Organik', 'Earphone Bluetooth', 'Power Bank 10000 mAh'} <= {p['title'] for p in b['items']})
        product = listing['items'][0]
        check('Pagination dan query string', '200; page=2; perPage=2; dua item',
              lambda: call('/api/products?page=2&perPage=2&sort=title'),
              lambda s, b: s == 200 and b['page'] == 2 and b['perPage'] == 2 and len(b['items']) == 2)
        check('GET /api/products/:id', '200; id dan title cocok', lambda: call('/api/products/' + product['id']),
              lambda s, b: s == 200 and b['id'] == product['id'] and b['title'] == product['title'])
        check('Pencarian kopi', '200; seluruh hasil memuat kopi',
              lambda: call('/api/products?' + urlencode({'filter': "title~'kopi'"})),
              lambda s, b: s == 200 and b['totalItems'] >= 1 and all('kopi' in p['title'].lower() for p in b['items']))
        check('Produk tidak ditemukan', '404; error PocketBase', lambda: call('/api/products/zzzzzzzzzzzzzzz'), error(404))
        check('Batas route produk', '404', lambda: call('/api/products-extra'), lambda s, b: s == 404)
        check('Favorit tanpa login', '200; daftar kosong menurut listRule PocketBase', lambda: call('/api/favorites'),
              lambda s, b: s == 200 and b['totalItems'] == 0 and b['items'] == [])
        check('Create produk anonim', '403; superuser diperlukan', lambda: call('/api/products', 'POST', {'title': 'forbidden'}), error(403))
        check('Update produk anonim', '403; data tetap', lambda: call('/api/products/' + product['id'], 'PATCH', {'title': 'forbidden'}), error(403))
        check('Delete produk anonim', '403; produk tetap', lambda: call('/api/products/' + product['id'], 'DELETE'), error(403))
        check('Produk tidak berubah setelah akses ditolak', '200; seluruh field sama', lambda: call('/api/products/' + product['id']),
              lambda s, b: s == 200 and all(b[k] == v for k, v in product.items()))

        for label in ('A', 'B'):
            email = 'test-' + secrets.token_hex(10) + '@katalogku.test'
            password = secrets.token_urlsafe(24)
            record = check('Registrasi user ' + label, '200; id tersedia; password/tokenKey tidak bocor',
                           lambda: call('/api/auth/records', 'POST', {'email': email, 'password': password, 'passwordConfirm': password, 'name': 'Integration ' + label}),
                           lambda s, b: s == 200 and bool(b['id']) and 'password' not in b and 'tokenKey' not in b)
            user = {'id': record['id'], 'token': None}
            users.append(user)
            auth = check('Login user ' + label, '200; token dan record cocok',
                         lambda: call('/api/auth/auth-with-password', 'POST', {'identity': email, 'password': password}),
                         lambda s, b: s == 200 and bool(b['token']) and b['record']['id'] == record['id'])
            user['token'] = auth['token']
            check('Login password salah ' + label, '400; tidak ada token',
                  lambda: call('/api/auth/auth-with-password', 'POST', {'identity': email, 'password': secrets.token_urlsafe(24)}),
                  lambda s, b: error(400)(s, b) and 'token' not in b)
        a, b = users
        favorite = {'user': a['id'], 'product_id': product['id']}
        check('Create favorit anonim', '400; createRule menolak', lambda: call('/api/favorites', 'POST', favorite), error(400))
        fav = check('Tambah favorit A', '200; pemilik dan product_id cocok', lambda: call('/api/favorites', 'POST', favorite, a['token']),
                    lambda s, r: s == 200 and r['user'] == a['id'] and r['product_id'] == product['id'])
        path = '/api/favorites/' + fav['id']
        check('List favorit A', '200; tepat satu record milik A', lambda: call('/api/favorites', token=a['token']),
              lambda s, r: s == 200 and r['totalItems'] == 1 and r['items'][0]['id'] == fav['id'])
        check('View favorit A', '200; id cocok', lambda: call(path, token=a['token']), lambda s, r: s == 200 and r['id'] == fav['id'])
        check('Favorit duplikat', '400; unique index menolak', lambda: call('/api/favorites', 'POST', favorite, a['token']), error(400))
        check('List favorit B terisolasi', '200; kosong', lambda: call('/api/favorites', token=b['token']),
              lambda s, r: s == 200 and r['items'] == [] and r['totalItems'] == 0)
        check('B membaca favorit A', '404; data tidak bocor', lambda: call(path, token=b['token']), error(404))
        check('Anonim membaca favorit A', '404; data tidak bocor', lambda: call(path), error(404))
        check('B membuat favorit atas nama A', '400; createRule menolak', lambda: call('/api/favorites', 'POST', favorite, b['token']), error(400))
        check('B menghapus favorit A', '404; data tetap ada', lambda: call(path, 'DELETE', token=b['token']), error(404))
        check('Update favorit terkunci', '403; updateRule null', lambda: call(path, 'PATCH', favorite, a['token']), error(403))
        check('B membaca user A', '404; data privat', lambda: call('/api/auth/records/' + a['id'], token=b['token']), error(404))
        check('List user hanya diri sendiri', '200; hanya user B', lambda: call('/api/auth/records', token=b['token']),
              lambda s, r: s == 200 and r['totalItems'] == 1 and r['items'][0]['id'] == b['id'])
        check('Create produk user biasa', '403', lambda: call('/api/products', 'POST', {'title': 'forbidden'}, a['token']), error(403))
        check('Update produk user biasa', '403', lambda: call('/api/products/' + product['id'], 'PATCH', {'title': 'forbidden'}, a['token']), error(403))
        check('Hapus favorit sendiri', '204; body kosong', lambda: call(path, 'DELETE', token=a['token']), lambda s, r: s == 204 and r is None)
        check('Favorit sudah terhapus', '404', lambda: call(path, token=a['token']), error(404))
        check('List favorit setelah hapus', '200; kosong', lambda: call('/api/favorites', token=a['token']),
              lambda s, r: s == 200 and r['items'] == [] and r['totalItems'] == 0)
        cascade = call('/api/favorites', 'POST', favorite, a['token'])
        assert cascade[0] == 200
        check('Delete user dan cascade favorit', '204', lambda: call('/api/auth/records/' + a['id'], 'DELETE', token=a['token']), lambda s, r: s == 204)
        a['deleted'] = True
        check('Favorit cascade tidak dapat diakses', '404', lambda: call('/api/favorites/' + cascade[1]['id'], token=a['token']), error(404))

        if admin_token:
            def create_product(payload):
                response = call('/api/products', 'POST', payload, admin_token)
                if response[0] == 200 and response[1].get('id'):
                    products.append(response[1]['id'])
                return response

            template = {'title': 'Integration ' + secrets.token_hex(8), 'category': 'test', 'price': 0, 'rating': 0, 'stock': 0}
            record = check('Superuser membuat produk harga nol', '200; price=0', lambda: create_product(template),
                           lambda s, r: s == 200 and r['price'] == 0)
            for name, fields, field in [
                ('Harga wajib', {'price': None}, 'price'),
                ('Harga negatif', {'price': -1}, 'price'),
                ('Harga bukan angka', {'price': 'abc'}, 'price'),
                ('Title wajib', {'title': ''}, 'title'),
                ('Category wajib', {'category': ''}, 'category'),
                ('Rating di atas 5', {'rating': 5.1}, 'rating'),
                ('Rating negatif', {'rating': -1}, 'rating'),
                ('Stock pecahan', {'stock': 1.2}, 'stock'),
                ('Stock negatif', {'stock': -1}, 'stock'),
                ('Thumbnail bukan URL', {'thumbnail': 'bad-url'}, 'thumbnail'),
            ]:
                payload = template | fields
                if fields == {'price': None}:
                    payload.pop('price')
                check(name, f'400; error field {field}', lambda p=payload: create_product(p), error(400, field))
            check('Superuser update produk', '200; price=1.5; rating=5; stock=2',
                  lambda: call('/api/products/' + record['id'], 'PATCH', {'price': 1.5, 'rating': 5, 'stock': 2}, admin_token),
                  lambda s, r: s == 200 and r['price'] == 1.5 and r['rating'] == 5 and r['stock'] == 2)
            check('Update harga invalid', '400; error field price',
                  lambda: call('/api/products/' + record['id'], 'PATCH', {'price': 'bad'}, admin_token), error(400, 'price'))
            check('Update harga menjadi nol', '200; price=0',
                  lambda: call('/api/products/' + record['id'], 'PATCH', {'price': 0}, admin_token), lambda s, r: s == 200 and r['price'] == 0)
            check('Update parsial tanpa price', '200; description berubah; price tetap 0',
                  lambda: call('/api/products/' + record['id'], 'PATCH', {'description': 'Uji update parsial'}, admin_token),
                  lambda s, r: s == 200 and r['description'] == 'Uji update parsial' and r['price'] == 0)
            check('Update harga null', '400; error field price',
                  lambda: call('/api/products/' + record['id'], 'PATCH', {'price': None}, admin_token), error(400, 'price'))
            check('Superuser delete produk pengujian', '204', lambda: call('/api/products/' + record['id'], 'DELETE', token=admin_token), lambda s, r: s == 204)
            products.remove(record['id'])
    finally:
        for user in users:
            if user.get('token') and not user.get('deleted'):
                status, _ = call('/api/auth/records/' + user['id'], 'DELETE', token=user['token'])
                if status != 204:
                    results.append({'scenario': 'Cleanup akun pengujian', 'expected': '204', 'actual': f'HTTP {status}', 'status': 'FAIL'})
        for product_id in products:
            status, _ = call('/api/products/' + product_id, 'DELETE', token=admin_token)
            if status != 204:
                results.append({'scenario': 'Cleanup produk pengujian', 'expected': '204', 'actual': f'HTTP {status}', 'status': 'FAIL'})
        run.results = results
    return results


def save_report(path, results, base, runtime):
    report = {'timestamp': datetime.now(timezone.utc).isoformat(), 'gateway': base,
              'runtime': runtime, 'results': results}
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# Hasil uji API KatalogKu', '', f'Waktu UTC: {report["timestamp"]}', '',
             f'Gateway: `{base}`. Runtime: {runtime}.', '',
             '| Skenario | Diharapkan | Aktual | Status |', '|---|---|---|---|']
    lines += ['| ' + ' | '.join(row[k].replace('|', '/') for k in ('scenario', 'expected', 'actual', 'status')) + ' |' for row in results]
    lines += ['', f'{sum(r["status"] == "PASS" for r in results)} dari {len(results)} pemeriksaan lulus.', '']
    path.with_suffix('.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8080')
    parser.add_argument('--admin-tests', action='store_true')
    parser.add_argument('--product-url', default='http://127.0.0.1:8091')
    parser.add_argument('--report', type=Path, default=Path('test-results.json'))
    parser.add_argument('--runtime', default='Runtime tidak dicatat')
    args = parser.parse_args()
    token = authenticate(args.product_url, *credentials('product')) if args.admin_tests else None
    try:
        rows = run(args.base_url, token)
    except Exception as error:
        save_report(args.report, getattr(run, 'results', []), args.base_url, args.runtime)
        print(str(error), file=sys.stderr)
        sys.exit(1)
    save_report(args.report, rows, args.base_url, args.runtime)
    sys.exit(0 if all(r['status'] == 'PASS' for r in rows) else 1)
