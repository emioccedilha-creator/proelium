import argparse
import base64
import hashlib
import io
import json
import mimetypes
import os
from pathlib import Path
import sqlite3
import uuid
import zipfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).parent
DATA = Path(os.environ.get('PROELIUM_DATA', ROOT / 'data')).resolve()

def now():
    return datetime.now(timezone.utc).isoformat()

def db():
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / 'files').mkdir(exist_ok=True)
    c = sqlite3.connect(DATA / 'studio.sqlite3')
    c.row_factory = sqlite3.Row
    c.executescript('''CREATE TABLE IF NOT EXISTS records
        (id TEXT PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events
        (id INTEGER PRIMARY KEY, date TEXT, action TEXT, record_id TEXT, snapshot TEXT);''')
    return c

def records(c):
    return [dict(json.loads(r['body']), id=r['id'], kind=r['kind']) for r in c.execute('SELECT * FROM records ORDER BY rowid')]

def event(c, action, rid, body):
    c.execute('INSERT INTO events(date,action,record_id,snapshot) VALUES(?,?,?,?)',
              (now(), action, rid, json.dumps(body, ensure_ascii=False)))

def save(payload):
    kind = payload.get('kind')
    if kind not in ('reference', 'bible', 'page', 'issue', 'onboarding'):
        raise ValueError('Tipo inválido')
    rid = payload.get('id') or uuid.uuid4().hex
    with db() as c:
        old = c.execute('SELECT * FROM records WHERE id=?', (rid,)).fetchone()
        if old and old['kind'] != kind:
            raise ValueError('Tipo imutável')
        body = {k:v for k,v in payload.items() if k not in ('id', 'kind', 'upload', 'uploads', 'versions')}
        if not str(body.get('name', '')).strip():
            raise ValueError('Informe um nome')
        previous = json.loads(old['body']) if old else {}
        if kind in ('reference', 'bible') and previous.get('status') == 'Aprovado':
            raise ValueError('Item canônico aprovado é imutável. Cadastre uma nova proposta.')
        versions = previous.get('versions', [])
        uploads = payload.get('uploads', [payload['upload']] if payload.get('upload') else [])
        if not isinstance(uploads, list) or len(uploads) > (10 if kind == 'reference' else 1):
            raise ValueError('Use até 10 imagens por referência ou uma revisão por vez')
        if kind == 'reference' and len(versions) + len(uploads) > 10:
            raise ValueError('Limite de 10 imagens por personagem/referência')
        prepared = []
        for upload in uploads:
            raw = base64.b64decode(upload['content'], validate=True)
            if not raw or len(raw) > 25 * 1024 * 1024:
                raise ValueError('Arquivo vazio ou maior que 25 MB')
            signatures = ((b'\x89PNG\r\n\x1a\n', '.png'), (b'\xff\xd8\xff', '.jpg'), (b'RIFF', '.webp'))
            ext = next((e for s,e in signatures if raw.startswith(s)), None)
            if ext == '.webp' and raw[8:12] != b'WEBP':
                ext = None
            if ext is None:
                raise ValueError('Use uma imagem PNG, JPEG ou WebP')
            filename = uuid.uuid4().hex + ext
            prepared.append((filename, raw))
            versions.append(dict(file=filename, name=Path(upload['name']).name, date=now(),
                                 sha256=hashlib.sha256(raw).hexdigest(), decision='Referência' if kind == 'reference' else 'Original' if not versions else 'Pendente'))
        if kind == 'page' and not versions:
            raise ValueError('Importe a página original')
        for filename, raw in prepared:
            (DATA / 'files' / filename).write_bytes(raw)
        body['versions'] = versions
        body['updated'] = now()
        c.execute('INSERT OR REPLACE INTO records VALUES(?,?,?)', (rid, kind, json.dumps(body, ensure_ascii=False)))
        event(c, 'Atualização' if old else 'Cadastro', rid, body)
    return rid

def decide(payload):
    if payload.get('decision') not in ('Aprovado', 'Rejeitado') or not payload.get('reason', '').strip():
        raise ValueError('Informe a decisão e sua justificativa')
    with db() as c:
        row = c.execute('SELECT * FROM records WHERE id=? AND kind="page"', (payload['id'],)).fetchone()
        if not row:
            raise ValueError('Página não encontrada')
        body = json.loads(row['body'])
        index = int(payload['index'])
        if index <= 0 or index >= len(body['versions']):
            raise ValueError('O original não pode ser aprovado ou rejeitado como revisão')
        body['versions'][index].update(decision=payload['decision'], reason=payload['reason'])
        c.execute('UPDATE records SET body=? WHERE id=?', (json.dumps(body, ensure_ascii=False), payload['id']))
        event(c, payload['decision'], payload['id'], body)

