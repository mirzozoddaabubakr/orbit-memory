const base='http://127.0.0.1:47831';
const queuePrefix='pending:';
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
    const record={time:Date.now(),item:msg.item,ownerKey:key};
    // Collapse ordinary streaming updates but preserve edited or partial versions.
    const pending=Object.entries(await chrome.storage.local.get(null)).filter(([k,v])=>k.startsWith(queuePrefix)&&v.ownerKey===key&&v.item.url===msg.item.url);
    const last=pending.sort((a,b)=>b[1].time-a[1].time)[0];
    if(last && last[1].item.transcript.includes(msg.item.transcript))return;
    const id=last&&msg.item.transcript.includes(last[1].item.transcript)?last[0]:queuePrefix+crypto.randomUUID();
    await chrome.storage.local.set({[id]:record,lastError:'Capture queued. Open Orbit to finish saving.'});
  }).then(()=>reply({ok:true})).catch(async e=>{await chrome.storage.local.set({lastError:e.message});reply({ok:false});});
  return true;
});
