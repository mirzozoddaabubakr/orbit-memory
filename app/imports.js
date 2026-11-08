function parts(value){
 if(typeof value==='string')return value;
 if(Array.isArray(value))return value.map(parts).filter(Boolean).join('\n');
 if(!value||typeof value!=='object')return '';
 return parts(value.text||value.parts||value.content);
}
function parseRecord(r,provider){
 if(typeof r.transcript==='string')return {provider:r.provider||provider,title:r.title,transcript:r.transcript};
 if(r.mapping){
   let at=r.current_node || Object.keys(r.mapping).filter(k=>!r.mapping[k].children?.length).pop();
   const turns=[],visited=new Set();
   while(at&&r.mapping[at]&&!visited.has(at)){visited.add(at);const node=r.mapping[at];const m=node.message;
     if(m && !m.metadata?.is_visually_hidden_from_conversation){const text=parts(m.content);if(text)turns.push((m.author?.role||'Message')+': '+text);}
     at=node.parent;
   }
   const transcript=turns.reverse();
   const other=Object.entries(r.mapping).filter(([k,node])=>!visited.has(k)&&node.message&&!node.message.metadata?.is_visually_hidden_from_conversation);
   if(other.length){
     transcript.push('Alternate conversation branches');
     for(const [key,node] of other){
       const text=parts(node.message.content);
       if(text)transcript.push('['+key+' · reply to '+(node.parent||'root')+'] '+(node.message.author?.role||'Message')+': '+text);
     }
   }
   return {provider:'ChatGPT',title:r.title,transcript:transcript.join('\n\n')};
 }
 const messages=r.chat_messages||r.messages;
 if(Array.isArray(messages))return {provider:r.chat_messages?'Claude':(r.provider||provider),title:r.name||r.title,
   transcript:messages.map(m=>{const text=parts(m.content)||parts(m.text);return text?(m.sender||m.role||m.author?.role||'Message')+': '+text:'';}).filter(Boolean).join('\n\n')};
 throw Error('Unrecognized JSON. Paste the conversation or import a text file instead.');
}
export function readFile(name,text,provider){
 if(!name.toLowerCase().endsWith('.json'))return [{title:name.replace(/\.[^.]+$/,''),provider,transcript:text}];
 const data=JSON.parse(text.replace(/^\uFEFF/,'')),rows=Array.isArray(data)?data:(data.conversations||[data]);
 const items=rows.map(r=>parseRecord(r,provider)).filter(r=>r.transcript?.trim());
 if(!items.length)throw Error('This file contains no readable conversation text.');
 return items;
}
