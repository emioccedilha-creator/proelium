"""Teste opcional da versão portátil, sem servidor e com perfil temporário."""
import base64
import os
from pathlib import Path
import tempfile
import zipfile
import json
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
import threading
import atexit
from playwright.sync_api import sync_playwright
png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aP1sAAAAASUVORK5CYII=')
# O Chromium gerenciado deste ambiente bloqueia file:// por política.
# O servidor de teste fornece apenas o HTML; não há backend de aplicação.
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(Path(__file__).resolve().parents[1]/'dist')))
threading.Thread(target=server.serve_forever,daemon=True).start()
atexit.register(server.server_close)
url=f'http://127.0.0.1:{server.server_port}/Proelium%20Studio.html'
with tempfile.TemporaryDirectory() as temp:
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'),headless=True,args=['--no-sandbox'])
  page=b.new_page(viewport={'width':1440,'height':1000})
  errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  network=[]
  page.on('request',lambda r:network.append(r.url) if r.url.startswith(('http:','https:')) and r.url!=url else None)
  page.goto(url)
  page.get_by_role('button',name='Cadastrar primeiro personagem').click()
  page.locator('[name=name]').fill('Ariadne')
  page.locator('[name=details]').fill('Capa azul; espada na mão esquerda')
  page.locator('[name=status]').select_option('Aprovado')
  page.get_by_role('button',name='Salvar registro').click()
  page.locator('#modal').wait_for(state='hidden')
  page.get_by_role('button',name='Personagens',exact=True).click()
  page.get_by_role('button',name='Consultar cânone').click()
  assert page.locator('[name=name]').is_disabled()
  page.get_by_role('button',name='Cancelar').click()
  page.get_by_role('button',name='Páginas',exact=True).click()
  page.get_by_role('button',name='+ Importar página').click()
  page.locator('[name=name]').fill('Página 1')
  page.locator('[name=before]').fill('Capa azul; sem ferimentos')
  page.locator('[name=after]').fill('Ferimento no braço direito')
  page.locator('[name=refs]').select_option(label='Ariadne · Aprovado')
  page.locator('[name=image]').set_input_files({'name':'original.png','mimeType':'image/png','buffer':png})
  page.get_by_role('button',name='Salvar registro').click()
  page.locator('#modal').wait_for(state='hidden')
  page.get_by_role('button',name='Abrir página').click()
  assert 'Capa azul' in page.locator('#prompt').input_value()
  page.get_by_role('button',name='+ Registrar defeito').click()
  page.locator('[name=name]').fill('Ferimento incorreto')
  page.locator('[name=location]').fill('Quadro 2, braço esquerdo')
  page.locator('[name=correction]').fill('Transferir ferimento para o braço direito')
  page.get_by_role('button',name='Salvar registro').click()
  page.locator('#modal').wait_for(state='hidden')
  page.locator('#reviewpage').select_option(label='Página 1')
  page.get_by_role('button',name='Editar continuidade / importar versão').click()
  page.locator('[name=image]').set_input_files({'name':'revisada.png','mimeType':'image/png','buffer':png})
  page.get_by_role('button',name='Salvar registro').click()
  page.locator('#modal').wait_for(state='hidden')
  page.locator('#reviewpage').select_option(label='Página 1')
  page.locator('#reason').fill('Conferência manual realizada')
  page.get_by_role('button',name='Aprovar revisão').click()
  page.wait_for_function("()=>document.querySelector('#notice').textContent.includes('Decisão registrada')")
  assert 'Aprovado' in page.locator('#version').inner_text()
  page.screenshot(path=str(Path(temp)/'studio.png'),full_page=True)
  page.get_by_text('Revisão manual / pacote para outro aplicativo',exact=True).click()
  with page.expect_download() as d:
   page.get_by_role('link',name='↓ Baixar pacote ZIP').click()
  assert d.value.suggested_filename=='revisao-proelium.zip'
  page.get_by_role('button',name='Histórico',exact=True).click()
  assert page.get_by_role('heading',name='Aprovado · Página 1').count()==1
  page.reload()
  page.get_by_role('button',name='Páginas',exact=True).click()
  assert page.get_by_role('heading',name='Página 1').count()==1
  assert not errors,errors
  with page.expect_download() as backup:
   page.get_by_role('link',name='↓ Backup completo').click()
  backup_path=Path(temp)/'backup.zip'
  backup.value.save_as(backup_path)
  with zipfile.ZipFile(backup_path) as z:
   assert z.testzip() is None
   manifest=json.loads(z.read('proelium-portable.json'))
   assert len(manifest['records'])==3
   for n in z.namelist():
    if n.startswith('files/'):
     assert z.read(n)==png
  awaitable="""async()=>{const d=await Portable.ready;await new Promise((ok,no)=>{const t=d.transaction(['records','events','files'],'readwrite');for(const n of ['records','events','files'])t.objectStore(n).clear();t.oncomplete=ok;t.onerror=no})}"""
  page.evaluate(awaitable)
  page.reload()
  page.get_by_role('button',name='Páginas',exact=True).click()
  assert page.get_by_role('heading',name='Página 1').count()==0
  page.locator('#backupfile').set_input_files(str(backup_path))
  page.wait_for_function("()=>document.querySelector('#notice').textContent.includes('Backup restaurado')")
  assert page.get_by_role('heading',name='Página 1').count()==1
  page.get_by_role('button',name='Abrir página').click()
  assert page.locator('#comparison img').first.evaluate('(img)=>img.complete && img.naturalWidth>0')
  assert not errors,errors
  assert not network,network
  print('PASS portátil (HTML estático): fluxo completo, persistência, ZIP íntegro, restauração e imagens originais; nenhuma requisição de rede')
  b.close()

