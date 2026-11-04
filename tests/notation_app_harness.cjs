// Execute the shipped widget script with a small DOM and MCP host substitute.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const [templatePath, scenario] = process.argv.slice(2);
const html = fs.readFileSync(templatePath, 'utf8');
const script = html.match(/<script type="module">([\s\S]*?)<\/script>/)[1]
    .replace(/import \{ App \} from [^;]+;/, '');
const elements = new Map();
function element(id) {
    if (!elements.has(id)) elements.set(id, {
        textContent: '', innerHTML: '', disabled: false,
        classList: { add() {}, remove() {}, toggle() {} },
        querySelector() { return { classList: { add() {} } }; },
        addEventListener(event, handler) { this[event] = handler; },
    });
    return elements.get(id);
}

const sessionId = 'test-notation-session';
const filename = 'Morley_1595_06_Lo_hear_another.mei';
const calls = [];
let app;
class App {
    constructor() { app = this; }
    async connect() {}
    async callServerTool() {
        throw new Error('Pagination must read a resource, not call a tool');
    }
    async readServerResource({ uri }) {
        calls.push(uri);
        assert.ok(!uri.includes('session'));
        const parsed = new URL(uri);
        assert.equal(parsed.protocol, 'notation:');
        assert.equal(parsed.hostname, 'pages');
        assert.equal(parsed.searchParams.get('start_measure'), '1');
        assert.equal(parsed.searchParams.get('end_measure'), '8');
        if (scenario === 'error') throw new Error('Page resource unavailable');
        const page = Number(parsed.pathname.split('/').pop());
        return { contents: [{ uri, text: JSON.stringify({
            filename, page, svg: `<svg>page ${page}</svg>`, total_pages: 10,
            start_measure: 1, end_measure: 8,
        }) }] };
    }
}

(async () => {
    await vm.runInNewContext('(async () => {' + script + '})()', {
        App, document: { getElementById: element }, console, URLSearchParams,
        CSS: { escape: value => value },
    });
    app.ontoolinput({ arguments: { filename, session_id: sessionId } });
    app.ontoolresult({ structuredContent: {
        filename, svg: '<svg>page 1</svg>', page: 1, total_pages: 10,
        start_measure: 1, end_measure: 8,
        highlight_note_ids: ['note-1'],
    } });
    element('next-btn').click();
    await new Promise(resolve => setImmediate(resolve));
    if (scenario === 'error') {
        assert.match(element('status').textContent, /Page resource unavailable/);
        assert.equal(element('notation').innerHTML, '<svg>page 1</svg>');
    } else {
        assert.equal(element('notation').innerHTML, '<svg>page 2</svg>', element('status').textContent);
        assert.ok(calls[0].includes(encodeURIComponent(filename)));
        element('prev-btn').click();
        await new Promise(resolve => setImmediate(resolve));
        assert.equal(element('notation').innerHTML, '<svg>page 1</svg>');
        assert.equal(calls.length, 2);
        if (templatePath.includes('highlight')) {
            assert.equal(element('highlight-summary').textContent, 'Highlighted 1 note');
        }
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
