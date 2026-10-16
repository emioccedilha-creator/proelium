"""Cria uma amostra sintética e valida uma edição real. Não usa imagens do usuário."""
from pathlib import Path
import argparse
import json
import os
import subprocess
from PIL import Image, ImageDraw

parser=argparse.ArgumentParser()
parser.add_argument('--cache',type=Path,required=True)
args=parser.parse_args()
samples=args.cache/'samples'
samples.mkdir(parents=True,exist_ok=True)
for name,color in [('page',(205,25,35)),('reference',(20,70,205))]:
    image=Image.new('RGB',(256,256),'white')
    d=ImageDraw.Draw(image)
    d.rectangle((8,8,247,247),outline='black',width=3)
    d.polygon([(38,246),(56,195),(92,178),(164,178),(201,195),(220,246)],fill=(245,245,245),outline='black',width=3)
    d.ellipse((75,45,180,176),fill=(253,251,246),outline='black',width=3)
    d.polygon([(72,89),(76,48),(111,27),(164,42),(183,82),(155,66),(142,87),(128,58),(101,85),(99,70)],fill='black')
    d.line((91,105,111,103),fill='black',width=3)
    d.line((145,103,166,105),fill='black',width=3)
    d.ellipse((100,107,105,113),fill='black')
    d.ellipse((151,107,156,113),fill='black')
    d.line((127,112,123,128,132,128),fill='black',width=2)
    d.arc((111,129,148,150),5,165,fill='black',width=2)
    d.polygon([(87,166),(167,166),(175,190),(147,203),(128,185),(101,202),(80,189)],fill=color,outline='black',width=3)
    d.polygon([(144,187),(163,196),(155,240),(133,231)],fill=color,outline='black',width=2)
    image.save(samples/(name+'.png'))
script=r'''
import {createEngine} from './desktop/engine.mjs';
import {readFile,writeFile} from 'node:fs/promises';
const root=process.env.PROELIUM_VALIDATION_CACHE;
const engine=createEngine({root:root+'/real-run',executable:root+'/native/sd-cli'});
await engine.setup();
const page=(await readFile(root+'/samples/page.png')).toString('base64');
const reference=(await readFile(root+'/samples/reference.png')).toString('base64');
const request={page,references:[reference],prompt:'Edit image 1. Change only the red scarf to blue, matching the blue scarf in image 2. Preserve the same face, black hair, eyes, manga line art, white background and rectangular panel border. Return image 1 with a blue scarf. No text.',width:256,height:256};
const {id}=await engine.start(request);
console.log('Edição real '+id);
let lastLog='';for(;;){const job=await engine.job(id);if(job.status!=='running'){await writeFile(root+'/samples/validation.json',JSON.stringify(job,null,2));if(job.status!=='completed')throw Error(job.message+'\n'+job.log);await writeFile(root+'/samples/result.png',await engine.result(id));console.log(JSON.stringify({...job,log:job.log.slice(-4000)}));break}const tail=job.log.slice(-400)||job.message;if(tail!==lastLog){console.log(tail);lastLog=tail}await new Promise(ok=>setTimeout(ok,10000))}
'''
result=subprocess.run(['node','--use-env-proxy','--input-type=module','-'],input=script,text=True,cwd=Path(__file__).resolve().parents[1],env={**os.environ,'PROELIUM_VALIDATION_CACHE':str(args.cache.resolve())})
raise SystemExit(result.returncode)
