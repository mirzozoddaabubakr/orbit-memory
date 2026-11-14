const base='http://127.0.0.1:47831';
const queuePrefix='pending:';
const patterns=fetch(chrome.runtime.getURL('secret-patterns.json')).then(r=>r.json()).then(rows=>
  rows.map(([name,source,flags=''])=>[name,new RegExp(source,flags+'g')]));
async function safeItem(item){
  const rules=await patterns;
  const result={...item};
  for(const field of ['provider','url','title','transcript']){
    if(typeof result[field]!=='string')continue;
    for(const [name,pattern] of rules){
      result[field]=result[field].replace(pattern,(...args)=>(args.length>3?args[1]:'')+'<redacted:'+name.replaceAll(' ','-')+'>');
    }
  }
  return result;
}
let task=Promise.resolve();
function serialize(fn){
  const next=task.then(fn);
  task=next.catch(()=>{});
  return next;
}
async function deliver(item,key){
  const response=await fetch(base+'/api/capture',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+key},body:JSON.stringify(item),signal:AbortSignal.timeout(12000)});
  if(!response.ok)throw Error((await response.json()).error);
  await chrome.storage.local.set({lastSaved:Date.now(),lastError:''});
}
async function drain(){
  const storage=await chrome.storage.local.get(null);
  const entries=Object.entries(storage).filter(([key])=>key.startsWith(queuePrefix)).sort((a,b)=>a[1].time-b[1].time);
  for(const [id,record] of entries){
    const clean=await safeItem(record.item);
    if(JSON.stringify(clean)!==JSON.stringify(record.item)){
      record.item=clean;await chrome.storage.local.set({[id]:record});
    }
  }
  for(const [id,record] of entries){
    // An older queue entry has no verifiable owner. Never replay it under a new login.
    if(!record.ownerKey||record.ownerKey!==storage.key)continue;
    try{await deliver(record.item,record.ownerKey);await chrome.storage.local.remove(id);}
    catch(e){await chrome.storage.local.set({lastError:'Capture queued. Open Orbit to finish saving. '+e.message});return false;}
  }
  return true;
}
chrome.alarms.onAlarm.addListener(alarm=>{if(alarm.name==='orbit-retry')serialize(drain);});
chrome.runtime.onInstalled.addListener(()=>chrome.alarms.create('orbit-retry',{periodInMinutes:1}));
chrome.runtime.onStartup.addListener(()=>chrome.alarms.create('orbit-retry',{periodInMinutes:1}));
chrome.runtime.onMessage.addListener((msg,sender,reply)=>{
  if(msg.type!=='capture'||!sender.tab||!sender.url)return false;
  serialize(async()=>{
    const url=new URL(sender.url);
    const {key,enabled=[]}=await chrome.storage.local.get(['key','enabled']);
    if(!key||!enabled.includes(url.hostname)||msg.item.url!==url.origin+url.pathname.replace(/\/$/,''))throw Error('Capture is off for this site.');
    if(await drain()){
      try{await deliver(msg.item,key);return;}
      catch{/* Persist the snapshot locally for the next retry. */}
    }
    const record={time:Date.now(),item:await safeItem(msg.item),ownerKey:key};
    // Collapse ordinary streaming updates but preserve edited or partial versions.
    const pending=Object.entries(await chrome.storage.local.get(null)).filter(([k,v])=>k.startsWith(queuePrefix)&&v.ownerKey===key&&v.item.url===record.item.url);
    const last=pending.sort((a,b)=>b[1].time-a[1].time)[0];
    if(last && last[1].item.transcript.includes(record.item.transcript))return;
    const id=last&&record.item.transcript.includes(last[1].item.transcript)?last[0]:queuePrefix+crypto.randomUUID();
    await chrome.storage.local.set({[id]:record,lastError:'Capture queued. Open Orbit to finish saving.'});
  }).then(()=>reply({ok:true})).catch(async e=>{await chrome.storage.local.set({lastError:e.message});reply({ok:false});});
  return true;
});
chrome.runtime.onMessage.addListener((msg,sender)=>{
  if(msg.type!=='open-recall'||!sender.tab||sender.frameId!==0)return;
  const hosts=['claude.ai','chatgpt.com','gemini.google.com','chat.qwen.ai'];
  const source=new URL(sender.url);
  if(source.protocol==='https:'&&hosts.includes(source.hostname)){
    chrome.windows.create({type:'popup',width:560,height:640,
      url:chrome.runtime.getURL('recall.html')+'?tab='+sender.tab.id});
  }
});
