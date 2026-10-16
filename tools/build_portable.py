"""Empacota o aplicativo sem dependências; a saída não precisa de Python."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
html = (root/'static/index.html').read_text()
css = (root/'static/style.css').read_text()
js = (root/'static/app.js').read_text()
start = js.index('async function api(')
end = js.index('\nfunction notice', start)
js = js[:start] + 'async function api(path,data){return Portable.api(path,data)}' + js[end:]
js = js.replace('/files/${v.file}', '${Portable.imageURL(v.file)}')
js = js.replace('/files/${r.versions[0].file}', '${Portable.imageURL(r.versions[0].file)}').replace('/files/${x.file}', '${Portable.imageURL(x.file)}')
html = html.replace('<link rel="stylesheet" href="/style.css">','<style>'+css+'</style>')
html = html.replace('<script src="/native.js"></script>', '<script>'+(root/'static/native.js').read_text()+'</script>')
html = html.replace('<script src="/generator.js"></script>', '<script>'+(root/'static/generator.js').read_text()+'</script>')
html = html.replace('<script src="/app.js"></script>','<script>'+(root/'portable/storage.js').read_text()+'\n'+js+'</script>')
html = html.replace('</header>', '</header><div class="panel"><b>Proelium Studio 2.0 · até 10 imagens por personagem</b><p>Seus dados ficam neste navegador, neste computador. Use sempre este arquivo no mesmo local e o mesmo perfil do navegador. Não use janela anônima. Exporte backups para proteger seu trabalho ao trocar de navegador, mover o arquivo ou limpar dados.</p><button class="secondary" id="restore">Restaurar backup portátil</button><input type="file" id="backupfile" accept=".zip" hidden></div>')
html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; img-src blob: data:; connect-src blob: http://127.0.0.1:* http://localhost:* https:; base-uri \'none\'; form-action \'none\'">')
(root/'dist').mkdir(exist_ok=True)
(root/'dist/Proelium Studio.html').write_text(html,encoding='utf-8')
print('Criado: dist/Proelium Studio.html')

import zipfile
with zipfile.ZipFile(root/'dist/Proelium Studio Portatil.zip','w',zipfile.ZIP_DEFLATED) as archive:
    archive.write(root/'dist/Proelium Studio.html','Proelium Studio.html')
    archive.writestr('COMECE AQUI.txt','Abra Proelium Studio.html no Edge ou Chrome. Use o mesmo arquivo, perfil e navegador. Exporte backups regularmente. Esta versão permite dez imagens por personagem. A correção automática exige conectar um gerador real na área Gerador de imagens; nenhum modelo é incluído no HTML.')
