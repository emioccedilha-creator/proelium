import {createHash} from 'node:crypto';
import {createReadStream,createWriteStream} from 'node:fs';
import {mkdir,readFile,writeFile,rename,stat,statfs,unlink} from 'node:fs/promises';
import {join} from 'node:path';
import {once} from 'node:events';

export const SPECS=[
 {id:'diffusion',repo:'leejet/FLUX.2-klein-4B-GGUF',patterns:[/Q4_K_S\.gguf$/i,/Q4_K_M\.gguf$/i,/Q4_0\.gguf$/i]},
 {id:'text',repo:'unsloth/Qwen3-4B-GGUF',patterns:[/^Qwen3-4B-Q4_K_M\.gguf$/i,/Qwen3-4B-Q4_K_M\.gguf$/i]},
 {id:'vae',repo:'Comfy-Org/flux2-dev',patterns:[/^split_files\/vae\/flux2-vae\.safetensors$/]},
];
export async function sha256(path){const h=createHash('sha256');for await(const b of createReadStream(path))h.update(b);return h.digest('hex')}
export function selectModel(spec,metadata){
 if(!/^[a-f0-9]{40}$/i.test(metadata.sha||''))throw Error('A fonte não forneceu uma revisão fixa para '+spec.repo);
 if(metadata.gated||metadata.private)throw Error('O arquivo exige conta ou autorização. Nenhuma credencial foi criada ou solicitada.');
 let candidates=[];
 for(const pattern of spec.patterns){candidates=(metadata.siblings||[]).filter(f=>pattern.test(f.rfilename));if(candidates.length)break}
 if(candidates.length!==1)throw Error('Não foi possível identificar um único arquivo compatível em '+spec.repo);
 const f=candidates[0],hash=f.lfs?.sha256||f.lfs?.oid;
 if(!/^[a-f0-9]{64}$/i.test(hash||'')||!Number.isSafeInteger(f.lfs?.size||f.size))throw Error('A fonte não forneceu SHA-256 e tamanho verificáveis para '+f.rfilename);
 return {id:spec.id,repo:spec.repo,revision:metadata.sha,filename:f.rfilename,sha256:hash.toLowerCase(),size:f.lfs?.size||f.size,url:`https://huggingface.co/${spec.repo}/resolve/${metadata.sha}/${f.rfilename.split('/').map(encodeURIComponent).join('/')}`,local:spec.id+(f.rfilename.endsWith('.gguf')?'.gguf':'.safetensors')};
}
export async function resolveModels(fetcher=fetch){
 const models=[];
 for(const spec of SPECS){const r=await fetcher('https://huggingface.co/api/models/'+spec.repo+'?blobs=true',{signal:AbortSignal.timeout(30000)});if(!r.ok)throw Error(`A fonte de modelos recusou o acesso (${r.status}): ${spec.repo}. Verifique a conexão com huggingface.co.`);models.push(selectModel(spec,await r.json()))}
 return models;
}
export async function downloadVerified(model,path,progress=()=>{},fetcher=fetch){
 try{if((await stat(path)).size===model.size&&await sha256(path)===model.sha256){progress(model.size,model.size);return path}}catch(e){if(e.code&&e.code!=='ENOENT')throw e}
 const part=path+'.part';let offset=0;
 try{offset=(await stat(part)).size;if(offset>model.size){await unlink(part);offset=0}}catch{}
 if(offset===model.size){if(await sha256(part)===model.sha256){await rename(part,path);return path}await unlink(part);offset=0}
 const r=await fetcher(model.url,{headers:offset?{Range:`bytes=${offset}-`}:{},signal:AbortSignal.timeout(6*60*60*1000)});
 if(!r.ok)throw Error(`Falha no download de ${model.id} (HTTP ${r.status}). Clique em Retomar preparação para tentar novamente.`);
 if(offset&&r.status!==206)offset=0;
 if(r.status===206&&!r.headers.get('content-range')?.startsWith(`bytes ${offset}-`))throw Error('A fonte retornou um intervalo de download incorreto');
 const h=createHash('sha256');if(offset)for await(const b of createReadStream(part))h.update(b);
 const out=createWriteStream(part,{flags:offset?'a':'w'});let received=offset;
 // Rejeições de stream são observadas mesmo se ocorrerem durante um fetch.
 let streamError;out.on('error',e=>{streamError=e});
 try{for await(const chunk of r.body){if(streamError)throw streamError;received+=chunk.length;if(received>model.size)throw Error('Download maior que o tamanho publicado');h.update(chunk);if(!out.write(chunk))await once(out,'drain');progress(received,model.size)}out.end();await once(out,'finish');if(streamError)throw streamError;
 }catch(e){out.destroy();throw e}
 if(received!==model.size)throw Error('Download interrompido. O progresso foi preservado para retomar.');
 if(h.digest('hex')!==model.sha256){await unlink(part);throw Error('A verificação SHA-256 falhou. O arquivo foi descartado e não será executado.')}
 await rename(part,path);return path;
}
export async function prepareModels(dir,progress=()=>{},fetcher=fetch){
 await mkdir(dir,{recursive:true});let models;
 try{models=JSON.parse(await readFile(join(dir,'model-lock.json'),'utf8'));if(!Array.isArray(models)||models.length!==SPECS.length||models.some((m,i)=>m.id!==SPECS[i].id||m.repo!==SPECS[i].repo||!new RegExp('^[a-f0-9]{40}$','i').test(m.revision)||!new RegExp('^[a-f0-9]{64}$','i').test(m.sha256)||(!Number.isSafeInteger(m.size)||m.size<=0)||m.local!==m.id+(m.id==='vae'?'.safetensors':'.gguf')||m.url!==`https://huggingface.co/${m.repo}/resolve/${m.revision}/${m.filename.split('/').map(encodeURIComponent).join('/')}`))throw Error('model-lock.json inválido; preserve o arquivo e verifique sua origem.');
 }catch(e){if(e.code!=='ENOENT')throw e;models=JSON.parse(await readFile(new URL('./model-catalog.json',import.meta.url),'utf8'));await writeFile(join(dir,'model-lock.json.tmp'),JSON.stringify(models,null,2));await rename(join(dir,'model-lock.json.tmp'),join(dir,'model-lock.json'))}
 const total=models.reduce((n,m)=>n+m.size,0),counts=new Map(models.map(m=>[m.id,0]));
 const disk=await statfs(dir);let remaining=total;
 for(const m of models){for(const suffix of ['', '.part']){try{remaining-=Math.min((await stat(join(dir,m.local+suffix))).size,m.size)}catch{}}}
 if(disk.bavail*disk.bsize<Math.max(0,remaining)+1024**3)throw Error('Espaço insuficiente. Libere pelo menos '+Math.ceil((Math.max(0,remaining)+1024**3)/1024**3)+' GB para os modelos.');
 const results=await Promise.allSettled(models.map(async m=>{
  const report=n=>{counts.set(m.id,n);progress({phase:'downloading',file:m.id,received:[...counts.values()].reduce((a,b)=>a+b,0),total,message:'Baixando ou verificando os três modelos (arquivos originais não são enviados)'})};
  report(0);await downloadVerified(m,join(dir,m.local),report,fetcher);
 }));
 const failed=results.find(r=>r.status==='rejected');if(failed)throw failed.reason;
 return Object.fromEntries(models.map(m=>[m.id,join(dir,m.local)]));
}
