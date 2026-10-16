"""Prepara o motor Linux verificável em cache fora do checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile

URL='https://github.com/leejet/stable-diffusion.cpp/releases/download/master-969-8c442fb/sd-master-8c442fb-bin-Linux-Ubuntu-24.04-x86_64.zip'
SHA='d090d294a1e59ee744c52f2d003ab7fcdb13d40006e3c67665fc6969b9cfb333'
parser=argparse.ArgumentParser()
parser.add_argument('--root',type=Path,default=Path('/workspace/shared/proelium-engine'))
parser.add_argument('--archive',type=Path)
args=parser.parse_args()
root=args.root.resolve()
native=root/'8c442fb'/'native'
receipt=root/'8c442fb'/'sha256.json'
if native.exists():
    if not receipt.is_file():
        raise SystemExit('Cache existente sem recibo. Preserve os arquivos e escolha outro --root.')
    for name,sha in json.loads(receipt.read_text()).items():
        if hashlib.sha256((native/name).read_bytes()).hexdigest()!=sha:
            raise SystemExit('Cache modificado: '+name+'. Nenhum arquivo foi substituído.')
else:
    root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as temp:
        temp=Path(temp)
        archive=args.archive
        if not archive:
            archive=temp/'engine.zip'
            with urllib.request.urlopen(URL,timeout=60) as source,archive.open('wb') as target:
                shutil.copyfileobj(source,target)
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA:
            raise SystemExit('Checksum oficial inválido. O motor não será usado.')
        extracted=temp/'native'
        extracted.mkdir()
        hashes={}
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                if name.endswith('/'):
                    continue
                if Path(name).name!=name:
                    raise SystemExit('Caminho inesperado no pacote oficial')
                content=z.read(name)
                (extracted/name).write_bytes(content)
                hashes[name]=hashlib.sha256(content).hexdigest()
                if name in ['sd-cli','sd-server']:
                    (extracted/name).chmod(0o755)
        native.parent.mkdir(parents=True,exist_ok=True)
        extracted.rename(native)
        receipt.write_text(json.dumps(hashes,indent=2))
print('Motor Linux preparado:',native/'sd-cli')
