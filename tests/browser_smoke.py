"""Teste opcional de navegador: pip install playwright; playwright install chromium."""
import base64
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright
png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aP1sAAAAASUVORK5CYII=')
with tempfile.TemporaryDirectory() as temp:
 with socket.socket() as sock:
  sock.bind(('127.0.0.1',0))
  port=sock.getsockname()[1]
 url=f'http://127.0.0.1:{port}'
 process=subprocess.Popen([sys.executable,str(Path(__file__).resolve().parents[1]/'app.py'),'--port',str(port)],env={**os.environ,'PROELIUM_DATA':str(Path(temp)/'data')},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  for attempt in range(100):
   try:
    urllib.request.urlopen(url+'/api/state',timeout=1).close()
    break
   except OSError:
    time.sleep(.05)
  else:
   raise RuntimeError('Servidor não iniciou')
  with sync_playwright() as p:
   b=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'),headless=True,args=['--no-sandbox'])
   page=b.new_page(viewport={'width':1440,'height':1000})
   errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
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
   page.wait_for_function("document.querySelector('#notice').textContent.includes('Decisão registrada')")
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
   print('PASS: cadastro, proteção canônica, upload original e revisão, continuidade, prompt, defeito, aprovação, pacote, histórico e persistência após recarregar; sem erros JS')
   b.close()
 finally:
  process.terminate()
  process.wait(timeout=10)
