import base64
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile

import app

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aP1sAAAAASUVORK5CYII=')

def upload():
    return {'name':'pagina.png','content':base64.b64encode(PNG).decode()}

class StudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = app.DATA
        app.DATA = Path(self.temp.name)/'source'
    def tearDown(self):
        app.DATA = self.previous
        self.temp.cleanup()
    def test_complete_review_and_backup(self):
        ref = app.save(dict(kind='reference', name='Herói', status='Aprovado', details='Capa azul', upload=upload()))
        with self.assertRaises(ValueError):
            app.save(dict(kind='reference', id=ref, name='Mudança', status='Proposta'))
        app.save(dict(kind='bible', name='Traço', status='Aprovado', rules='Hachuras finas'))
        page = app.save(dict(kind='page', name='P01', refs=[ref], before='Espada na mão esquerda', after='Ferimento no braço', upload=upload()))
        with app.db() as c:
            original = next(r for r in app.records(c) if r['id']==page)['versions'][0]
        app.save(dict(kind='page', id=page, name='P01', refs=[ref], before='Espada na mão esquerda', after='Ferimento no braço', upload=upload()))
        issue = app.save(dict(kind='issue', name='Espada trocada', page=page, location='Quadro 2', severity='Alta', correction='Repor à esquerda', status='Aberto'))
        app.decide(dict(id=page, index=1, decision='Rejeitado', reason='Espada ainda invertida'))
        app.decide(dict(id=page, index=1, decision='Aprovado', reason='Inspeção manual concluída'))
        with self.assertRaises(ValueError):
            app.decide(dict(id=page, index=0, decision='Rejeitado', reason='Teste'))
        context, prompt = app.package(page)
        self.assertIn('Hachuras finas', prompt)
        self.assertIn('Espada na mão esquerda', prompt)
        self.assertEqual(context['defeitos_registrados'][0]['id'], issue)
        self.assertEqual(context['pagina']['versions'][0], original)
        self.assertEqual((app.DATA/'files'/original['file']).read_bytes(), PNG)
        with zipfile.ZipFile(io.BytesIO(app.archive(page))) as z:
            self.assertIn('prompt-work-astra.txt', z.namelist())
            self.assertEqual(len([n for n in z.namelist() if n.startswith('files/')]), 3)
        backup = Path(self.temp.name)/'backup.zip'
        backup.write_bytes(app.archive())
        target = Path(self.temp.name)/'restored'
        import os
        result = subprocess.run([sys.executable, 'app.py', '--restore', str(backup)], env={**os.environ, 'PROELIUM_DATA':str(target)}, capture_output=True, text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        with sqlite3.connect(target/'studio.sqlite3') as c:
            self.assertEqual(c.execute('SELECT count(*) FROM records').fetchone()[0],4)
            self.assertEqual(c.execute('SELECT count(*) FROM events').fetchone()[0],7)
        self.assertEqual((target/'files'/original['file']).read_bytes(),PNG)
        result = subprocess.run([sys.executable,'app.py','--restore',str(backup)],env={**os.environ,'PROELIUM_DATA':str(target)},capture_output=True)
        self.assertNotEqual(result.returncode,0)
    def test_ten_character_images_and_limit(self):
        rid = app.save(dict(kind='reference', name='Dez ângulos', uploads=[upload() for _ in range(10)]))
        with app.db() as c:
            r = next(r for r in app.records(c) if r['id']==rid)
        self.assertEqual(len(r['versions']), 10)
        self.assertNotIn('uploads', r)
        with self.assertRaises(ValueError):
            app.save(dict(kind='reference', id=rid, name='Dez ângulos', upload=upload()))
        self.assertEqual(len(list((app.DATA/'files').iterdir())),10)
        with self.assertRaises(ValueError):
            app.save(dict(kind='reference', name='Lote inválido', uploads=[upload(), {'name':'bad.png','content':base64.b64encode(b'not image').decode()}]))
        self.assertEqual(len(list((app.DATA/'files').iterdir())),10)

    def test_invalid_inputs(self):
        for payload in [dict(kind='page',name='Sem imagem'),dict(kind='reference',name=''),dict(kind='invalid',name='Teste'),dict(kind='reference',name='Arquivo',upload={'name':'x.svg','content':base64.b64encode(b'<svg/>').decode()})]:
            with self.assertRaises(ValueError):
                app.save(payload)

if __name__=='__main__':
    unittest.main()
