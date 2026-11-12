import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

test('offline extension queue stores masked chat text and metadata',async()=>{
  const rules=JSON.parse(readFileSync('extension/secret-patterns.json','utf8'));
  let listener;
  const event={addListener(){}};
  const state={key:'fixture-pairing',enabled:['example.test']};
  const chrome={storage:{local:{
    get:async()=>({...state}), set:async data=>Object.assign(state,data),remove:async k=>delete state[k]
  }},alarms:{onAlarm:event},runtime:{getURL:()=>'/rules',onInstalled:event,onStartup:event,
    onMessage:{addListener:fn=>{listener=fn;}}}};
  const fetch=async url=>{
    if(url==='/rules')return {json:async()=>rules};
    throw Error('Offline fixture');
  };
  vm.runInNewContext(readFileSync('extension/background.js','utf8'),{chrome,fetch,crypto,URL,AbortSignal});
  const url='https://example.test/c/test',fake='ghp_'+'Q'.repeat(36);
  const result=await new Promise(resolve=>listener({type:'capture',item:{url,title:fake,provider:'Test',transcript:'Bearer '+fake}},
    {tab:{id:1},url},resolve));
  assert.ok(result.ok);
  const record=Object.entries(state).find(([key])=>key.startsWith('pending:'))[1];
  assert.equal(record.item.title,'<redacted:GitHub-token>');
  assert.equal(record.item.transcript,'Bearer <redacted:Bearer-token>');
  assert.ok(!JSON.stringify(record.item).includes(fake));
});
