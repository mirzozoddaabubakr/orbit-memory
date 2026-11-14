const el=id=>document.getElementById(id);
let snapshot=null, selected=new Set(), busy=false;
const tabId=Number(new URLSearchParams(location.search).get('tab'));
async function lookup(topic){
  const {key}=await chrome.storage.local.get('key');
  if(!key) throw Error('Pair the extension with Orbit first.');
  const res=await fetch('http://127.0.0.1:47831/api/recall',{method:'POST',
    headers:{'Content-Type':'application/json',Authorization:'Bearer '+key},body:JSON.stringify({topic})});
  if(!res.ok) throw Error('Open Orbit and check your extension pairing.');
  return {key,topic,result:await res.json()};
}
function render(){
  const result=snapshot?.result;
  el('items').replaceChildren();
  for(const item of result?.items||[]){
    const label=document.createElement('label'), box=document.createElement('input');
    box.type='checkbox';box.checked=selected.has((item.project_id||item.memory_id));
    box.onchange=()=>{if(box.checked)selected.add((item.project_id||item.memory_id));else selected.delete((item.project_id||item.memory_id));render();};
    label.append(box,document.createTextNode(item.title));el('items').append(label);
  }
  const blocks=result?.items.filter(item=>selected.has((item.project_id||item.memory_id))).map(item=>item.reference)||[];
  el('preview').textContent=result?[result.preamble,...blocks].join('\n\n'):'';
  el('insert').disabled=busy||!blocks.length;el('preview').hidden=!result;el('copy').disabled=busy||!blocks.length;
}
function show(next){
  snapshot=next;selected=new Set(next.result.items.map(item=>(item.project_id||item.memory_id)));render();
}
async function action(fn){
  if(busy)return;
  busy=true;el('topic').disabled=el('search').disabled=true;el('items').inert=true;
  el('status').textContent='';render();
  try{await fn();}catch(e){el('status').textContent=e.message;}
  finally{busy=false;el('topic').disabled=el('search').disabled=false;el('items').inert=false;render();}
}
el('search').onclick=()=>action(async()=>show(await lookup(el('topic').value)));
el('topic').oninput=()=>{snapshot=null;selected.clear();render();};
async function confirmSelection(write){
  if(!snapshot||!selected.size)return;
  const next=await lookup(snapshot.topic);
  const refs=result=>result.items.filter(i=>selected.has((i.project_id||i.memory_id))).map(i=>i.reference);
  if(next.key!==snapshot.key || next.result.preamble!==snapshot.result.preamble ||
     JSON.stringify(refs(next.result))!==JSON.stringify(refs(snapshot.result))){
    show(next); el('status').textContent='Memory changed. Review the updated preview and confirm again.';return;
  }
  await write(el('preview').textContent);
}
el('copy').onclick=()=>action(()=>confirmSelection(async text=>{
  await navigator.clipboard.writeText(text);el('status').textContent='Copied.';
}));
el('cancel').onclick=()=>window.close();

let destination;
async function readDraft(){
  if(!Number.isInteger(tabId)||tabId<=0)return;
  try{
    const target={tabId};
    await chrome.scripting.executeScript({target,files:['composer.js']});
    const [probe]=await chrome.scripting.executeScript({target,func:()=>{
      const e=globalThis.orbitComposer.composer();
      return e?{url:location.href,draft:globalThis.orbitComposer.draft(e).slice(0,4000)}:null;
    }});
    if(!probe.result)return;
    destination={url:probe.result.url,documentId:probe.documentId};
    if(!snapshot && !el('topic').value)el('topic').value=probe.result.draft;
    el('insert').hidden=new URL(destination.url).origin!=='https://chat.qwen.ai';
  }catch{/* Toolbar copy works without persistent site access. */}
}
el('insert').onclick=()=>action(()=>confirmSelection(async text=>{
  try{
    const [response]=await chrome.scripting.executeScript({
      target:{tabId,documentIds:[destination.documentId]},args:[destination.url,text],
      func:(url,reference)=>location.href===url && location.origin==='https://chat.qwen.ai' &&
        globalThis.orbitComposer.insert(reference)
    });
    if(!response.result)throw Error();
    window.close();
  }catch{
    el('insert').hidden=true;
    el('status').textContent='Check your draft. Use Copy selected context if the reference is missing.';
  }
}));
readDraft();
