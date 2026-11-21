/* DOM values are text only. No network, evaluation, persistent storage or target control. */
(function () {
  'use strict';
  const model = window.RessemblyViewer;
  const byId = id => document.getElementById(id);
  const recordSelect = byId('record-select');
  const previousView = byId('record-previous');
  const nextView = byId('record-next');
  let current = null, importGeneration = 0;
  function message(text, error = false) {
    byId('feedback').textContent = text;
    byId('feedback').classList.toggle('error', error);
  }
  function make(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = model.plain(text);
    if (className) element.className = className;
    return element;
  }
  function table(columns, rows, caption) {
    const wrap = make('div', undefined, 'table-wrap');
    wrap.tabIndex = 0; wrap.setAttribute('role', 'region'); wrap.setAttribute('aria-label', caption);
    const element = make('table'), head = make('thead'), header = make('tr'), body = make('tbody');
    for (const value of columns) { const th = make('th', value); th.scope = 'col'; header.append(th); }
    head.append(header);
    for (const row of rows) { const tr = make('tr'); for (const value of row) tr.append(make('td', value)); body.append(tr); }
    if (!rows.length) { const tr = make('tr'), td = make('td', 'No records supplied.'); td.colSpan = columns.length; tr.append(td); body.append(tr); }
    element.append(head, body); wrap.append(element); return wrap;
  }
  function activate(name, focus = false) {
    for (const button of document.querySelectorAll('[role="tab"]')) {
      const selected = button.dataset.panel === name;
      button.setAttribute('aria-selected', String(selected)); button.tabIndex = selected ? 0 : -1;
      byId('panel-' + button.dataset.panel).hidden = !selected;
      if (selected && focus) button.focus();
    }
  }
  function render(index) {
    const selected = current.views[index];
    const count = current.views.length;
    recordSelect.value = String(index);
    byId('record-navigation').hidden = count < 2;
    previousView.disabled = index === 0;
    nextView.disabled = index === count - 1;
    byId('record-position').textContent = 'View ' + (index + 1) + ' of ' + count;
    byId('document-title').textContent = selected.view.title;
    byId('integrity-notice').textContent = selected.view.notice;
    byId('semantics').textContent = selected.view.semantics;
    byId('summary').replaceChildren(table(['Field', 'Supplied value'], selected.view.summary, 'Evidence overview'));
    const blocks = [];
    for (const section of selected.view.sections) {
      const block = make('section', undefined, 'section-block');
      block.append(make('h3', section.title), table(section.columns, section.rows, section.title));
      if (section.omitted) block.append(make('p', section.omitted + ' further rows are available in Original JSON.', 'omitted'));
      blocks.push(block);
    }
    byId('records').replaceChildren(...blocks);
  }
  function load(raw, source) {
    const parsed = model.parse(raw);
    current = parsed;
    recordSelect.replaceChildren(...parsed.views.map((view, index) => {
      const option = make('option', view.label); option.value = String(index); return option;
    }));
    byId('source-name').textContent = model.plain(source);
    byId('raw-json').textContent = raw;
    byId('precision-notice').hidden = parsed.largeIntegers === 0;
    byId('precision-notice').textContent = parsed.largeIntegers + ' large number(s) preserved as exact source text to avoid JavaScript integer rounding.';
    render(0); activate('summary');
    byId('empty').hidden = true; byId('document').hidden = false; byId('clear').disabled = false;
    message('Document opened locally. Origin and authenticity remain unverified.');
    byId('document-title').focus();
  }
  byId('file-input').addEventListener('change', async () => {
    const generation = ++importGeneration;
    const file = byId('file-input').files[0]; if (!file) return;
    try {
      if (file.size > model.LIMITS.bytes) throw new Error('File exceeds the 1 MiB viewer limit.');
      const raw = new TextDecoder('utf-8', {fatal: true}).decode(await file.arrayBuffer());
      if (generation !== importGeneration) return;
      load(raw, file.name);
    } catch (error) { if (generation === importGeneration) message(error.message + ' Previous evidence, if any, is unchanged.', true); }
  });
  byId('import-text').addEventListener('click', () => {
    importGeneration++;
    try { load(byId('json-input').value, 'Pasted JSON'); }
    catch (error) { message(error.message + ' Previous evidence, if any, is unchanged.', true); }
  });
  recordSelect.addEventListener('change', () => render(Number(recordSelect.value)));
  function moveView(offset, control) {
    if (!current) return;
    const index = Number(recordSelect.value) + offset;
    if (index < 0 || index >= current.views.length) return;
    render(index);
    if (control.disabled) recordSelect.focus();
  }
  previousView.addEventListener('click', () => moveView(-1, previousView));
  nextView.addEventListener('click', () => moveView(1, nextView));
  byId('clear').addEventListener('click', () => {
    importGeneration++; current = null;
    for (const id of ['raw-json', 'summary', 'records', 'record-select', 'source-name',
      'document-title', 'integrity-notice', 'precision-notice', 'semantics', 'record-position']) byId(id).replaceChildren();
    byId('record-navigation').hidden = true;
    byId('json-input').value = ''; byId('file-input').value = '';
    byId('document').hidden = true; byId('empty').hidden = false; byId('clear').disabled = true;
    message('Evidence cleared from the viewer. No source file was changed.'); byId('file-input').focus();
  });
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  for (const [index, button] of tabs.entries()) {
    button.addEventListener('click', () => activate(button.dataset.panel));
    button.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      else if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = tabs.length - 1;
      else return;
      event.preventDefault(); activate(tabs[next].dataset.panel, true);
    });
  }
})();
