import http from 'node:http';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {resolve,join,dirname} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {spawn} from 'node:child_process';
import {createEngine} from './engine.mjs';

export function createServer(engine,html){
 const json=(res,value,status=200)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(JSON.stringify(value))};
 return http.createServer(async(req,res)=>{try{
  const authority='127.0.0.1:'+req.socket.localPort;
  if(req.headers.host!==authority)return json(res,{error:'Endereço local inválido'},403);
  const url=new URL(req.url,'http://'+authority);
  if(req.headers.origin&&req.headers.origin!=='http://'+authority)return json(res,{error:'Origem externa recusada'},403);
  if(req.method==='GET'&&url.pathname==='/'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});return res.end(html.replace('<script>','<script>window.PROELIUM_DESKTOP=true;</script><script>'))}
  if(req.method==='GET'&&url.pathname==='/engine/status')return json(res,engine.status());
  if(req.method==='GET'&&url.pathname.startsWith('/engine/jobs/')){const id=url.pathname.slice('/engine/jobs/'.length);return json(res,await engine.job(id))}
  if(req.method==='GET'&&url.pathname.startsWith('/engine/result/')){const b=await engine.result(url.pathname.slice('/engine/result/'.length));res.writeHead(200,{'Content-Type':'image/png','Cache-Control':'no-store'});return res.end(b)}
  if(req.method!=='POST')return json(res,{error:'Não encontrado'},404);
  if(req.headers['content-type']!=='application/json')return json(res,{error:'Use JSON'},415);
  const chunks=[];let size=0;for await(const b of req){size+=b.length;if(size>96*1024*1024)return json(res,{error:'Envio grande demais. Reduza a resolução das referências.'},413);chunks.push(b)}
  const payload=JSON.parse(Buffer.concat(chunks).toString()||'{}');
  if(url.pathname==='/engine/setup'){engine.setup().catch(()=>{});return json(res,{started:true})}
  if(url.pathname==='/engine/edit')return json(res,await engine.start(payload),202);
  json(res,{error:'Não encontrado'},404);
 }catch(e){json(res,{error:e.message},400)}});
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 const appRoot=resolve(dirname(fileURLToPath(import.meta.url)),'..'),desktopDir=join(appRoot,'desktop'),dataRoot=process.env.PROELIUM_ENGINE_DATA?resolve(process.env.PROELIUM_ENGINE_DATA):join(appRoot,'engine-data');
 await mkdir(dataRoot,{recursive:true});
 const executable=process.env.PROELIUM_ENGINE_EXE||join(appRoot,'native',process.platform==='win32'?'sd-cli.exe':'sd-cli');
 let manifest;if(!process.env.PROELIUM_ENGINE_EXE)manifest=JSON.parse(await readFile(join(desktopDir,'native-sha256.json'),'utf8'));
 const engine=createEngine({root:dataRoot,executable,manifest});let html;try{html=await readFile(join(appRoot,'Proelium Studio.html'),'utf8')}catch(e){if(e.code!=='ENOENT')throw e;html=await readFile(join(appRoot,'dist','Proelium Studio.html'),'utf8')}
 const server=createServer(engine,html),port=Number(process.env.PROELIUM_PORT||8767);
 server.on('error',e=>{console.error(e.code==='EADDRINUSE'?'O Proelium já pode estar aberto nesta porta. Feche a outra instância e tente novamente.':e.message);process.exitCode=1});
 server.listen(port,'127.0.0.1',()=>{const url=`http://127.0.0.1:${server.address().port}`;console.log('Proelium Studio — '+url+'\nMantenha esta janela aberta. Os modelos serão preparados no aplicativo.');if(process.platform==='win32'&&!process.argv.includes('--no-browser'))spawn('rundll32.exe',['url.dll,FileProtocolHandler',url],{windowsHide:true}).on('error',()=>console.log('Abra o endereço acima no seu navegador.')).unref()});
}
