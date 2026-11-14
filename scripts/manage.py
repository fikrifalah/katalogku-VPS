"""Setup superuser, import schema, export, dan seed melalui API PocketBase."""
import argparse
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


class ApiError(Exception):
    def __init__(self, status, data):
        self.status, self.data = status, data
        super().__init__(f'HTTP {status}: {data.get("message", "Request gagal")}')


def request(base, path, method='GET', data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = Request(base.rstrip('/') + path, method=method, headers=headers,
                  data=None if data is None else json.dumps(data).encode())
    try:
        with urlopen(req, timeout=20) as response:
            body = response.read()
            return response.status, json.loads(body) if body else None
    except HTTPError as error:
        try:
            body = json.loads(error.read())
        except ValueError:
            body = {'message': error.reason}
        raise ApiError(error.code, body) from None


def credentials(service):
    prefix = 'KATALOGKU_' + service.upper()
    email = os.environ.get(prefix + '_EMAIL') or input(f'Email superuser {service}: ').strip()
    password = os.environ.get(prefix + '_PASSWORD') or getpass.getpass(f'Password superuser {service}: ')
    if not email or '\n' in email or '\n' in password or len(password) < 10:
        raise ValueError('Email wajib diisi dan password minimal 10 karakter tanpa newline.')
    return email, password


def authenticate(base, email, password):
    return request(base, '/api/collections/_superusers/auth-with-password', 'POST',
                   {'identity': email, 'password': password})[1]['token']


def collection(base, name, token):
    try:
        return request(base, '/api/collections/' + name, token=token)[1]
    except ApiError as error:
        if error.status == 404:
            return None
        raise


def signature(value):
    return {key: item for key, item in value.items() if key not in ('created', 'updated')}


def preflight(base, schemas, token):
    for desired in schemas:
        current = collection(base, desired['name'], token)
        if current is None or signature(current) == signature(desired):
            continue
        params = urlencode({'perPage': 1})
        count = request(base, f'/api/collections/{desired["name"]}/records?{params}', token=token)[1]['totalItems']
        if count:
            raise ValueError(f'Import dihentikan: schema {desired["name"]} berbeda dan berisi {count} record. Backup dan tinjau migrasi terlebih dahulu.')


def import_schema(base, schemas, token):
    request(base, '/api/collections/import', 'PUT',
            {'collections': schemas, 'deleteMissing': False}, token)


def export_schema(base, schemas, token, path):
    exported = [collection(base, schema['name'], token) for schema in schemas]
    path.write_text(json.dumps(exported, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def seed(base, token):
    products = json.loads((ROOT / 'seed/products.json').read_text(encoding='utf-8'))
    created = skipped = 0
    for product in products:
        # Judul dari data seed tetap, bukan input filter dari klien.
        params = urlencode({'filter': 'title=' + json.dumps(product['title']), 'perPage': 2})
        existing = request(base, '/api/collections/products/records?' + params, token=token)[1]
        if existing['totalItems']:
            skipped += 1
            continue
        request(base, '/api/collections/products/records', 'POST', product, token)
        created += 1
    print(f'Seed: {created} dibuat, {skipped} sudah ada; data lama tidak diubah.')
    return created, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['superusers', 'bootstrap', 'seed', 'export'])
    parser.add_argument('--product-url', default=os.environ.get('PRODUCT_URL', 'http://127.0.0.1:8091'))
    parser.add_argument('--account-url', default=os.environ.get('ACCOUNT_URL', 'http://127.0.0.1:8092'))
    args = parser.parse_args()
    if args.action == 'superusers':
        for service in ('product', 'account'):
            email, password = credentials(service)
            # Secret dikirim melalui stdin, bukan argumen command pada host.
            shell = 'IFS= read -r email; IFS= read -r password; exec pocketbase superuser upsert "$email" "$password" --dir=/pb_data'
            result = subprocess.run(['docker', 'compose', 'exec', '-T', service + '-service', 'sh', '-c', shell],
                                    input=email + '\n' + password + '\n', text=True, cwd=ROOT, capture_output=True)
            if result.returncode:
                raise RuntimeError(f'Pembuatan superuser {service} gagal. Periksa status service.')
            print(f'Superuser {service} siap.')
        return
    services = [('product', args.product_url)]
    if args.action != 'seed':
        services.append(('account', args.account_url))
    configs = []
    for service, base in services:
        token = authenticate(base, *credentials(service))
        path = ROOT / f'pb_schema/{service}_collections.json'
        schemas = json.loads(path.read_text(encoding='utf-8'))
        configs.append((base, token, path, schemas))
    if args.action == 'bootstrap':
        for base, token, path, schemas in configs:
            preflight(base, schemas, token)
        for base, token, path, schemas in configs:
            import_schema(base, schemas, token)
            export_schema(base, schemas, token, path)
            print(f'Import dan export {path.name} selesai.')
        seed(configs[0][0], configs[0][1])
    elif args.action == 'export':
        for base, token, path, schemas in configs:
            export_schema(base, schemas, token, path)
            print(f'Export {path.name} selesai.')
    else:
        seed(configs[0][0], configs[0][1])


if __name__ == '__main__':
    try:
        main()
    except (ApiError, ValueError, RuntimeError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
