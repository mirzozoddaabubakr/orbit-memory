import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from '../app/imports.js';

test('ChatGPT import preserves active and alternate messages',()=>{
  const message=text=>({author:{role:'assistant'},content:{parts:[text]}});
  const input={title:'Branches',current_node:'b',mapping:{a:{message:message('First.'),children:['b','c']},b:{parent:'a',message:message('Active.'),children:[]},c:{parent:'a',message:message('Alternate.'),children:[]}}};
  const [item]=readFile('chats.json',JSON.stringify([input]),'Other');
  assert.equal(item.provider,'ChatGPT');
  for(const text of ['First.','Active.','Alternate.'])assert.ok(item.transcript.includes(text));
});
test('Claude imports keep message order, code, and multiline text',()=>{
  const input={name:'Build',chat_messages:[{sender:'human',text:'Help me build.'},{sender:'assistant',content:[{type:'text',text:'Use this code:\nconst π = 3.14;'}]}]};
  const [item]=readFile('conversations.json',JSON.stringify([input]),'Other');
  assert.equal(item.provider,'Claude');
  assert.equal(item.transcript,'human: Help me build.\n\nassistant: Use this code:\nconst π = 3.14;');
});
test('plain text works for a custom source',()=>{
  assert.deepEqual(readFile('model.txt','a\nb','Local model'),[{title:'model',transcript:'a\nb',provider:'Local model'}]);
});
