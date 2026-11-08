import {icon,colors,providerMark} from './icons.js';
import {mountUniverse} from './universe.js';
import {readFile} from './imports.js';

const $=s=>document.querySelector(s), esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const names={universe:'Memory universe',library:'Memory library',starred:'Starred',sources:'Sources'};
let real=[],active='universe',filter='',query='',dispose=null,selected=null,tab='summary',history=[],loaded=false,failure='',sort='recent';
let account;
const providers=()=>[...new Set(real.map(m=>m.provider))].sort((a,b)=>a.localeCompare(b));
const day=m=>new Date(m.updated).toLocaleDateString(undefined,{month:'short',day:'numeric'});
const tint=p=>colors[p]||'#a6b4c7';
async function api(path,data){
 const headers=account?{'X-Orbit-Account':account.id}:{};
 const r=await fetch('/api/'+path,data?{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify(data)}:{headers});
 if(r.status===401){location.replace('/');throw Error('Sign in to Orbit.');}
 const body=await r.json();if(!r.ok)throw Error(body.error||'Request failed');return body;
}
let toastTimer;
function toast(msg){$('#toast').textContent=msg;$('#toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),3500);}
async function refresh(){try{real=await api('memories');loaded=true;failure='';}catch(e){failure=e.message;}render();}
function navButton(id,label,count){return '<button class="nav-button '+(active===id&&!filter?'chosen':'')+'" data-nav="'+id+'">'+icon(id==='sources'?'link':id==='starred'?'star':id)+'<span>'+esc(label)+'</span>'+(count===undefined?'':'<small>'+count+'</small>')+'</button>';}
function navigate(id,p=''){active=id;filter=p;query='';$('#search').value='';location.hash=p?'source/'+encodeURIComponent(p):id;document.body.classList.remove('show-menu');render();}
function fromHash(){const hash=decodeURIComponent(location.hash.slice(1));filter=hash.startsWith('source/')?hash.slice(7):'';active=filter?'library':Object.hasOwn(names,hash)?hash:'universe';render();}
function visible(){
 let list=real.filter(m=>(!filter||m.provider===filter)&&(active!=='starred'||m.starred)&&(!query||[m.title,m.provider,m.transcript,m.summary.overview].some(s=>s.toLowerCase().includes(query.toLowerCase()))));
 if(sort==='title')list.sort((a,b)=>a.title.localeCompare(b.title));return list;
}
function card(m){return '<article class="card" style="--tint:'+tint(m.provider)+'"><button class="card-open" data-open="'+m.id+'" aria-label="Open '+esc(m.title)+'"></button><div class="card-top"><div class="provider">'+providerMark(m.provider)+esc(m.provider)+'</div><button class="fav '+(m.starred?'on':'')+'" data-star="'+m.id+'" title="'+(m.starred?'Remove from starred':'Star memory')+'" aria-label="'+(m.starred?'Unstar ':'Star ')+esc(m.title)+'">'+icon('star',16)+'</button></div><h3>'+esc(m.title)+'</h3><p>'+esc(m.summary.overview)+'</p><div class="card-bottom"><span class="tag">'+esc(m.topic||(m.url?'Captured':'Imported'))+'</span><time>'+icon('clock',13)+day(m)+'</time></div></article>';}
function empty(){return '<div class="empty">'+icon(active==='starred'?'star':'search',25)+'<h3>'+(active==='starred'&&!query?'No starred memories yet':'No matching memories')+'</h3><p>'+(active==='starred'&&!query?'Use the star on a memory to keep it here.':'Try a different search or add a conversation.')+'</p></div>';}
function scene(){return '<section class="scene" aria-label="Interactive orbital memory map"><canvas aria-label="Drag to rotate the map. Select a labeled planet to read a conversation."></canvas><div class="planet-labels"></div><div class="scene-top"><span class="map-label"><i></i>ORBITAL VIEW</span><button class="map-btn" data-map="expand" aria-label="Expand map" title="Expand map">'+icon('expand',16)+'</button></div><div class="scene-foot"><span class="scene-hint">'+icon('mouse',14)+'Drag to orbit <b>·</b> Select a memory</span><div class="map-controls">'+['minus','plus','reset'].map((k,i)=>'<button data-map="'+k+'" aria-label="'+['Zoom out','Zoom in','Reset view'][i]+'" title="'+['Zoom out','Zoom in','Reset view'][i]+'">'+icon(k,15)+'</button>').join('')+'</div></div></section>';}
function render(){
 if(dispose){dispose();dispose=null;}
 const items=real, pnames=providers();
 if(loaded&&!failure&&filter&&!pnames.includes(filter)){
   active='library';filter='';window.history.replaceState(null,'','#library');
 }
 const list=visible();
 $('.source-label').hidden=!pnames.length;
 const firstMemory=loaded&&!failure&&!items.length&&!query&&['universe','library'].includes(active);
 $('#add').hidden=firstMemory;
 $('#nav').innerHTML=navButton('universe',names.universe)+navButton('library',names.library,items.length)+navButton('starred','Starred')+navButton('sources','Sources');
 $('#sourceNav').innerHTML=pnames.map(p=>'<button class="source-nav '+(filter===p?'selected':'')+'" data-source="'+esc(p)+'"><i style="background:'+tint(p)+'"></i>'+esc(p)+'</button>').join('');
 $('#crumb').textContent=filter||names[active];
 if(failure){$('#main').innerHTML='<h1>Library unavailable</h1><p>Open Orbit on this computer, then retry.</p><button id="retry" class="plain">Retry</button>';$('#retry').onclick=refresh;return;}
 if(!loaded){$('#main').innerHTML='<p>Opening your library…</p>';return;}
 if(active==='sources'&&!query){sources();return;}
 const home=active==='universe'&&!query;
 const title=query?'Search results':filter?filter+' memories':names[active];
 const heading='<div class="page-intro"><h1>'+esc(title)+'</h1></div>';
 if(firstMemory){
   $('#main').innerHTML=heading+'<section class="scene first-memory"><canvas aria-hidden="true"></canvas><div class="first-copy"><h2>No memories yet</h2><p>Add a conversation to start your orbit.</p><button class="primary" id="firstAdd">'+icon('plus',16)+'Add memory</button></div></section>';
   dispose=mountUniverse($('.scene'),[],open);
   $('#firstAdd').onclick=addModal;
   return;
 }
 $('#main').innerHTML=heading+
 (home?scene()+'<div class="scene-caption"><div class="map-legend">'+[...new Set(items.map(m=>m.provider))].map(p=>'<span><i style="background:'+tint(p)+'"></i>'+esc(p)+'</span>').join('')+'</div><span>'+items.length+' memories in orbit</span></div>':'')+
 '<section class="memory-section"><div class="section-head"><div><h2>'+(home?'Recent memories':query?'Matching memories':'Memories')+'</h2><span class="count">'+list.length+'</span></div>'+(home?'<button class="text-btn" data-nav="library">View library '+icon('arrow',15)+'</button>':'<select id="sort" aria-label="Sort memories"><option value="recent">Most recent</option><option value="title">Title A–Z</option></select>')+'</div>'+
 (list.length?'<div class="cards">'+(home?list.slice(0,3):list).map(card).join('')+'</div>':empty())+'</section>';
 if(home)dispose=mountUniverse($('.scene'),items,open);
 if($('#sort')){$('#sort').value=sort;$('#sort').onchange=e=>{sort=e.target.value;render();};}
}
function sources(){
 const main=$('#main');
 function row(symbol,title,description,body){
   return '<details class="setup-row"><summary><span class="setup-icon">'+icon(symbol,20)+'</span><span><strong>'+title+'</strong><small>'+description+'</small></span>'+icon('chevron',16)+'</summary><div class="setup-body">'+body+'</div></details>';
 }
 const agent='<select id="agentChoice" aria-label="Choose an agent"><option value="">Choose an agent…</option></select><p class="agent-instructions"></p><pre class="agent-config" hidden></pre><button class="plain agent-copy" hidden>Copy setup</button><a class="plain agent-download" download="Orbit Memory.mcpb" hidden>Download Orbit extension</a>';
 const browser='<ol><li>In Chrome or Edge extensions, turn on <strong>Developer mode</strong>.</li><li>Choose <strong>Load unpacked</strong> and select the Orbit folder. <button class="inline" id="folder">Copy folder path</button></li><li>Open the extension and paste your pairing code. <button class="inline" id="pairKey">Copy code</button></li><li>Open a chat and choose <strong>Enable capture</strong>.</li></ol><p>Only loaded chat text is saved. For another site, choose <strong>Configure another AI site</strong> or <strong>Save selected text</strong> in the extension.</p>';
 main.innerHTML='<div class="page-intro"><h1>Sources</h1></div><section class="connection-list" aria-label="Connection setup">'+
   row('link','MCP connection','Connect an AI agent to your library.',agent)+
   row('universe','Browser extension','Save chats as you browse.',browser)+'</section>';
 const select=$('#agentChoice'),settings=select.closest('details');
 settings.addEventListener('toggle',async()=>{
   if(!settings.open||select.options.length>1||select.disabled)return;
   select.disabled=true;
   try{
     const choices=await api('agent-connections');
     const instructions=settings.querySelector('.agent-instructions'),config=settings.querySelector('pre');
     const copySetup=settings.querySelector('.agent-copy'),download=settings.querySelector('a');
     for(const name of Object.keys(choices))select.add(new Option(name,name));
     const keyButton=document.createElement('button');keyButton.className='plain';keyButton.textContent='Copy agent pairing code';
     settings.querySelector('.setup-body').append(keyButton);
     keyButton.onclick=async()=>{try{await copy((await api('agent-key')).key,'Pairing code copied');}catch(e){toast(e.message);}};
     select.onchange=()=>{
       const chosen=choices[select.value]||{};
       instructions.textContent=chosen.help||'';config.textContent=chosen.value||'';
       config.hidden=copySetup.hidden=!chosen.value;download.hidden=!chosen.download;
       keyButton.hidden=select.value!=='Claude Desktop';
       if(chosen.download)download.href=chosen.download;
       copySetup.onclick=()=>copy(chosen.value,'Setup copied').catch(e=>toast(e.message));
     };
     select.onchange();
   }catch(e){settings.querySelector('.agent-instructions').textContent='Could not load setup. Reopen to retry.';}
   finally{select.disabled=false;}
 });
 $('#folder').onclick=async()=>{try{await copy((await api('setup')).folder,'Extension folder path copied');}catch(e){toast(e.message);}};
 $('#pairKey').onclick=async()=>{try{await copy((await api('setup')).key,'Pairing code copied');}catch(e){toast(e.message);}};
}

async function copy(t,msg){try{await navigator.clipboard.writeText(t);toast(msg);}catch{throw Error('Clipboard unavailable. Use Download handoff or allow clipboard access.');}}
function modal(body){$('#modalBody').innerHTML=body;if(!$('#modal').open)$('#modal').showModal();}
function close(){selected=null;$('#modal').close();}
function closeBtn(){return '<button class="icon close" data-close aria-label="Close dialog">'+icon('close',20)+'</button>';}
async function open(id){
 const m=real.find(x=>x.id===id);if(!m)return;selected=m;tab='summary';history=[];detail();
 try{const result=await api('history/'+id);if(selected?.id===id){history=result;detail();}}catch(e){toast(e.message);}
}
function summaryView(m){
 const s=m.summary;return '<section class="brief"><h4>Overview</h4><p>'+esc(s.overview)+'</p>'+[['highlights','Key details'],['decisions','Decisions and progress'],['next','Open questions and next steps']].filter(([k])=>s[k]?.length).map(([k,l])=>'<h4>'+l+'</h4><ul>'+s[k].map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>').join('')+'</section>';
}
function handoff(m){const s=m.summary;return ['# '+m.title,'Source: '+m.provider+(m.url?'\n'+m.url:''),'## Overview\n'+s.overview,...[['highlights','Key details'],['decisions','Decisions and progress'],['next','Open questions and next steps']].filter(([k])=>s[k]?.length).map(([k,l])=>'## '+l+'\n'+s[k].map(x=>'- '+x).join('\n')),'## Full conversation\n'+m.transcript,...history.map((t,i)=>'## Earlier captured version '+(i+1)+'\n'+t)].join('\n\n');}
function detail(){
 const m=selected;if(!m)return;
 modal(closeBtn()+'<div class="detail-meta provider" style="--tint:'+tint(m.provider)+'">'+providerMark(m.provider)+esc(m.provider)+'</div><h2>'+esc(m.title)+'</h2><p class="detail-date">'+day(m)+' · '+m.transcript.trim().split(/\s+/).length+' words</p><div class="tabs">'+[['summary','Summary'],['transcript','Conversation'],['handoff','Handoff']].map(([k,l])=>'<button class="'+(tab===k?'active':'')+'" data-tab="'+k+'">'+l+'</button>').join('')+'</div><div class="reader">'+(tab==='summary'?summaryView(m):tab==='handoff'?'<pre>'+esc(handoff(m))+'</pre>':'<pre>'+esc(m.transcript)+'</pre>'+history.map((t,i)=>'<details><summary>Earlier captured version '+(i+1)+'</summary><pre>'+esc(t)+'</pre></details>').join(''))+'</div><footer class="dialog-actions"><button class="primary" id="copy">'+icon('copy',15)+'Copy handoff</button><button class="plain" id="download">Download</button>'+'<button class="icon delete" id="delete" aria-label="Delete memory">'+icon('trash')+'</button>'+'</footer>');
 if(tab==='summary'){
   const box=document.createElement('details');box.className='ai-brief';
   box.innerHTML='<summary>'+esc(m.summary.model?'Brief generated with '+m.summary.model:'Generate a brief with local AI')+'</summary><div class="model-options"></div>';
   $('.reader').append(box);
   box.addEventListener('toggle',async()=>{
     if(!box.open||box.dataset.ready)return;
     const options=box.querySelector('.model-options');options.textContent='Looking for local models…';
     try{
       const models=await api('models');
       if(!models.length){options.textContent='Start Ollama with a downloaded chat model to generate a written brief. The automatic summary above uses excerpts from your conversation.';return;}
       box.dataset.ready='1';options.innerHTML='<label>Local model<select>'+models.map(name=>'<option>'+esc(name)+'</option>').join('')+'</select></label><button class="plain">Generate brief</button><p role="status"></p>';
       const generate=options.querySelector('button'),status=options.querySelector('p');
       generate.onclick=async()=>{generate.disabled=true;status.textContent='Reading the saved conversation on this device…';
         try{const summary=await api('brief',{id:m.id,model:options.querySelector('select').value});m.summary=summary;await refresh();if(selected?.id===m.id){selected=m;detail();}toast('Local AI brief saved');}
         catch(e){status.textContent=e.message;generate.disabled=false;}
       };
     }catch(e){options.textContent=e.message;}
   });
 }
 async function packet(){history=await api('history/'+m.id);return handoff(m);}
 $('#copy').onclick=async()=>{try{await copy(await packet(),'Handoff copied, including the full conversation');}catch(e){toast(e.message);}};
 $('#download').onclick=async()=>{try{const u=URL.createObjectURL(new Blob([await packet()],{type:'text/markdown'}));const a=document.createElement('a');a.href=u;a.download=(m.title.replace(/[^\p{L}\p{N} ._-]/gu,'').trim()||'memory')+'.md';a.click();setTimeout(()=>URL.revokeObjectURL(u),2000);}catch(e){toast(e.message);}};
 if($('#delete'))$('#delete').onclick=()=>{if(confirm('Delete this memory and its saved versions from this device?'))api('change',{id:m.id,action:'delete'}).then(()=>{close();refresh();}).catch(e=>toast(e.message));};
}
function addModal(){
 selected=null;
 modal(closeBtn()+'<h2>Add memory</h2><form id="importForm"><label>AI source<input list="providers" id="provider" placeholder="Enter the model name"><datalist id="providers">'+providers().map(s=>'<option>'+esc(s)+'</option>').join('')+'</datalist></label><label>Conversation title <small>Optional</small><input id="title" maxlength="160" placeholder="Name this memory"></label><label>Conversation<textarea id="transcript" rows="7" placeholder="Paste the conversation, including both sides…"></textarea></label><label class="file-input">'+icon('file')+'Import a file<input type="file" id="file" accept=".txt,.md,.json"></label><small class="file-note" id="fileNote">Text, Markdown, or conversation JSON</small><p role="alert" id="error"></p><footer class="dialog-actions"><button type="submit" class="primary">'+icon('plus')+'Save memory</button><button type="button" data-close class="plain">Cancel</button></footer></form>');
 $('#file').onchange=()=>{$('#fileNote').textContent=$('#file').files[0]?.name||'Text, Markdown, or conversation JSON';$('#transcript').disabled=!!$('#file').files.length;};
 $('#importForm').onsubmit=async e=>{e.preventDefault();const submit=e.submitter;submit.disabled=true;$('#error').textContent='';let saved=0;
  try{const provider=$('#provider').value.trim(),title=$('#title').value.trim(),file=$('#file').files[0];let items;
    if(file){items=readFile(file.name,await file.text(),provider);if(items.length===1&&title)items[0].title=title;}
    else {
      if(!provider)throw Error('Enter the AI source.');
      items=[{provider,title,transcript:$('#transcript').value}];
    }
    if(items.some(item=>!item.provider?.trim()))throw Error('Enter the AI source for this conversation.');
    for(const item of items){if(!item.transcript?.trim())throw Error('Paste a conversation or choose a file.');await api('memories',item);saved++;}
    close();navigate('universe');await refresh();toast(saved===1?'Memory saved to your universe':saved+' memories imported');
  }catch(err){$('#error').textContent=(saved?saved+' saved. ':'')+err.message;if(saved)await refresh();}finally{submit.disabled=false;}
 };
}
async function star(id){const m=real.find(x=>x.id===id);if(!m)return;
 await api('change',{id,action:!m.starred});await refresh();
}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const d=b.dataset;
 if(d.nav)navigate(d.nav);else if(d.source)navigate('library',d.source);else if(d.open)open(d.open);else if(d.star)star(d.star).catch(e=>toast(e.message));else if(d.close!==undefined)close();else if(d.tab){tab=d.tab;detail();}
});
$('#modal').addEventListener('close',()=>selected=null);
$('#modal').addEventListener('click',e=>{if(e.target===$('#modal')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)close();}});
$('#menu').innerHTML=icon('menu');$('#menu').onclick=()=>document.body.classList.toggle('show-menu');
$('#add').innerHTML=icon('plus',17)+'Add memory';$('#add').onclick=addModal;$('#searchIcon').innerHTML=icon('search',16);
$('#search').oninput=e=>{query=e.target.value.trim();render();};
document.addEventListener('keydown',e=>{if(e.key==='/'&&!e.ctrlKey&&!e.metaKey&&!$('#modal').open&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();$('#search').focus();}});
window.addEventListener('hashchange',fromHash);
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!$('#modal').open)refresh();});
setInterval(async()=>{if(document.hidden||$('#modal').open)return;try{const next=await api('memories');if(JSON.stringify(next)!==JSON.stringify(real)||failure){real=next;loaded=true;failure='';render();}}catch{}},8000);
window.addEventListener('storage',e=>{if(e.key==='orbit-account-change')location.replace('/');});
window.addEventListener('pageshow',e=>{if(e.persisted)location.reload();});
try{
 account=(await api('session')).user;
 if(!account){location.replace('/login.html');}
 else{
   $('#accountEmail').textContent=account.email;$('#accountEmail').title=account.email;
   $('#signOut').onclick=async()=>{try{await api('auth/logout',{});localStorage.setItem('orbit-account-change',crypto.randomUUID());location.replace('/login.html');}catch(e){toast(e.message);}};
   fromHash();refresh();
 }
}catch(e){failure=e.message;render();}
