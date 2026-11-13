/* Ressembly M0: offline function-entry observations. No debugger or target execution. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.Ressembly=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const HEX=/^[a-f0-9]{64}$/i, RVA=/^0x[0-9a-f]{1,16}$/i;
function fail(message){throw new Error(message);}
function text(v,name,max=256){if(typeof v!=='string'||!v.length||v.length>max)fail(name+': invalid string');return v;}
function uint(v,name){if(!Number.isSafeInteger(v)||v<0)fail(name+': invalid integer');return v;}
function digest(v,name){if(typeof v!=='string'||!HEX.test(v))fail(name+': invalid SHA-256');return v.toLowerCase();}
function validate(b){
 if(!b||typeof b!=='object'||b.schema_version!==1)fail('Unsupported schema_version');
 if(!['synthetic-demo','imported-observations'].includes(b.provenance))fail('Missing observation provenance');
 text(b.target?.name,'target.name');digest(b.target?.sha256,'target.sha256');
 if(!['x86_64','arm64'].includes(b.target.architecture))fail('Unsupported architecture');
 text(b.target.os,'target.os');
 if(!Array.isArray(b.runs)||b.runs.length<2||b.runs.length>20)fail('Expected 2–20 runs');
 const ids=new Set();let total=0;
 for(const r of b.runs){
  text(r.id,'run.id');if(ids.has(r.id))fail('Duplicate run ID');ids.add(r.id);
  text(r.label,'run.label');text(r.input_label,'run.input_label');digest(r.target_sha256,'run.target_sha256');
  if(r.capture?.mode!=='function-entry')fail('Only function-entry observations are supported');
  if(!['complete','partial'].includes(r.capture.status))fail('Invalid capture status');
  text(r.capture.scope_id,'capture.scope_id');uint(r.capture.dropped_events,'capture.dropped_events');
  if(r.capture.status==='complete'&&r.capture.dropped_events!==0)fail('Complete capture cannot contain dropped events');
  if(!Array.isArray(r.modules)||!r.modules.length||r.modules.length>256)fail('Invalid modules');
  const mods=new Map();for(const m of r.modules){text(m.id,'module.id');text(m.name,'module.name');digest(m.sha256,'module.sha256');if(mods.has(m.id))fail('Duplicate module ID');mods.set(m.id,m);}
  if(!Array.isArray(r.events))fail('Missing events');total+=r.events.length;if(total>50000)fail('M0 limit: 50000 events per bundle');
  let previous=-1;
  for(const e of r.events){uint(e.seq,'event.seq');if(e.seq<=previous)fail('Events require increasing capture sequence');previous=e.seq;
   uint(e.thread_id,'event.thread_id');if(e.kind!=='function_entry')fail('Unsupported event kind');
   if(!mods.has(e.module_id))fail('Event references unknown module');
   if(typeof e.rva!=='string'||!RVA.test(e.rva))fail('Invalid 64-bit RVA');text(e.function,'event.function');
  }
 }
 return b;
}
function normalizeRva(rva){return '0x'+BigInt(rva).toString(16);}
function summarize(run){const mods=new Map(run.modules.map(m=>[m.id,m]));const out=new Map();
 for(const e of run.events){const m=mods.get(e.module_id),rva=normalizeRva(e.rva),key=m.sha256.toLowerCase()+':'+rva;
  if(!out.has(key))out.set(key,{key,module:m.name,module_sha256:m.sha256.toLowerCase(),rva,name:e.function,hits:0,event_refs:[],threads:[]});
  const row=out.get(key);row.hits++;row.event_refs.push({run_id:run.id,seq:e.seq,thread_id:e.thread_id});if(!row.threads.includes(e.thread_id))row.threads.push(e.thread_id);
 }return out;
}
function compare(bundle,aId,bId){validate(bundle);if(aId===bId)fail('Choose two different runs');
 const a=bundle.runs.find(r=>r.id===aId),b=bundle.runs.find(r=>r.id===bId);if(!a||!b)fail('Unknown run');
 if(a.target_sha256.toLowerCase()!==b.target_sha256.toLowerCase()||a.target_sha256.toLowerCase()!==bundle.target.sha256.toLowerCase())fail('Build identity differs: cross-build matching is outside M0');
 if(a.capture.scope_id!==b.capture.scope_id)fail('Capture scopes differ');
 const aa=summarize(a),bb=summarize(b);const rows=[];
 for(const key of new Set([...aa.keys(),...bb.keys()])){const left=aa.get(key),right=bb.get(key),v=right||left;
  rows.push({...v,hits_a:left?.hits||0,hits_b:right?.hits||0,refs_a:left?.event_refs||[],refs_b:right?.event_refs||[],relation:!left?'observed-only-b':!right?'observed-only-a':'observed-both',names_disagree:!!left&&!!right&&left.name!==right.name});
 }
 rows.sort((x,y)=>({ 'observed-only-b':0,'observed-only-a':1,'observed-both':2}[x.relation]-{'observed-only-b':0,'observed-only-a':1,'observed-both':2}[y.relation])||x.module.localeCompare(y.module)|| (BigInt(x.rva)<BigInt(y.rva)?-1:BigInt(x.rva)>BigInt(y.rva)?1:0));
 const partial=[a,b].some(r=>r.capture.status!=='complete'||r.capture.dropped_events>0);
 return {schema_version:1,provenance:bundle.provenance,target:bundle.target,run_a:a.id,run_b:b.id,quality:partial?'partial':'declared-complete',limitations:['Counts describe captured function entries, not instructions or call durations.','Not observed is not proof of non-execution.','Metadata and completeness are exporter declarations, not independent attestations.','Differences do not establish causation or reconstruct a call tree.','M0 compares one build and one declared capture scope.'],rows};
}
return {validate,compare,normalizeRva};
});
