const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html = fs.readFileSync(0, 'utf8');
const start = html.indexOf('class AppBridge {');
const end = html.indexOf('async function loadBridgeModule()', start);
const AppBridge = vm.runInNewContext(html.slice(start, end) + '\nAppBridge');

(async () => {
    const sent = [];
    const transport = { start() {}, close() {}, send(message) { sent.push(message); } };
    const bridge = new AppBridge(null, {}, { serverResources: {} });
    const uri = 'notation://pages/Morley_1595_06_Lo_hear_another.mei/2';
    const resource = { contents: [{ uri, text: JSON.stringify({ svg: '<svg/>', page: 2 }) }] };
    bridge.onreadresource = async params => {
        assert.equal(params.uri, uri);
        return resource;
    };
    await bridge.connect(transport);
    await transport.onmessage({ jsonrpc: '2.0', id: 7, method: 'resources/read', params: { uri } });
    assert.equal(sent.length, 1, 'Replay bridge did not reply to pagination resource read');
    assert.equal(sent[0].id, 7);
    assert.equal(sent[0].result, resource);

    bridge.onreadresource = async () => { throw new Error('Page not found'); };
    await transport.onmessage({ jsonrpc: '2.0', id: 8, method: 'resources/read', params: { uri } });
    assert.equal(sent[1].error.message, 'Page not found');
})().catch(error => { console.error(error); process.exitCode = 1; });
