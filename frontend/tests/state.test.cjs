// Exercise the real UI controller with a small DOM boundary. No browser internals.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function harness(fetcher) {
  const nodes = new Map();
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, {textContent:'', value:'', hidden:false, disabled:false, dataset:{},
      handlers:new Map(),classList:{toggle(){}},addEventListener(event,handler){this.handlers.set(event,handler);},
      setAttribute(){}, removeAttribute(){},close(){this.open=false;},
      replaceChildren(...children){this.children=children;}, append(){}, scrollIntoView(){}});
    return nodes.get(id);
  }
  const context = vm.createContext({
    document:{getElementById:node,querySelectorAll:()=>[],createElement:()=>node(Symbol()),createTextNode:(text)=>({textContent:text})},
    window:{APP_CONFIG:{API_BASE_URL:'http://api.test'}},
    localStorage:{getItem:()=> '5fd8cacc-2165-4f7e-97ba-678fbca1a823'},
    crypto:{randomUUID:()=> '5fd8cacc-2165-4f7e-97ba-678fbca1a823'},
    AbortController, setTimeout, clearTimeout, console,
    fetch:fetcher,
  });
  const source = fs.readFileSync(path.join(__dirname,'../app.js'),'utf8');
  vm.runInContext(source.replace(/\ninit\(\);\s*$/, '\n'),context);
  return {node,context};
}

test('failed conversation data refresh never displays previous market prices', async () => {
  const {node,context}=harness(async (url)=> {
      if(url.endsWith('/api/conversations/eth-conversation')) return {ok:true,status:200,json:async()=>({id:'eth-conversation',market:'KRW-ETH',title:'ETH 질문',messages:[{role:'user',content:'ETH 질문'}]})};
      throw new TypeError('unreachable');
  });
  vm.runInContext("state.markets=[]; state.records=[{id:'btc',market:'KRW-BTC',date:'2025-01-01',value:100}]; state.summary={count:1,metrics:{latest:100}}; renderSummary();",context);
  assert.equal(node('metric-latest').textContent,'100원');
  await vm.runInContext("openConversation('eth-conversation')",context);
  assert.equal(vm.runInContext('state.market',context),'KRW-ETH');
  assert.equal(node('context-market').textContent,'KRW-ETH');
  assert.equal(node('metric-latest').textContent,'—');
  assert.equal(vm.runInContext('state.records.length',context),0);
});

test('successful save followed by refresh failure shows an error outside the closed form', async () => {
  const {node,context}=harness(async (url,options)=> {
    if(url.endsWith('/api/data') && options.method === 'POST') return {ok:true,status:201,json:async()=>({id:'saved'})};
    throw new TypeError('unreachable');
  });
  const values={value:'100',open:'95',high:'105',low:'90',volume:'10',memo:'test'};
  node('record-form').elements={namedItem:(name)=>({value:values[name]})};
  node('record-date').value='2025-01-01';
  node('record-dialog').open=true;
  node('feedback').hidden=true;
  await node('record-form').handlers.get('submit')({preventDefault(){}});
  assert.equal(node('record-dialog').open,false);
  assert.equal(node('feedback').hidden,false);
  assert.match(node('feedback').textContent,/저장은 완료/);
});
