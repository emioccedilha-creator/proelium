"""Empacota runtime e motor oficiais já baixados e verificados, sem instalar Python no destino."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
 'engine-win.zip':'65c6da06be455cc35614514816a785dc3a253506d563cb4dc9748f2f285d4eda',
 'node-win.zip':'57f71ab3652e797d84acddc79c81cc9ff1c6ddb2a1974cdb83f00fee9bff4c73',
}
parser=argparse.ArgumentParser()
parser.add_argument('--archives',type=Path,required=True)
args=parser.parse_args()
for name,sha in EXPECTED.items():
    p=args.archives/name
    if hashlib.sha256(p.read_bytes()).hexdigest()!=sha:
        raise SystemExit('Checksum oficial divergente: '+name)
output=ROOT/'dist/Proelium Studio Windows IA.zip'
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as target:
    prefix='Proelium Studio/'
    def add(path,content):
        target.writestr(prefix+path,content)
    add('Proelium Studio.html',(ROOT/'dist/Proelium Studio.html').read_bytes())
    for name in ['models.mjs','engine.mjs','server.mjs','model-catalog.json']:
        add('desktop/'+name,(ROOT/'desktop'/name).read_bytes())
    manifest={}
    with zipfile.ZipFile(args.archives/'engine-win.zip') as engine:
        for name in engine.namelist():
            if name.endswith('/'):
                continue
            if Path(name).name!=name:
                raise SystemExit('Caminho inesperado no pacote do motor: '+name)
            b=engine.read(name)
            add('native/'+name,b)
            manifest[name]=hashlib.sha256(b).hexdigest()
    add('desktop/native-sha256.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(args.archives/'node-win.zip') as node:
        for name in ['node.exe','LICENSE']:
            add('runtime/'+name,node.read('node-v24.19.0-win-x64/'+name))
    add('ABRIR PROELIUM.cmd',('@echo off\r\nchcp 65001 >nul\r\ncd /d "%~dp0"\r\n"%~dp0runtime\\node.exe" --use-env-proxy "%~dp0desktop\\server.mjs"\r\nif errorlevel 1 pause\r\n').encode('utf-8'))
    add('LEIA PRIMEIRO.txt',('PROELIUM STUDIO PARA WINDOWS x64\r\n\r\n1. Extraia a pasta inteira. Não execute dentro do ZIP.\r\n2. Dê dois cliques em ABRIR PROELIUM.cmd. O navegador será aberto automaticamente.\r\n3. Acompanhe a preparação dos modelos em Gerador de imagens. O primeiro uso exige internet e vários GB de download. Mantenha a janela aberta.\r\n4. Cadastre personagens, vincule-os à página e clique em Corrigir página agora. Compare a revisão antes de aprovar.\r\n\r\nNão requer instalação de Python, Node, ComfyUI, conta ou chave de API. O runtime e o motor de CPU estão nesta pasta. Os modelos públicos são baixados automaticamente e verificados. Mínimo: 12 GB de RAM; recomendados 16 GB ou mais. Reserve pelo menos 15 GB de disco e bastante tempo para edição em CPU. Windows ARM não é suportado por este pacote.\r\n\r\nSe usava o HTML antigo, abra-o no mesmo navegador e exporte Backup completo. No aplicativo novo, use Restaurar backup portátil. Não limpe os dados antigos antes de conferir a importação.\r\n\r\nA biblioteca fica no navegador, no endereço local estável http://127.0.0.1:8767. Use sempre o mesmo perfil e exporte backups. Modelos e cópias dos trabalhos ficam em engine-data nesta pasta; não são incluídos no backup da biblioteca.\r\n\r\nESTADO DA VALIDAÇÃO: runtime e motor oficiais têm SHA-256 verificado; o motor CPU foi iniciado em Linux. Uma edição real de imagem sintética de 256 px com uma referência foi concluída em CPU/Linux em aproximadamente quatro minutos; os arquivos de prova estão em VALIDACAO. O iniciador Windows não foi executado neste ambiente Linux. Não há garantia de fidelidade perfeita ou velocidade em qualquer computador.\r\n').encode('utf-8'))
    for name in ['native-validation.json','native-page.png','native-reference.png','native-result.png']:
        add('VALIDACAO/'+name,(ROOT/'docs'/name).read_bytes())
    add('FONTES E VERSOES.txt',json.dumps({
        'engine':{'release':'master-969-8c442fb','url':'https://github.com/leejet/stable-diffusion.cpp','archive_sha256':EXPECTED['engine-win.zip']},
        'runtime':{'version':'24.19.0','url':'https://nodejs.org/dist/v24.19.0/SHASUMS256.txt','archive_sha256':EXPECTED['node-win.zip']},
        'models':['https://huggingface.co/leejet/FLUX.2-klein-4B-GGUF','https://huggingface.co/unsloth/Qwen3-4B-GGUF','https://huggingface.co/Comfy-Org/flux2-dev'],
        'model_checksums':'Os arquivos são fixados por revisão e SHA-256 em engine-data/models/model-lock.json antes do download; TLS e checksums são obrigatórios.'
    },ensure_ascii=False,indent=2))
print(output,output.stat().st_size,'bytes')
