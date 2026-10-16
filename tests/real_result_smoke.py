"""Recupera na UI o resultado real documentado; exige servidor e cache reais ativos."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
report=json.loads((ROOT/'docs/native-validation.json').read_text())
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'),headless=True,args=['--no-sandbox'])
 page=b.new_page()
 errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(os.environ.get('PROELIUM_TEST_URL','http://127.0.0.1:8767'))
 page.wait_for_function("async()=> (await fetch('/engine/status').then(r=>r.json())).phase==='ready'")
 page.get_by_role('button',name='Cadastrar primeiro personagem').click()
 page.locator('[name=name]').fill('Cânone da edição real')
 page.locator('[name=details]').fill('Lenço azul, cabelo preto, mesmo rosto')
 page.locator('[name=status]').select_option('Aprovado')
 page.locator('[name=image]').set_input_files(str(ROOT/'docs/native-reference.png'))
 page.locator('#save-record').click()
 expect(page.locator('#modal')).not_to_be_visible()
 page.get_by_role('button',name='Páginas',exact=True).click()
 page.get_by_role('button',name='+ Importar página').click()
 page.locator('[name=name]').fill('Página da edição real')
 page.locator('[name=refs]').select_option(label='Cânone da edição real · Aprovado')
 page.locator('[name=image]').set_input_files(str(ROOT/'docs/native-page.png'))
 page.locator('#save-record').click()
 expect(page.locator('#modal')).not_to_be_visible()
 data=page.evaluate("()=>Portable.api('state')")
 manga=next(r for r in data['records'] if r['kind']=='page')
 page.evaluate("p=>localStorage.setItem('proelium-engine-pending-'+p.page,JSON.stringify({id:p.job,metadata:{referenceCount:1,instructions:'Trocar o lenço vermelho pelo azul da referência',width:256,height:256}}))",{'page':manga['id'],'job':report['job']})
 page.get_by_role('button',name='Abrir página').click()
 page.get_by_role('button',name='Recuperar edição anterior').click()
 expect(page.locator('#notice')).to_contain_text('modelo retornou uma imagem',timeout=15000)
 expect(page.locator('#version option')).to_have_count(2)
 data=page.evaluate("()=>Portable.api('state')")
 manga=next(r for r in data['records'] if r['kind']=='page')
 assert manga['versions'][0]['sha256']==report['images']['page']['sha256']
 assert manga['versions'][1]['sha256']==report['images']['result']['sha256']
 assert manga['versions'][1]['decision']=='Pendente'
 canon=next(r for r in data['records'] if r['kind']=='reference')
 assert canon['status']=='Aprovado' and canon['versions'][0]['sha256']==report['images']['reference']['sha256']
 page.reload()
 page.get_by_role('button',name='Páginas',exact=True).click()
 page.get_by_role('button',name='Abrir página').click()
 expect(page.locator('#version option')).to_have_count(2)
 assert not errors,errors
 b.close()
 print('PASS: resultado real recuperado do motor nativo e salvo na biblioteca; hashes do original, referência e revisão conferidos; cânone protegido e persistência após recarregar.')
