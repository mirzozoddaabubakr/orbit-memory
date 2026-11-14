const $=id=>document.getElementById(id), base='http://127.0.0.1:47831';
const sites={'claude.ai':'Claude','chatgpt.com':'ChatGPT','gemini.google.com':'Gemini','chat.qwen.ai':'Qwen'};
let tab, host, state;
async function refresh(){
  [tab]=await chrome.tabs.query({active:true,currentWindow:true});
  host=tab?.url ? new URL(tab.url).hostname : '';
  state=await chrome.storage.local.get(['key','enabled','lastSaved','lastError','customSites','recallSites']);
  state.enabled ||= [];
  state.customSites ||= {};
  state.recallSites ||= [];
  $('recallSite').hidden=!sites[host];
  $('recallSite').textContent=state.recallSites.includes(host)?'Hide button on this site':'Show memory button on this site';
  $('pair').hidden=!!state.key; $('actions').hidden=!state.key;
  $('intro').textContent=state.key ? (sites[host] ? 'Capture conversations you open on '+sites[host]+'.' : 'Highlight a conversation on this page to save it.') : 'Find your pairing code in Orbit → Sources.';
  $('connect').hidden=!tab?.url?.startsWith('https://');
  $('custom').hidden=!!sites[host] || $('connect').hidden;
  const custom=state.customSites[host];
  $('siteName').value=custom?.name || host;
  if(custom){$('userSelector').value=custom.user;$('assistantSelector').value=custom.assistant;}
  $('connect').textContent=(state.enabled.includes(host)?'Pause ':'Enable ')+(sites[host]||custom?.name||'site')+' capture';
  $('status').textContent=state.lastError || (state.lastSaved ? 'Last saved '+new Date(state.lastSaved).toLocaleString() : '');
}
function run(fn){return async()=>{try{await fn();}catch(e){$('status').textContent=e.message==='Failed to fetch'?'Open the Orbit app on this computer and try again.':e.message;}};}
$('saveKey').onclick=run(async()=>{
  const key=$('key').value.trim();
  // The privileged background fetch authenticates with a local bearer key.
  const result=await fetch(base+'/api/pair',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})});
  if(!result.ok)throw Error('Pairing failed. Copy the code from Sources and try again.');
  await chrome.storage.local.set({key}); await refresh();
});
$('unpair').onclick=run(async()=>{
  await chrome.storage.local.set({enabled:[],recallSites:[]});
  await chrome.storage.local.remove(['key','lastSaved','lastError']);
  const scripts=await chrome.scripting.getRegisteredContentScripts();
  if(scripts.length)await chrome.scripting.unregisterContentScripts({ids:scripts.map(s=>s.id)});
  for(const domain of new Set([...state.enabled,...state.recallSites])){
    const pattern='https://'+domain+'/*';
    for(const page of await chrome.tabs.query({url:pattern}))await chrome.tabs.sendMessage(page.id,{type:'stop'}).catch(()=>{});
    await chrome.permissions.remove({origins:[pattern]});
  }
  await refresh();
});
$('connect').onclick=run(async()=>{
  const origin='https://'+host+'/*', id='capture-'+host;
  if(state.enabled.includes(host)){
    await chrome.storage.local.set({enabled:state.enabled.filter(h=>h!==host)});
    await chrome.scripting.unregisterContentScripts({ids:[id]}).catch(()=>{});
    for(const t of await chrome.tabs.query({url:origin})) await chrome.tabs.sendMessage(t.id,{type:'stop'}).catch(()=>{});
    if(!state.recallSites.includes(host))await chrome.permissions.remove({origins:[origin]});
  }else{
    if(!await chrome.permissions.request({origins:[origin]}))throw Error('Site permission was declined.');
    if(!sites[host]){
      const user=$('userSelector').value.trim(),assistant=$('assistantSelector').value.trim(),name=$('siteName').value.trim()||host;
      const [probe]=await chrome.scripting.executeScript({target:{tabId:tab.id},args:[user,assistant],func:(u,a)=>{
        try{return u!==a && location.pathname.length>1 && !!document.querySelector(u) && !!document.querySelector(a);}
        catch{return false;}
      }});
      if(!probe.result)throw Error('Open a chat with both sides visible and configure matching message selectors.');
      await chrome.storage.local.set({customSites:{...state.customSites,[host]:{user,assistant,name}}});
    }
    if(!(await chrome.scripting.getRegisteredContentScripts({ids:[id]})).length)
      await chrome.scripting.registerContentScripts([{id,matches:[origin],js:['capture.js'],runAt:'document_idle'}]);
    await chrome.storage.local.set({enabled:[...state.enabled,host]});
    await chrome.scripting.executeScript({target:{tabId:tab.id},files:['capture.js']});
  }
  await refresh();
});
$('selection').onclick=run(async()=>{
  const [r]=await chrome.scripting.executeScript({target:{tabId:tab.id},func:()=>({text:getSelection().toString(),title:document.title})});
  if(!r.result.text.trim())throw Error('First highlight the conversation text on this page.');
  const result=await fetch(base+'/api/selection',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+state.key},body:JSON.stringify({provider:sites[host]||host,title:r.result.title,transcript:r.result.text})});
  if(!result.ok)throw Error((await result.json()).error);
  $('status').textContent='Saved to your memory library.';
});
refresh().catch(e=>$('status').textContent=e.message);
$('recall').onclick=run(async()=>{
  await chrome.windows.create({type:'popup',width:560,height:640,
    url:chrome.runtime.getURL('recall.html')+'?tab='+tab.id});
});

$('recallSite').onclick=run(async()=>{
  if(!sites[host])return;
  const origin='https://'+host+'/*', id='recall-'+host;
  const files=['composer.js','recall-button.js'];
  if(state.recallSites.includes(host)){
    await chrome.scripting.unregisterContentScripts({ids:[id]});
    await chrome.storage.local.set({recallSites:state.recallSites.filter(h=>h!==host)});
    for(const t of await chrome.tabs.query({url:origin})){
      await chrome.scripting.executeScript({target:{tabId:t.id},func:()=>{
        globalThis.orbitRecallObserver?.disconnect();delete globalThis.orbitRecallObserver;
        globalThis.orbitComposer?.remove();
      }}).catch(()=>{});
    }
    if(!state.enabled.includes(host))await chrome.permissions.remove({origins:[origin]});
  }else{
    if(!await chrome.permissions.request({origins:[origin]}))throw Error('Site permission was declined.');
    await chrome.scripting.registerContentScripts([{id,matches:[origin],js:files}]);
    await chrome.storage.local.set({recallSites:[...state.recallSites,host]});
    await chrome.scripting.executeScript({target:{tabId:tab.id},files});
  }
  await refresh();
});
