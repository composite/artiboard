// Real local server + transport + existing board. Run after installing jsdom@24.1.1.
const assert = require('node:assert/strict');
const {spawn, spawnSync} = require('node:child_process');
const {mkdtempSync, rmSync} = require('node:fs');
const {tmpdir} = require('node:os');
const path = require('node:path');
const {once} = require('node:events');
const {JSDOM, VirtualConsole} = require('jsdom');
const dir = mkdtempSync(path.join(tmpdir(), 'artiboard-'));
const db = path.join(dir, 'board.sqlite3');
const script = path.resolve(__dirname, '../skills/artiboard/scripts/local_board.py');
const python = process.env.PYTHON || 'python3';
let server, windows = [];
const errors = [];
function cli(...args) {
  const r = spawnSync(python, [script, '--db', db, ...args], {encoding: 'utf8'});
  assert.equal(r.status, 0, r.stderr);
  return r.stdout;
}
function request(req) {
  const r = spawnSync(python, [script, '--db', db, 'request'], {input: JSON.stringify(req), encoding: 'utf8'});
  assert.equal(r.status, 0, r.stderr);
  return JSON.parse(r.stdout);
}
const get = p => request({action: 'get', path: p});
async function until(check, message) {
  const end = Date.now() + 6000;
  while (Date.now() < end) {
    if (check()) return;
    await new Promise(r => setTimeout(r, 40));
  }
  throw new Error(message);
}
async function start() {
  server = spawn(python, [script, '--db', db, 'serve', '--port', '0'], {stdio: ['ignore', 'pipe', 'pipe']});
  const [line] = await once(server.stdout, 'data');
  return line.toString().trim();
}
async function stop() {
  const exited = once(server, 'exit');
  server.kill('SIGINT');
  await exited;
}
async function browser(url) {
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => errors.push(e.message));
  const dom = await JSDOM.fromURL(url, {
    runScripts: 'dangerously', resources: 'usable', pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) {
      w.fetch = (p, options) => fetch(new URL(p, url), options);
      w.structuredClone = structuredClone;
      w.HTMLElement.prototype.scrollIntoView = () => {};
    }
  });
  windows.push(dom.window);
  await until(() => dom.window.document.querySelectorAll('tr.item').length === 2, 'board did not load');
  return dom.window;
}
(async () => {
  cli('init', '--title', 'Local test', '--person', 'ana', '--person', 'ben');
  request({action: 'batch', writes: [
    {op: 'set', path: 'tasks/A', if_version: 0, data: {key: 'M1-1', title: 'First task', status: 'todo', deps: []}},
    {op: 'set', path: 'tasks/B', if_version: 0, data: {key: 'M1-2', title: 'Dependent task', status: 'todo', deps: ['M1-1']}},
    {op: 'set', path: 'details/A', if_version: 0, data: {summary: '', acceptance: 'Verified'}}
  ]});
  let url = await start();
  const a = await browser(url), b = await browser(url);
  const da = a.document;
  assert.equal(da.getElementById('hTitle').textContent, 'Local test');
  const dba = await a.artiboard.use('db'), dbb = await b.artiboard.use('db');
  // Hold both claim reads until both clients have observed the same version.
  const originalA = a.fetch, originalB = b.fetch;
  let readers = 0, release;
  const bothRead = new Promise(r => { release = r; });
  for (const [w, original] of [[a, originalA], [b, originalB]]) {
    w.fetch = async (p, options) => {
      const body = JSON.parse(options.body);
      const result = await original(p, options);
      if (body.action === 'get' && body.path === 'tasks/A') {
        if (++readers === 2) release();
        await bothRead;
      }
      return result;
    };
  }
  const claims = await Promise.allSettled([
    dba.claim('A', 'ana', new Date().toISOString()), dbb.claim('A', 'ben', new Date().toISOString())
  ]);
  a.fetch = originalA; b.fetch = originalB;
  assert.equal(claims.filter(r => r.status === 'fulfilled').length, 1);
  assert.equal(claims.find(r => r.status === 'rejected').reason.code, 'conflict');
  await until(() => da.querySelector('tr.item .state.doing'), 'claim did not reach the page');
  da.querySelector('[data-view="kanban"]').click();
  assert.equal(da.querySelectorAll('.card').length, 2);
  da.querySelector('[data-view="graph"]').click();
  assert.equal(da.querySelectorAll('.node').length, 2);
  da.querySelector('[data-view="doc"]').click();
  da.querySelector('tr.item').click();
  await until(() => da.querySelector('.sheet'), 'detail did not open');
  da.getElementById('fStatus').value = 'done';
  da.getElementById('fStatus').dispatchEvent(new a.Event('change'));
  await until(() => get('tasks/A').data.status === 'done', 'status write did not persist');
  assert.deepEqual(get('tasks/B').data.waitingOn, []);
  await until(() => da.getElementById('msgText'), 'composer unavailable');
  da.getElementById('msgText').value = 'Persisted browser message';
  da.querySelector('.composer .btn.primary').click();
  await until(() => request({action: 'query', collection: 'tasks/A/messages'}).docs.length === 1, 'message not saved');
  da.dispatchEvent(new a.KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
  await until(() => da.querySelector('.pick .btn.primary'), 'dependent task was not offered');
  da.querySelector('.pick .btn.primary').click();
  await until(() => get('tasks/B').data.status === 'doing', 'UI claim did not persist');
  await until(() => da.getElementById('newBtn').disabled, 'own UI claim should not be marked new');
  // No heal loop: after snapshots settle, waitingOn stays correct without extra writes.
  await new Promise(r => setTimeout(r, 3500));
  const stable = get('tasks/B').version;
  await new Promise(r => setTimeout(r, 1500));
  assert.equal(get('tasks/B').version, stable);
  await stop();
  await until(() => !da.getElementById('localConnection').hidden, 'disconnect was not visible');
  for (const w of windows) w.close();
  windows = [];
  url = await start();
  const resumed = await browser(url);
  assert.equal(get('tasks/A').data.status, 'done');
  resumed.document.querySelector('tr.item').click();
  await until(() => resumed.document.querySelector('.msgs').textContent.includes('Persisted browser message'), 'thread missing after restart');
  assert.deepEqual(errors, []);
  console.log('ok: local views, two-client claim conflict, writes, readiness, disconnect and restart');
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  for (const w of windows) w.close();
  if (server && server.exitCode === null) await stop();
  rmSync(dir, {recursive: true, force: true});
});
