'use strict';
const $=id=>document.getElementById(id),make=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
let bundle=structuredClone(RESSEMBLY_DEMO),result=null,selected=null,filter='all',notes=new Map();
const relationLabel={'observed-only-b':'Solo in B','observed-only-a':'Solo in A','observed-both':'Entrambe'};
function pairKey(){return $('run-a').value+'|'+$('run-b').value;}
function setup(){Ressembly.validate(bundle);$('target').textContent=bundle.target.name;$('run-count').textContent=String(bundle.runs.length).padStart(2,'0');$('runs').replaceChildren();
 for(const r of bundle.runs){const box=make('div',undefined,'run-card'+(r.capture.status==='partial'?' partial':'')),top=make('div',undefined,'run-top');top.append(make('strong',r.label),make('span',String(r.events.length).padStart(2,'0')));box.append(top,make('p',r.input_label+' · '+(r.capture.status==='partial'?'Parziale':'Completezza dichiarata')));$('runs').append(box);}
 for(const id of ['run-a','run-b']){$(id).replaceChildren();for(const r of bundle.runs){const o=make('option',r.label);o.value=r.id;$(id).append(o);}}
 $('run-a').value=bundle.runs[0].id;$('run-b').value=bundle.runs[1].id;
 const demo=bundle.provenance==='synthetic-demo';$('provenance').className='demo-banner'+(demo?'':' imported');$('provenance').textContent=demo?'ANTEPRIMA APP DESKTOP · Dati sintetici. Nessun processo collegato.':'OSSERVAZIONI IMPORTATE · Metadati dichiarati dall’esportatore, non verificati contro il binario.';
 selected=null;recompute();}
function recompute(){try{result=Ressembly.compare(bundle,$('run-a').value,$('run-b').value);$('error').hidden=true;$('export').disabled=false;
 $('only-b').textContent=result.rows.filter(r=>r.relation==='observed-only-b').length;$('shared').textContent=result.rows.filter(r=>r.relation==='observed-both').length;
 $('events').textContent=bundle.runs.find(r=>r.id===result.run_a).events.length+' / '+bundle.runs.find(r=>r.id===result.run_b).events.length;
 $('quality').className='quality'+(result.quality==='partial'?' partial':'');$('quality').textContent=result.quality==='partial'?'△ Acquisizione parziale: il confronto riguarda soltanto gli eventi disponibili. Nessuna conclusione sull’assenza di altre esecuzioni.':'● Stessa build e stesso ambito dichiarato. Completezza dichiarata dall’esportatore; nessuna inferenza causale.';
 if(!result.rows.some(r=>r.key===selected))selected=result.rows.find(r=>r.relation==='observed-only-b')?.key||result.rows[0]?.key;
 $('note').value=notes.get(pairKey())||'';updateNote();renderRows();renderDetail();
 }catch(e){result=null;$('error').hidden=false;$('error').textContent='Confronto non disponibile: '+e.message;$('export').disabled=true;$('functions').replaceChildren();$('detail').replaceChildren();for(const id of ['only-b','shared','events'])$(id).textContent='—';$('quality').textContent='Seleziona due osservazioni differenti e compatibili.';}}
function renderRows(){if(!result)return;const q=$('search').value.trim().toLowerCase();$('functions').replaceChildren();
 const rows=result.rows.filter(r=>(filter==='all'||filter==='b'&&r.relation==='observed-only-b'||filter==='both'&&r.relation==='observed-both')&&(!q||(r.name+' '+r.rva+' '+r.module).toLowerCase().includes(q)));
 for(const r of rows){const tr=make('tr');tr.className=selected===r.key?'selected':'';tr.tabIndex=0;tr.setAttribute('aria-label',r.name+' · '+relationLabel[r.relation]);const name=make('td',r.name);name.append(make('small',r.module+' + '+r.rva));tr.append(name,make('td',r.hits_a,'number'),make('td',r.hits_b,'number'));const status=make('td');status.append(make('span',relationLabel[r.relation],'pill '+(r.relation==='observed-only-b'?'only-b':r.relation==='observed-only-a'?'only-a':'')));tr.append(status);const choose=()=>{selected=r.key;renderRows();renderDetail();};tr.onclick=choose;tr.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose();}};$('functions').append(tr);}
 if(!rows.length){const tr=make('tr'),td=make('td','Nessuna funzione corrisponde al filtro.');td.colSpan=4;tr.append(td);$('functions').append(tr);}}
function renderDetail(){const box=$('detail');box.replaceChildren();const r=result?.rows.find(r=>r.key===selected);if(!r){box.append(make('p','Seleziona una funzione.','detail-note'));return;}
 box.append(make('h3',r.name));const location=make('div',undefined,'location');location.append(make('div',r.module),make('div','RVA '+r.rva),make('div','SHA-256 '+r.module_sha256.slice(0,14)+'…'));box.append(location,make('div','RIFERIMENTI AGLI EVENTI','detail-label'));
 const refs=[...r.refs_a.map(e=>({...e,side:'A'})),...r.refs_b.map(e=>({...e,side:'B'}))];
 for(const e of refs.slice(0,30)){const row=make('div',undefined,'evidence-item');row.append(make('span',e.side+' / evento #'+e.seq),make('span','thread '+e.thread_id));box.append(row);}
 if(refs.length>30)box.append(make('p','Primi 30 riferimenti visualizzati; tutti inclusi nell’esportazione.','detail-note'));
 box.append(make('div','COME INTERPRETARLA','detail-label'),make('p','Questa funzione è stata osservata '+r.hits_a+' volte in A e '+r.hits_b+' volte in B. Il confronto suggerisce dove indagare; non dimostra quale operazione la funzione realizzi.','detail-note'));
 if(r.names_disagree)box.append(make('p','I nomi differiscono tra le acquisizioni. L’identità è basata su hash del modulo e RVA.','detail-note'));}
function updateNote(){$('note-status').textContent=$('note').value.trim()?'Nota pronta per l’esportazione':'Nessuna nota';}
function download(name,value){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'})),a=make('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
for(const id of ['run-a','run-b'])$(id).onchange=recompute;
$('search').oninput=renderRows;
for(const btn of document.querySelectorAll('[data-filter]'))btn.onclick=()=>{filter=btn.dataset.filter;for(const b of document.querySelectorAll('[data-filter]'))b.classList.toggle('active',b===btn);renderRows();};
$('note').oninput=()=>{notes.set(pairKey(),$('note').value);updateNote();};
$('export').onclick=()=>{if(result)download('ressembly-observations.json',{...result,analyst_note:$('note').value,source_bundle:bundle});};
$('import-btn').onclick=()=>$('import-file').click();
$('import-file').onchange=async e=>{const f=e.target.files[0];if(!f)return;try{if(f.size>5*1024*1024)throw new Error('Il file supera il limite di 5 MB.');const next=JSON.parse(await f.text());Ressembly.validate(next);bundle=next;notes=new Map();setup();}catch(err){$('error').hidden=false;$('error').textContent='Importazione rifiutata: '+err.message;}finally{e.target.value='';}};
$('reset').onclick=()=>{bundle=structuredClone(RESSEMBLY_DEMO);notes=new Map();filter='all';$('search').value='';for(const b of document.querySelectorAll('[data-filter]'))b.classList.toggle('active',b.dataset.filter==='all');setup();};
setup();
