/* Local evidence presentation only. No authenticity or exploitability verdict. */
(function (global) {
  'use strict';
  const LIMITS = Object.freeze({bytes: 1048576, depth: 32, nodes: 20000, rows: 200});
  const SCHEMAS = Object.freeze({
    'ressembly.debug-context.v1': ['Debug context', 'debug'],
    'ressembly.lldb-context.v1': ['LLDB context · macOS / Mach-O', 'lldb-debug'],
    'ressembly.lldb-memory.v1': ['LLDB memory · macOS / Mach-O', 'lldb-memory'],
    'ressembly.process-diagnostics.v1': ['Process and thread diagnostics', 'process'],
    'ressembly.allocator-summary.v1': ['Allocator statistics', 'allocator'],
    'ressembly.ghidra-review.v1': ['Ghidra review selection', 'ghidra-review'],
    'ressembly.experiment.v1': ['Experiment dossier', 'experiment'],
    'ressembly.object-history.v1': ['Object history · API 1', 'history'],
    'ressembly.object-history.v2': ['Object history · API 2', 'history'],
    'ressembly.marker-history.v1': ['Historical marker capture', 'history'],
    'ressembly.heap-structure.v1': ['Heap structure', 'heap'],
    'ressembly.plugin-annotations.v1': ['Plugin annotations', 'plugin'],
    'ressembly.plugin-analysis.v2': ['Plugin analysis', 'plugin'],
    'ressembly.step-observations.v1': ['Instruction-stop samples', 'steps'],
    'ressembly.memory-maps.v1': ['Memory maps', 'maps'],
    'ressembly.memory-dump.v1': ['Memory dump', 'memory'],
    'ressembly.memory-search.v1': ['Memory search', 'memory'],
    'ressembly.pointer-chain.v1': ['Pointer chain', 'memory']
  });
  function requireValue(value, message) { if (!value) throw new Error(message); }
  function object(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
  function plain(value) {
    const text = typeof value === 'string' ? value : value === undefined ? '—' : JSON.stringify(value);
    return text.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u202a-\u202e\u2066-\u2069]/g,
      c => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0'));
  }
  function compact(value) { const text = plain(value); return text.length > 600 ? text.slice(0, 600) + '… [see original JSON]' : text; }

  // Parsing here preserves large integer lexemes and rejects duplicate keys before display.
  function decode(raw) {
    requireValue(typeof raw === 'string', 'Input must be JSON text.');
    requireValue(new TextEncoder().encode(raw).length <= LIMITS.bytes, 'Input exceeds the 1 MiB viewer limit.');
    let offset = 0, nodes = 0, largeIntegers = 0;
    function whitespace() { while (/[ \n\r\t]/.test(raw[offset] || '') && offset < raw.length) offset++; }
    function string() {
      const start = offset++;
      while (offset < raw.length) {
        const ch = raw[offset++];
        if (ch === '\\') offset++;
        else if (ch === '"') return JSON.parse(raw.slice(start, offset));
      }
      throw new Error('Unterminated JSON string.');
    }
    function value(depth) {
      requireValue(depth <= LIMITS.depth && ++nodes <= LIMITS.nodes, 'JSON exceeds the depth or node limit.');
      whitespace();
      const ch = raw[offset];
      if (ch === '"') return string();
      if (ch === '{' || ch === '[') {
        const isObject = ch === '{', result = isObject ? Object.create(null) : [], end = isObject ? '}' : ']';
        offset++; whitespace();
        if (raw[offset] === end) { offset++; return result; }
        while (offset < raw.length) {
          whitespace();
          if (isObject) {
            requireValue(raw[offset] === '"', 'Object keys must be JSON strings.');
            const key = string();
            requireValue(!Object.prototype.hasOwnProperty.call(result, key), 'Duplicate JSON key.');
            whitespace(); requireValue(raw[offset++] === ':', 'Missing JSON colon.');
            result[key] = value(depth + 1);
          } else result.push(value(depth + 1));
          whitespace();
          const separator = raw[offset++];
          if (separator === end) return result;
          requireValue(separator === ',', 'Invalid JSON collection separator.');
        }
        throw new Error('Unterminated JSON collection.');
      }
      for (const [token, result] of [['true', true], ['false', false], ['null', null]]) {
        if (raw.slice(offset, offset + token.length) === token) { offset += token.length; return result; }
      }
      const match = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/.exec(raw.slice(offset));
      requireValue(match, 'Invalid JSON value.');
      offset += match[0].length;
      const number = Number(match[0]);
      requireValue(Number.isFinite(number), 'Nonfinite numbers are not accepted.');
      if (Number.isInteger(number) && !Number.isSafeInteger(number)) { largeIntegers++; return match[0]; }
      return number;
    }
    const data = value(0);
    whitespace(); requireValue(offset === raw.length, 'Unexpected text after JSON value.');
    return {data, largeIntegers, nodes};
  }

  function shape(data) {
    requireValue(object(data) && typeof data.schema === 'string' && Object.hasOwn(SCHEMAS, data.schema),
      'Unsupported document schema. Import an exported Ressembly JSON document.');
    const kind = SCHEMAS[data.schema][1];
    const needs = kind === 'debug' ? {metadata:'object', registers:'object'} :
      kind === 'lldb-debug' ? {metadata:'object', registers:'object', assembly:'array'} :
      kind === 'lldb-memory' ? {metadata:'object'} :
      kind === 'experiment' ? {build:'object', snapshots:'array', inputs:'array', notes:'array'} :
      kind === 'process' ? {metadata:'object', processes:'array', children:'array'} :
      kind === 'allocator' ? {metadata:'object', bytes:'object', unavailable:'array'} :
      kind === 'history' ? {metadata:'object', objects:'object', events:'array'} :
      kind === 'steps' ? {identity:'object', regions:'array', baseline:'array', changes:'array'} :
      kind === 'plugin' ? {plugin:'object', annotations:'array'} : kind === 'maps' ? {regions:'array'} : {};
    for (const [key, type] of Object.entries(needs)) requireValue(type === 'array' ? Array.isArray(data[key]) : object(data[key]),
      'Invalid document structure: ' + key + '.');
    if (kind === 'process') {
      const ids = new Set();
      requireValue(data.processes.length > 0 && data.processes.length <= 32, 'Invalid process count.');
      for (const p of data.processes) {
        requireValue(object(p) && /^[a-f0-9]{32}$/.test(p.id) && !ids.has(p.id) &&
          typeof p.label === 'string' && Number.isSafeInteger(p.pid) && p.pid > 0 &&
          Array.isArray(p.events) && p.events.length <= 128 && p.events.every((e, i) =>
            object(e) && e.sequence === i + 1 && typeof e.kind === 'string' && typeof e.label === 'string'),
          'Invalid process diagnostics record.');
        ids.add(p.id);
      }
      requireValue(data.processes.every(p => p.parent_id === null || ids.has(p.parent_id) && p.parent_id !== p.id) &&
        data.children.length <= data.processes.length && data.children.every(child =>
          object(child) && ids.has(child.id) && Number.isSafeInteger(child.exit_code)), 'Invalid process linkage.');
    }
    if (kind === 'allocator') {
      const metrics = ['allocated', 'active', 'metadata', 'resident', 'mapped', 'retained'];
      const validCount = value => Number.isSafeInteger(value) && value >= 0 ||
        typeof value === 'string' && /^[0-9]{1,20}$/.test(value) && BigInt(value) < (1n << 64n);
      requireValue(data.metadata.allocator === 'jemalloc' && Object.hasOwn(data.bytes, 'allocated') &&
        Object.entries(data.bytes).every(([name, count]) => metrics.includes(name) && validCount(count)) &&
        data.unavailable.every(name => metrics.includes(name) && !Object.hasOwn(data.bytes, name)),
        'Invalid aggregate allocator statistics.');
    }
    if (kind === 'ghidra-review') requireValue(
      Object.keys(data).length === 5 && typeof data.executable_sha256 === 'string' &&
      /^[0-9a-f]{64}$/.test(data.executable_sha256) &&
      ['program', 'language', 'function'].every(k => typeof data[k] === 'string' &&
        data[k].trim() && data[k].length <= 512 && !/[\u0000-\u001f\u007f-\u009f]/.test(data[k])),
      'Invalid Ghidra review selection.');
    if (kind.startsWith('lldb-')) requireValue(data.metadata.backend === 'lldb' && data.metadata.binary_format === 'Mach-O',
      'LLDB document requires its declared backend and Mach-O metadata.');
    if (kind === 'lldb-debug') requireValue(data.assembly.every(item => object(item) &&
      ['number','string'].includes(typeof item.address) && typeof item.mnemonic === 'string' && typeof item.operands === 'string'),
      'Invalid LLDB instruction structure.');
    if (kind === 'lldb-memory') requireValue(['number','string'].includes(typeof data.address) &&
      Number.isInteger(data.length) && data.length >= 1 && data.length <= 4096 && typeof data.hex === 'string' &&
      /^[0-9a-f]+$/.test(data.hex) && data.hex.length === data.length * 2, 'Invalid LLDB memory structure.');
    for (const name of ['events', 'snapshots', 'inputs', 'notes', 'annotations', 'changes', 'regions', 'breakpoints']) {
      if (data[name] !== undefined) requireValue(Array.isArray(data[name]) && data[name].every(object),
        'Invalid record list: ' + name + '.');
    }
    if (data.schema === 'ressembly.plugin-analysis.v2') requireValue(Array.isArray(data.tables), 'Missing API 2 tables.');
    if (data.tables !== undefined) {
      requireValue(Array.isArray(data.tables) && data.tables.length <= 8, 'Invalid plugin tables.');
      for (const table of data.tables) requireValue(object(table) && typeof table.title === 'string' &&
        Array.isArray(table.columns) && table.columns.length >= 1 && table.columns.length <= 16 && table.columns.every(c => typeof c === 'string') &&
        Array.isArray(table.rows) && table.rows.every(row => Array.isArray(row) && row.length === table.columns.length &&
          row.every(cell => cell === null || ['string', 'number', 'boolean'].includes(typeof cell))), 'Invalid plugin table structure.');
    }
    return kind;
  }

  function eventCategory(event, schema) {
    if (schema === 'ressembly.marker-history.v1') return 'Target marker declaration';
    if (event.kind === 'value_change') return 'Observed value difference';
    if (/^(allocation|free_|unmatched_free|realloc_)/.test(event.kind || '')) return 'Allocator operation';
    return 'Collection / coverage event';
  }
  function describe(data, selectedProcess = null) {
    const kind = shape(data), sections = [];
    function table(title, columns, rows) {
      sections.push({title, columns, rows: rows.slice(0, LIMITS.rows).map(row => row.map(compact)), omitted: Math.max(0, rows.length - LIMITS.rows)});
    }
    function fields(title, data) { if (object(data)) table(title, ['Field', 'Supplied value'], Object.entries(data)); }
    function records(title, collection, columns) {
      if (Array.isArray(collection)) table(title, columns, collection.map((item, index) => columns.map(key => key === '#' ? index + 1 : item[key])));
    }
    const metadata = data.metadata || data.identity || data.plugin || data.build || {};
    const summary = [['Schema', data.schema], ['Record identity', data.snapshot_id || data.observation_id || data.id || 'Not supplied'],
      ['Backend', metadata.backend || 'Not supplied'], ['Architecture', metadata.architecture || 'Not supplied'],
      ['Binary format', metadata.binary_format || 'Not supplied'],
      ['Claimed status', data.status || metadata.acquisition_status || 'Not supplied'],
      ['Run identity', metadata.run_id || data.run_id || 'Not supplied'],
      ['Binary SHA-256', metadata.executable_sha256 || metadata.target_sha256 || data.executable_sha256 ||
        data.build?.sha256 || 'Not supplied'],
      ['Coverage / limits', data.coverage || data.limits || data.evidence_status || 'Not supplied']].map(row => row.map(compact));
    fields('Supplied metadata', metadata);
    if (kind === 'debug' || kind === 'lldb-debug') {
      fields('Registers', data.registers);
      if (kind === 'lldb-debug') records('LLDB assembly', data.assembly, ['address', 'mnemonic', 'operands']);
      else records('Assembly', data.assembly?.instructions, ['addr', 'asm']);
      if (Array.isArray(data.stack?.words)) table('Stack words', ['Index', 'Value'], data.stack.words.map((word, i) => [i, word]));
      records('Breakpoints', data.breakpoints, ['number', 'location', 'enabled', 'hit_count']);
      fields('Collection errors', data.errors);
    } else if (kind === 'lldb-memory') {
      fields('Selected stopped memory', {address:data.address, length:data.length, hex:data.hex, coverage:data.coverage});
    } else if (kind === 'experiment') {
      table('Snapshots', ['Label', 'Schema', 'Run', 'Claimed provenance'], data.snapshots.map(r => [r.label, r.payload?.schema, r.run_id, r.provenance]));
      records('Recorded inputs — not proof of consumption', data.inputs, ['label', 'size', 'sha256', 'status']);
      records('Analyst notes', data.notes, ['text', 'snapshot_id', 'created']);
    } else if (kind === 'process') {
      if (selectedProcess) {
        const {events, ...identity} = selectedProcess;
        fields('Process identity', identity);
        records('Application declarations in process order', events,
          ['sequence', 'elapsed_ns', 'kind', 'label', 'os_thread_id', 'thread_id']);
      } else {
        records('Processes', data.processes, ['label', 'id', 'parent_id', 'pid']);
        records('Child exit status', data.children, ['id', 'pid', 'exit_code']);
      }
    } else if (kind === 'allocator') {
      table('Aggregate byte counts', ['Metric', 'Bytes'], Object.entries(data.bytes));
      fields('Unavailable metrics', {metrics: data.unavailable});
    } else if (kind === 'ghidra-review') {
      fields('Static selection', {program: data.program, language: data.language, function: data.function});
    } else if (kind === 'history') {
      table('Events', ['Sequence', 'Kind', 'Classification', 'Object', 'Address', 'Details'], data.events.map(e =>
        [e.sequence, e.kind, eventCategory(e, data.schema), e.object_id, e.address, e]));
      table('Object generations', ['Object identity', 'Supplied state'], Object.entries(data.objects));
    } else if (kind === 'steps') {
      records('Selected regions', data.regions, ['#', 'address', 'length']);
      records('Differences between stops — not a write log', data.changes,
        ['step_command', 'previous_stop_pc', 'stop_pc', 'regions', 'evidence']);
      fields('Termination', {reason: data.termination, detail: data.termination_detail, step_commands: data.step_commands_completed});
      records('Collection errors', data.errors, ['step_command', 'reason', 'regions']);
    } else if (kind === 'plugin') {
      records('Plugin annotations — not debugger observations', data.annotations, ['message', 'address']);
      for (const item of data.tables || []) table(item.title, item.columns, item.rows);
    } else if (kind === 'maps') records('Memory maps', data.regions, ['start', 'end', 'permissions', 'path']);
    else fields('Supplied fields', data);
    const diagnosticsSemantics = {
      process: 'Application declarations are ordered separately per process. Exit status is supplied by the demo supervisor.',
      allocator: 'Aggregate statistics summarize one sample. Thread caches can delay updates.',
      'ghidra-review': 'Static program selection by build hash and qualified function name.'
    };
    return {title: selectedProcess ? selectedProcess.label : SCHEMAS[data.schema][0], kind, summary, sections,
      notice: 'Imported JSON is supplied evidence. Its metadata and provenance claims have not been authenticated by this viewer.',
      semantics: diagnosticsSemantics[kind] ||
        'Allocator operations and observed value changes are different evidence. Missing events do not prove absence of writes; no single signal establishes exploitability.'};
  }
  function parse(raw) {
    const decoded = decode(raw);
    const views = [{label: 'Document overview', data: decoded.data, view: describe(decoded.data)}];
    if (decoded.data.schema === 'ressembly.experiment.v1') {
      for (const record of decoded.data.snapshots) {
        if (object(record.payload) && Object.hasOwn(SCHEMAS, record.payload.schema)) views.push({
          label: compact(record.label || record.id || 'Snapshot'), data: record.payload, view: describe(record.payload)});
      }
    } else if (decoded.data.schema === 'ressembly.process-diagnostics.v1') {
      for (const process of decoded.data.processes) {
        views.push({label: compact(process.label + ' (PID ' + process.pid + ')'),
          data: process, view: describe(decoded.data, process)});
      }
    }
    return {...decoded, raw, views};
  }
  const api = {LIMITS, SCHEMAS, decode, parse, describe, plain, eventCategory};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else global.RessemblyViewer = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
