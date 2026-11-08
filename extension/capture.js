(() => {
  if (globalThis.orbitCapture) return;
  const adapters = {
    'chatgpt.com': ['ChatGPT', /\/c\/[^/]+/, '[data-message-author-role="user"],[data-message-author-role="assistant"]', '[data-message-author-role="user"]'],
    'claude.ai': ['Claude', /\/chat\/[^/]+/, '[data-testid="user-message"],[data-testid="assistant-message"],.font-claude-response,[data-is-streaming] .standard-markdown', '[data-testid="user-message"]'],
    'gemini.google.com': ['Gemini', /\/app\/[^/]+/, 'user-query,model-response', 'user-query'],
    'chat.qwen.ai': ['Qwen', /\/(?:c|chat|s)\/[^/]+/, '[class*="chat-message-user"],[class*="chat-message-assistant"],[data-message-author-role],[class~="user-message"],[class~="assistant-message"]', '[class*="chat-message-user"],[data-message-author-role="user"],.user-message']
  };
  async function snapshot() {
    let spec = adapters[location.hostname];
    if (!spec) {
      const {customSites={}}=await chrome.storage.local.get('customSites');
      const config=customSites[location.hostname];
      if (!config) return null;
      spec=[config.name, /./, config.user+', '+config.assistant, config.user];
    }
    if (!spec[1].test(location.pathname) || location.pathname==='/') return null;
    const candidates = [...document.querySelectorAll(spec[2])];
    const messages = candidates.filter(n => n.getClientRects().length && !candidates.some(parent => parent !== n && parent.contains(n)));
    function visibleText(node) {
      if(node.nodeType===Node.TEXT_NODE)return node.textContent;
      if(node.nodeType!==Node.ELEMENT_NODE || node.matches('button,textarea,input,script,style,svg,[aria-hidden="true"],[hidden]'))return '';
      const style=getComputedStyle(node);
      if(style.display==='none'||style.visibility==='hidden')return '';
      if(node.tagName==='BR')return '\n';
      if(node.tagName==='PRE')return '\n```\n'+node.innerText+'\n```\n';
      const value=Array.from(node.childNodes,visibleText).join('');
      if(node.tagName==='TD'||node.tagName==='TH')return value+'\t';
      return style.display==='block'||node.tagName==='LI'||node.tagName==='TR'?'\n'+value+'\n':value;
    }
    const turns = messages.map(el => {
      const text = visibleText(el).trim();
      return text && (el.matches(spec[3]) ? 'You' : spec[0]) + ': ' + text;
    }).filter(Boolean);
    if (!turns.length) return null;
    const title = document.title.replace(/\s+[-|–]\s+(?:Claude|ChatGPT|Gemini|Qwen).*$/i, '').trim();
    return {provider:spec[0], title: !title || /^(Claude|ChatGPT|Gemini|Qwen|Google Gemini)$/i.test(title) ? turns[0].replace(/^\w+: /,'').slice(0,100) : title,
      url:location.origin + location.pathname.replace(/\/$/,''),transcript:turns.join('\n\n')};
  }
  globalThis.orbitCapture = snapshot;
  let previous = '', busy = false, dirty=true;
  const observer=new MutationObserver(()=>{dirty=true;});
  observer.observe(document.documentElement,{childList:true,characterData:true,subtree:true});
  async function sync() {
    if (busy || !chrome.runtime?.id || !dirty) return;
    busy = true;
    dirty=false;
    try {
      const item = await snapshot();
      if (!item) return;
      const signature = JSON.stringify(item);
      if (signature === previous) return;
      const result = await chrome.runtime.sendMessage({type:'capture',item});
      if (result?.ok) previous = signature; else dirty=true;
    } catch { dirty=true; }
    finally { busy = false; }
  }
  const timer = setInterval(sync, 3500);
  const changed=()=>{dirty=true;sync();};
  document.addEventListener('visibilitychange',changed);
  chrome.runtime.onMessage.addListener(msg => {
    if (msg.type === 'stop') { clearInterval(timer); observer.disconnect(); document.removeEventListener('visibilitychange',changed); delete globalThis.orbitCapture; }
  });
  sync();
})();
