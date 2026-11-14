(() => {
  if(globalThis.orbitComposer)return;
  const selectors={
    'chatgpt.com':'#prompt-textarea',
    'claude.ai':'[data-testid="chat-input"],div.ProseMirror[contenteditable="true"]',
    'gemini.google.com':'rich-textarea [contenteditable="true"]',
    'chat.qwen.ai':'textarea.message-input-textarea,textarea[placeholder],div[contenteditable="true"][role="textbox"]'
  };
  function composer(){
    const selector=selectors[location.hostname];
    if(!selector||location.protocol!=='https:')return null;
    const matches=[...document.querySelectorAll(selector)].filter(e=>
      (e instanceof HTMLTextAreaElement||e.isContentEditable)&&e.getClientRects().length&&!e.disabled);
    return matches.length===1?matches[0]:null;
  }
  function draft(e){return e instanceof HTMLTextAreaElement?e.value:e.innerText;}
  function insert(text){
    const e=composer();
    if(!e)return false;
    const before=draft(e), addition=(before?'\n\n':'')+text;
    e.focus();
    if(e instanceof HTMLTextAreaElement)e.setSelectionRange(before.length,before.length);
    else{
      const range=document.createRange();range.selectNodeContents(e);range.collapse(false);
      const selection=getSelection();selection.removeAllRanges();selection.addRange(range);
    }
    if(!document.execCommand('insertText',false,addition))return false;
    return draft(e)===before+addition;
  }
  let button;
  function place(){
    const e=composer();
    if(!e){button?.remove();return;}
    if(!button){
      button=document.createElement('button');button.type='button';button.textContent='Load Orbit memory';
      button.onclick=event=>{if(event.isTrusted)chrome.runtime.sendMessage({type:'open-recall'});};
    }
    if(e.previousElementSibling!==button)e.before(button);
  }
  globalThis.orbitComposer={composer,draft,insert,place,remove:()=>button?.remove()};
})();
