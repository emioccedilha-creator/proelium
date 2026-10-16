"""Regressões de salvamento, dez referências e conectores com serviço simulado."""
import base64
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aP1sAAAAASUVORK5CYII=')
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT/'dist')))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/Proelium%20Studio.html'
try:
 with tempfile.TemporaryDirectory() as temp, sync_playwright() as p:
  b=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'),headless=True,args=['--no-sandbox'])
  page=b.new_page()
  errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.add_init_script("Object.defineProperty(crypto,'randomUUID',{value:undefined});Object.defineProperty(crypto,'subtle',{value:undefined});Object.defineProperty(window,'structuredClone',{value:undefined});")
  page.goto(url)
  page.get_by_role('button',name='Cadastrar primeiro personagem').click()
  page.locator('[name=name]').fill('Ariadne canônica')
  images=[{'name':f'angulo-{i}.png','mimeType':'image/png','buffer':PNG} for i in range(10)]
  page.locator('[name=image]').set_input_files(images)
  expect(page.locator('#image-count')).to_contain_text('10/10')
  page.locator('#save-record').click()
  expect(page.locator('#modal')).not_to_be_visible()
  expect(page.locator('h1')).to_have_text('Personagens')
  expect(page.get_by_role('heading',name='Ariadne canônica')).to_be_visible()
  page.get_by_role('button',name='Editar registro').click()
  expect(page.locator('.thumbs img')).to_have_count(10)
  page.locator('[name=image]').set_input_files(images[:1])
  page.locator('#save-record').click()
  expect(page.locator('#form-error')).to_contain_text('máximo 10')
  assert page.evaluate("async()=> (await Portable.api('state')).records[0].versions.length")==10
  page.locator('[name=image]').set_input_files([])
  page.locator('[name=status]').select_option('Aprovado')
  page.locator('#save-record').click()
  expect(page.locator('#modal')).not_to_be_visible()
  # Rejeição de quota visível, campos intactos, sem criação parcial.
  page.get_by_role('button',name='+ Novo registro').click()
  page.locator('[name=name]').fill('Não perder este formulário')
  page.evaluate("()=>{window.originalPut=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(){throw new DOMException('Quota','QuotaExceededError')}}")
  page.locator('#save-record').click()
  expect(page.locator('#form-error')).to_contain_text('Sem espaço')
  expect(page.locator('[name=name]')).to_have_value('Não perder este formulário')
  page.evaluate('()=>{IDBObjectStore.prototype.put=window.originalPut}')
  page.get_by_role('button',name='Cancelar').click()
  page.get_by_role('button',name='Páginas',exact=True).click()
  page.get_by_role('button',name='+ Importar página').click()
  page.locator('[name=name]').fill('Página conectada')
  page.locator('[name=refs]').select_option(label='Ariadne canônica · Aprovado')
  page.locator('[name=image]').set_input_files(images[0])
  page.locator('#save-record').click()
  expect(page.locator('#modal')).not_to_be_visible()
  page.get_by_role('button',name='Abrir página').click()
  page.locator('#f-edit-instructions').fill('Corrigir o rosto conforme os dez ângulos cadastrados')
  page.locator('#generate-page').click()
  expect(page.locator('#generation-state')).to_contain_text('Nenhum gerador')
  page.locator('#configure-generator').click()
  workflow={'1':{'class_type':'LoadImage','inputs':{'image':''},'_meta':{'title':'PROELIUM_PAGE'}},'20':{'class_type':'CLIPTextEncode','inputs':{'text':''},'_meta':{'title':'PROELIUM_PROMPT'}},'21':{'class_type':'TestEditor','inputs':{'page':['1',0],'prompt':['20',0]}},'22':{'class_type':'SaveImage','inputs':{'images':['21',0]},'_meta':{'title':'PROELIUM_OUTPUT'}}}
  for i in range(10):
   node=str(i+2)
   workflow[node]={'class_type':'LoadImage','inputs':{'image':''},'_meta':{'title':f'PROELIUM_REF_{i+1:02}'}}
   workflow['21']['inputs'][f'ref{i}']=[node,0]
  page.locator('#workflow').set_input_files({'name':'workflow-api.json','mimeType':'application/json','buffer':json.dumps(workflow).encode()})
  expect(page.locator('#workflow-name')).to_contain_text('Workflow lido')
  page.locator('#save-generator').click()
  calls={'uploads':0,'prompts':0}
  def comfy(route):
   path=route.request.url.split(':8188')[1]
   headers={'Access-Control-Allow-Origin':'*'}
   if path=='/system_stats':
    route.fulfill(json={'system':{'os':'test'}},headers=headers)
   elif path=='/upload/image':
    calls['uploads']+=1
    route.fulfill(json={'name':f'input-{calls["uploads"]}.png','subfolder':''},headers=headers)
   elif path=='/prompt':
    body=route.request.post_data_json
    assert len(body['prompt'])==14
    assert 'Ariadne canônica' in body['prompt']['20']['inputs']['text']
    assert all(body['prompt'][str(i+2)]['inputs']['image'] for i in range(10))
    calls['prompts']+=1
    route.fulfill(json={'prompt_id':'test-job','node_errors':{}},headers=headers)
   elif path=='/history/test-job':
    route.fulfill(json={'test-job':{'status':{'completed':True},'outputs':{'22':{'images':[{'filename':'output.png','subfolder':'','type':'output'}]}}}},headers=headers)
   elif path.startswith('/view?'):
    route.fulfill(body=PNG,content_type='image/png',headers=headers)
   else:
    raise AssertionError(path)
  page.route('http://127.0.0.1:8188/**',comfy)
  page.locator('#test-generator').click()
  expect(page.locator('#connection-state')).to_contain_text('Serviço respondeu')
  page.get_by_role('button',name='Revisão',exact=True).click()
  page.locator('#reviewpage').select_option(label='Página conectada')
  page.locator('#f-edit-instructions').fill('Corrigir o rosto')
  page.on('dialog',lambda d:d.accept())
  page.locator('#generate-page').click()
  expect(page.locator('#notice')).to_contain_text('Correção recebida',timeout=15000)
  expect(page.locator('#version option')).to_have_count(2)
  assert calls=={'uploads':11,'prompts':1},calls
  data=page.evaluate("()=>Portable.api('state')")
  char=next(r for r in data['records'] if r['kind']=='reference')
  assert char['status']=='Aprovado' and len(char['versions'])==10
  manga=next(r for r in data['records'] if r['kind']=='page')
  assert manga['versions'][0]['decision']=='Original'
  assert manga['versions'][1]['decision']=='Pendente'
  assert manga['generation']['referenceCount']==10
  # Conector HTTP de edição: API simulada, sem credenciais reais ou cobrança.
  page.get_by_role('button',name='Gerador de imagens',exact=True).click()
  page.locator('#f-provider').select_option('API de edição compatível')
  page.locator('#f-endpoint').fill('https://editor.example.test/v1')
  page.locator('#f-api-key').fill('test-session-key')
  page.locator('#save-generator').click()
  api_calls=[]
  def editor(route):
   if route.request.method=='OPTIONS':
    route.fulfill(status=204,headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'Authorization,Content-Type','Access-Control-Allow-Methods':'GET,POST,OPTIONS'})
   elif route.request.url.endswith('/models'):
    route.fulfill(json={'data':[{'id':'gpt-image-1'}]})
   else:
    assert route.request.url.endswith('/images/edits')
    assert route.request.headers.get('authorization')=='Bearer test-session-key'
    raw=route.request.post_data_buffer
    assert raw.count(b'name="image[]"')==11
    api_calls.append(1)
    route.fulfill(json={'data':[{'b64_json':base64.b64encode(PNG).decode()}]})
  page.route('https://editor.example.test/**',editor)
  page.get_by_role('button',name='Revisão',exact=True).click()
  page.locator('#reviewpage').select_option(label='Página conectada')
  page.locator('#f-edit-instructions').fill('Ajustar detalhes da roupa')
  page.locator('#generate-page').click()
  expect(page.locator('#notice')).to_contain_text('Correção recebida',timeout=15000)
  expect(page.locator('#version option')).to_have_count(3)
  assert api_calls==[1]
  assert 'test-session-key' not in page.evaluate("()=>JSON.stringify(localStorage)")
  assert 'test-session-key' not in json.dumps(page.evaluate("()=>Portable.api('state')"))
  page.reload()
  page.get_by_role('button',name='Personagens',exact=True).click()
  page.get_by_role('button',name='Consultar cânone').click()
  expect(page.locator('.thumbs img')).to_have_count(10)
  assert not errors,errors
  print('PASS: salvamento sem randomUUID/subtle/structuredClone; dez imagens; limite/atomicidade; erro de quota visível; conexão ausente; conectores ComfyUI e API com 11 imagens e retornos simulados; originais e cânone preservados.')
  b.close()
finally:
 server.shutdown()
 server.server_close()
