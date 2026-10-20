// Local transport for the existing board UI. The server injects this file;
// publishing board.html as a Claude Artifact needs no local files.
(function () {
  'use strict';
  var versions = new Map();
  var connection = document.createElement('p');
  connection.id = 'localConnection';
  connection.className = 'err';
  connection.setAttribute('role', 'status');
  connection.hidden = true;
  document.querySelector('header').appendChild(connection);
  async function request(body) {
    var response;
    try {
      response = await fetch('/api', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-Artiboard': '1'},
        body: JSON.stringify(body)
      });
    } catch (error) {
      connection.textContent = document.documentElement.lang === 'ko'
        ? '로컬 서버 연결이 끊겼습니다. 서버를 다시 실행한 뒤 저장 상태를 확인하세요.'
        : 'Local server disconnected. Restart it and check whether your changes were saved.';
      connection.hidden = false;
      throw {code: 'disconnected', message: connection.textContent};
    }
    connection.hidden = response.status < 500;
    if (!connection.hidden) connection.textContent = 'Local storage is unavailable. Check the server.';
    var result = await response.json();
    if (!response.ok) throw result;
    return result;
  }
  function snapshot(doc) {
    versions.set(doc.path, doc.version);
    return {id: doc.id, exists: doc.exists, version: doc.version, data: function () { return structuredClone(doc.data); }};
  }
  function subscribe(load, callback, onError) {
    var stopped = false, timer, previous;
    async function poll() {
      try {
        var value = await load();
        if (stopped) return;
        var serialized = JSON.stringify(value);
        if (serialized !== previous) {
          previous = serialized;
          callback(value.docs ? {docs: value.docs.map(snapshot)} : snapshot(value));
        }
      } catch (error) {
        if (!stopped && onError) onError(error);
      } finally {
        if (!stopped) timer = setTimeout(poll, 1000);
      }
    }
    poll();
    return function () { stopped = true; clearTimeout(timer); };
  }
  async function write(path, op, data, version) {
    // A document never read by this page is create-only, never an unconditional overwrite.
    var result = await request({action: 'batch', writes: [
      {path: path, op: op, data: data, if_version: version === undefined ? (versions.get(path) || 0) : version}
    ]});
    result.docs.forEach(snapshot);
  }
  function doc(path) {
    return {
      get: async function () { return snapshot(await request({action: 'get', path: path})); },
      onSnapshot: function (cb, err) { return subscribe(function () { return request({action: 'get', path: path}); }, cb, err); },
      update: function (data) { return write(path, 'update', data); },
      set: function (data) { return write(path, 'set', data); }
    };
  }
  function collection(path, options) {
    options = options || {limit: null};
    return {
      orderBy: function (field, direction) { return collection(path, Object.assign({}, options, {order_by: field, direction: direction || 'asc'})); },
      limit: function (count) { return collection(path, Object.assign({}, options, {limit: count})); },
      onSnapshot: function (cb, err) {
        return subscribe(function () { return request(Object.assign({action: 'query', collection: path}, options)); }, cb, err);
      }
    };
  }
  var db = {
    doc: doc, collection: collection,
    claim: async function (id, who, at) {
      var path = 'tasks/' + id;
      var task = await request({action: 'get', path: path});
      if (!task.exists || (task.data.status || 'todo') !== 'todo' || task.data.claimedBy
          || !Array.isArray(task.data.waitingOn) || task.data.waitingOn.length)
        throw {code: 'conflict', message: 'Task is no longer ready'};
      // Pin the version from this read, even if a polling callback runs before the write.
      return write(path, 'update', {status: 'doing', owner: who,
        claimedBy: {who: who, agent: false, at: at}, updatedAt: at}, task.version);
    }
  };
  window.artiboard = {storageKey: window.ARTIBOARD_STORAGE_KEY,
    use: async function (name) { return name === 'db' ? db : null; }};
})();
