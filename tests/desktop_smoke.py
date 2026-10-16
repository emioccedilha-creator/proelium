"""Testa a UI do pacote Windows com executor simulado; não avalia IA real."""
import base64
import os
from pathlib import Path
import subprocess
import tempfile
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aP1sAAAAASUVORK5CYII=')
with tempfile.TemporaryDirectory() as temp:
 process=subprocess.Popen(['node',str(ROOT/'tests/desktop_fixture.mjs')],stdout=subprocess.PIPE,text=True,env={**os.environ,'PROELIUM_TEST_DATA':temp})
 try:
  line=process.stdout.readline().strip()
  assert line.startswith('PORT='),line
  url='http://127.0.0.1:'+line.split('=')[1]
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'),headless=True,args=['--no-sandbox'])
   page=browser.new_page()
   errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(url)
   page.wait_for_function("async()=> (await fetch('/engine/status').then(r=>r.json())).phase==='ready'")
   page.get_by_role('button',name='Cadastrar primeiro personagem').click()
   page.locator('[name=name]').fill('Memória integrada')
   page.locator('[name=details]').fill('Manter rosto, cicatriz e capa azul')
   page.locator('[name=status]').select_option('Aprovado')
   page.locator('[name=image]').set_input_files([{'name':f'angulo-{i}.png','mimeType':'image/png','buffer':PNG} for i in range(10)])
   page.locator('#save-record').click()
   expect(page.locator('#modal')).not_to_be_visible()
   expect(page.locator('h1')).to_have_text('Personagens')
   page.get_by_role('button',name='Páginas',exact=True).click()
   page.get_by_role('button',name='+ Importar página').click()
   page.locator('[name=name]').fill('Edição integrada')
   page.locator('[name=refs]').select_option(label='Memória integrada · Aprovado')
   page.locator('[name=image]').set_input_files({'name':'original.png','mimeType':'image/png','buffer':PNG})
   page.locator('#save-record').click()
   expect(page.locator('#modal')).not_to_be_visible()
   page.get_by_role('button',name='Abrir página').click()
   page.locator('#f-edit-instructions').fill('Corrigir a capa sem alterar os balões')
   page.locator('#generate-page').click()
   expect(page.locator('#notice')).to_contain_text('modelo retornou uma imagem',timeout=15000)
   expect(page.locator('#version option')).to_have_count(2)
   data=page.evaluate("()=>Portable.api('state')")
   manga=next(r for r in data['records'] if r['kind']=='page')
   assert manga['versions'][0]['decision']=='Original'
   assert manga['versions'][1]['decision']=='Pendente'
   assert manga['generation']['referenceCount']==10
   assert manga['generation']['provider']=='Motor Proelium CPU'
   assert len(manga['engineJobIds'])==1
   char=next(r for r in data['records'] if r['kind']=='reference')
   assert char['status']=='Aprovado' and len(char['versions'])==10
   page.get_by_role('button',name='Gerador de imagens',exact=True).click()
   expect(page.get_by_role('heading',name='Motor de edição incluído')).to_be_visible()
   page.reload()
   page.get_by_role('button',name='Páginas',exact=True).click()
   expect(page.get_by_role('heading',name='Edição integrada')).to_be_visible()
   assert not errors,errors
   browser.close()
   print('PASS desktop: preparação automática, cadastro com 10 imagens, edição local integrada com executor simulado, revisão pendente, originais/cânone preservados e persistência.')
 finally:
  process.terminate()
  process.wait(timeout=10)