def package(rid):
    with db() as c:
        all_records = records(c)
    page = next((r for r in all_records if r['id'] == rid and r['kind'] == 'page'), None)
    if not page:
        raise ValueError('Página não encontrada')
    refs = [r for r in all_records if r['kind'] == 'reference' and r['id'] in page.get('refs', [])]
    rules = [r for r in all_records if r['kind'] == 'bible' and r.get('status') == 'Aprovado']
    issues = [r for r in all_records if r['kind'] == 'issue' and r.get('page') == rid]
    context = dict(pagina=page, referencias=refs, biblia_aprovada=rules, defeitos_registrados=issues)
    prompt = '''Você está revisando o mangá Proelium. Analise minuciosamente a página anexada e compare-a com as referências fornecidas. Não invente cânone ausente; declare dúvidas. Preserve a assinatura gráfica aprovada, composição e intenção narrativa. Verifique anatomia, proporções, rostos, roupas, objetos, ferimentos, posições, perspectiva, luz, traço, balões e continuidade. Para cada defeito, informe localização (quadro e região), evidência, gravidade, correção específica e critério de aceite. Diferencie problemas observados de hipóteses. Proponha correções localizadas sem alterar elementos já corretos. Não afirme ter editado a imagem se apenas a analisou. Responda em português brasileiro. Use o estado de entrada e saída de continuidade abaixo e a página anterior quando fornecida.\n\nDADOS DO PROJETO:\n'''+json.dumps(context, ensure_ascii=False, indent=2)
    return context, prompt

def archive(rid=None):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        if rid:
            context, prompt = package(rid)
            z.writestr('prompt-work-astra.txt', prompt)
            z.writestr('revisao.json', json.dumps(context, ensure_ascii=False, indent=2))
            items = [context['pagina']] + context['referencias']
            files = {v['file'] for r in items for v in r.get('versions', [])}
            for name in files:
                z.write(DATA / 'files' / name, 'files/' + name)
        else:
            with db() as c:
                snapshot = sqlite3.connect(':memory:')
                c.backup(snapshot)
                z.writestr('database.sql', '\n'.join(snapshot.iterdump()))
                snapshot.close()
                z.writestr('exportacao.json', json.dumps(records(c), ensure_ascii=False, indent=2))
            for f in (DATA / 'files').iterdir():
                if f.is_file():
                    z.write(f, 'files/' + f.name)
    return out.getvalue()

class Handler(BaseHTTPRequestHandler):
    def respond(self, body, status=200, mime='application/json; charset=utf-8'):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path)
        try:
            if u.path == '/api/state':
                with db() as c:
                    return self.respond(dict(records=records(c), events=[dict(r) for r in c.execute('SELECT * FROM events ORDER BY id DESC')]))
            if u.path == '/api/package':
                return self.respond(dict(zip(('context', 'prompt'), package(parse_qs(u.query)['id'][0]))))
            if u.path in ('/api/backup', '/api/export'):
                return self.respond(archive(parse_qs(u.query).get('id', [None])[0]), mime='application/zip')
            if u.path.startswith('/files/'):
                name = u.path.removeprefix('/files/')
                if Path(name).name != name:
                    raise ValueError('Caminho inválido')
                return self.respond((DATA/'files'/name).read_bytes(), mime=mimetypes.guess_type(name)[0] or 'application/octet-stream')
            name = {'/':'index.html', '/app.js':'app.js', '/style.css':'style.css', '/generator.js':'generator.js', '/native.js':'native.js'}.get(u.path)
            if name:
                return self.respond((ROOT/'static'/name).read_bytes(), mime=mimetypes.guess_type(name)[0] + '; charset=utf-8')
            self.respond({'error':'Não encontrado'}, 404)
        except (ValueError, KeyError, FileNotFoundError) as e:
            self.respond({'error':str(e)}, 400)

    def do_POST(self):
        # Rejeita chamadas de outras origens e formulários de sites externos.
        if self.headers.get('Origin') not in (None, 'http://' + self.headers.get('Host', '')) or self.headers.get('Content-Type') != 'application/json':
            return self.respond({'error':'Origem ou conteúdo inválido'}, 403)
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length > 140 * 1024 * 1024:
                raise ValueError('Limite de upload excedido')
            payload = json.loads(self.rfile.read(length))
            if self.path == '/api/save':
                return self.respond({'id':save(payload)})
            if self.path == '/api/decide':
                decide(payload)
                return self.respond({'ok':True})
            self.respond({'error':'Não encontrado'}, 404)
        except (ValueError, KeyError, TypeError) as e:
            self.respond({'error':str(e)}, 400)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--restore', type=Path)
    args = parser.parse_args()
    if args.restore:
        if DATA.exists() and any(DATA.iterdir()):
            parser.error('Restaure apenas em PROELIUM_DATA vazio, preservando os dados atuais.')
        with zipfile.ZipFile(args.restore) as z:
            names = z.namelist()
            if 'database.sql' not in names:
                parser.error('Backup inválido')
            for name in names:
                if name.startswith('files/') and Path(name).name == name[6:]:
                    target = DATA / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(z.read(name))
            with db() as c:
                c.executescript('DROP TABLE records; DROP TABLE events;')
                c.executescript(z.read('database.sql').decode())
        print('Backup restaurado.')
    else:
        db().close()
        print(f'Proelium Studio: http://127.0.0.1:{args.port}', flush=True)
        ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
