import {createEngine} from '../desktop/engine.mjs';
import {resolve,join} from 'node:path';
const root=process.env.PROELIUM_ENGINE_DATA||'/workspace/shared/proelium-engine/data';
const executable=process.env.PROELIUM_ENGINE_EXE||'/workspace/shared/proelium-engine/8c442fb/native/sd-cli';
const engine=createEngine({root:resolve(root),executable});
const timer=setInterval(()=>{const s=engine.status();console.log(s.phase+': '+s.message+(s.total?' '+Math.round(s.received/1024**2)+'/'+Math.round(s.total/1024**2)+' MiB':''))},10000);
try{await engine.setup();console.log(engine.status().message)}finally{clearInterval(timer)}
