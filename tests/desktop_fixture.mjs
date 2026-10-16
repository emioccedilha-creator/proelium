// Servidor exclusivo dos testes: não é incluído no pacote do usuário.
import {createEngine} from '../desktop/engine.mjs';
import {createServer} from '../desktop/server.mjs';
import {readFile,writeFile} from 'node:fs/promises';
const engine=createEngine({root:process.env.PROELIUM_TEST_DATA,executable:'/test-fixture/sd-cli',totalmem:()=>16*2**30,prepare:async()=>({diffusion:'fixture-diffusion',text:'fixture-text',vae:'fixture-vae'}),run:async(exe,args)=>{if(args[0]==='--help')return;const count=args.filter(a=>a==='-r').length;if(count!==11)throw Error('Referências omitidas no teste');const source=args[args.indexOf('-r')+1];await writeFile(args[args.indexOf('-o')+1],await readFile(source))}});
const html=await readFile(new URL('../dist/Proelium Studio.html',import.meta.url),'utf8');
createServer(engine,html).listen(0,'127.0.0.1',function(){console.log('PORT='+this.address().port)});
