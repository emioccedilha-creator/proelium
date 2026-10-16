import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile,stat,access,rm} from 'node:fs/promises';
import {join} from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {selectModel,downloadVerified,SPECS} from '../desktop/models.mjs';
import {createEngine,buildArgs,imageBytes,nativeRun} from '../desktop/engine.mjs';
import {createServer} from '../desktop/server.mjs';
const PNG=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aP1sAAAAASUVORK5CYII=','base64');
const hash=b=>createHash('sha256').update(b).digest('hex');
async function temp(fn){const dir=await mkdtemp(join(os.tmpdir(),'proelium-engine-test-'));try{await fn(dir)}finally{await rm(dir,{recursive:true,force:true})}}

test('modelo exige revisão fixa, checksum e arquivo correto',()=>{
 const m=selectModel(SPECS[0],{sha:'a'.repeat(40),siblings:[{rfilename:'flux-2-klein-4b-Q4_K_S.gguf',lfs:{sha256:'b'.repeat(64),size:100}}]});
 assert.equal(m.local,'diffusion.gguf');assert.ok(m.url.includes('a'.repeat(40)));
 assert.throws(()=>selectModel(SPECS[0],{sha:'main',siblings:[]}));
 assert.throws(()=>selectModel(SPECS[0],{sha:'a'.repeat(40),gated:true}));
 assert.throws(()=>selectModel(SPECS[0],{sha:'a'.repeat(40),siblings:[{rfilename:'flux-Q4_K_S.gguf'}]}));
});

test('download retoma arquivo parcial e não aceita checksum incorreto',()=>temp(async dir=>{
 const bytes=Buffer.from('modelo de teste'),m={id:'test',url:'https://example.test/file',size:bytes.length,sha256:hash(bytes)},path=join(dir,'model.gguf');
 await writeFile(path+'.part',bytes.subarray(0,5));
 await downloadVerified(m,path,()=>{},async(url,options)=>{assert.equal(options.headers.Range,'bytes=5-');return new Response(bytes.subarray(5),{status:206,headers:{'content-range':`bytes 5-${bytes.length-1}/${bytes.length}`}})});
 assert.deepEqual(await readFile(path),bytes);
 let fetched=false;await downloadVerified(m,path,()=>{},async()=>{fetched=true});assert.equal(fetched,false);
 const bad=join(dir,'bad.gguf');await assert.rejects(downloadVerified({...m,sha256:'0'.repeat(64)},bad,()=>{},async()=>new Response(bytes)),/SHA-256/);
 await assert.rejects(access(bad));await assert.rejects(access(bad+'.part'));
}));

test('um trabalho usa todas as referências, não aprova a imagem nem promete qualidade',()=>temp(async dir=>{
 let seen;const engine=createEngine({root:dir,executable:'/fake/sd-cli',totalmem:()=>16*2**30,prepare:async()=>({diffusion:'d.gguf',text:'t.gguf',vae:'v.safetensors'}),run:async(exe,args,log)=>{if(args[0]==='--help')return;seen=args;log('executor simulado');await writeFile(args[args.indexOf('-o')+1],PNG)}});
 await engine.setup();assert.equal(engine.status().phase,'ready');assert.equal(engine.status().inferenceVerified,false);
 const j=await engine.start({page:PNG.toString('base64'),references:Array(10).fill(PNG.toString('base64')),prompt:'Preserve o rosto e corrija a roupa',width:512,height:512});
 for(let i=0;i<100&&(await engine.job(j.id)).status==='running';i++)await new Promise(ok=>setTimeout(ok,5));
 const result=await engine.job(j.id);assert.equal(result.status,'completed');assert.equal(result.referenceCount,10);assert.equal(seen.filter(x=>x==='-r').length,11);assert.equal(seen.includes('--prompt-file'),true);assert.deepEqual(await engine.result(j.id),PNG);assert.equal(engine.status().inferenceVerified,true);
 const record=JSON.parse(await readFile(join(dir,'jobs',j.id,'result.json'),'utf8'));assert.equal(record.status,'completed');
 const restarted=createEngine({root:dir,executable:'/fake/sd-cli'});assert.deepEqual(await restarted.result(j.id),PNG);
}));

test('falta de RAM e falha no download impedem status pronto',()=>temp(async dir=>{
 const low=createEngine({root:dir,executable:'/fake/sd-cli',totalmem:()=>8*2**30});await assert.rejects(low.setup(),/12 GB/);assert.equal(low.status().phase,'error');
 const denied=createEngine({root:dir,executable:'/fake/sd-cli',totalmem:()=>16*2**30,run:async()=>{},prepare:async()=>{throw Error('HTTP 403: acesso negado')}});await assert.rejects(denied.setup(),/403/);assert.equal(denied.status().phase,'error');await assert.rejects(denied.start({}),/preparação/);
}));

test('servidor local recusa outras origens, traversal e formulário externo',async()=>{
 const engine={status:()=>({phase:'missing'}),setup:async()=>{},start:async()=>({id:'x'})};const server=createServer(engine,'<html><script>example</script></html>');await new Promise(ok=>server.listen(0,'127.0.0.1',ok));const url='http://127.0.0.1:'+server.address().port;
 try{assert.equal((await fetch(url+'/engine/status')).status,200);assert.equal((await fetch(url+'/engine/setup',{method:'POST',headers:{Origin:'https://evil.example','Content-Type':'application/json'},body:'{}'})).status,403);assert.equal((await fetch(url+'/engine/setup',{method:'POST',body:'x'})).status,415);assert.match(await (await fetch(url)).text(),/PROELIUM_DESKTOP=true/);assert.equal((await fetch(url+'/../desktop/server.mjs')).status,404)}finally{await new Promise(ok=>server.close(ok))}
});

test('flags nativas protegem dimensões e rejeitam imagens inválidas',()=>{
 assert.throws(()=>imageBytes('not-an-image'));assert.throws(()=>buildArgs({},'x',[],'p','o',511,512,2));assert.deepEqual(imageBytes(PNG.toString('base64')),PNG);
});

test('o binário oficial local inicia e oferece edição multirreferência',{skip:!process.env.PROELIUM_NATIVE_PROBE},async()=>{
 let output='';await nativeRun(process.env.PROELIUM_NATIVE_PROBE,['--help'],s=>output+=s);assert.match(output,/commit 8c442fb/);assert.match(output,/--ref-image/);assert.match(output,/--llm/);assert.match(output,/--backend/);
});
