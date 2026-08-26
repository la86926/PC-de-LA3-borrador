from pathlib import Path
import re
import subprocess

FILES = [Path('index1.html'), Path('index2.html')]

BACKUP_ROW = r'''    <div class="actions pc-backup-actions" id="pc-backup-actions" style="justify-content:center">
      <button class="btn" id="b-backup-export" type="button"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M5 21h14"/></svg>Exportar copia</button>
      <button class="btn" id="b-backup-import" type="button"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21V9"/><path d="M7 14l5-5 5 5"/><path d="M5 3h14"/></svg>Importar copia</button>
      <input id="pc-backup-file" type="file" accept="application/json,.json" hidden>
    </div>'''

PRELOAD = r'''<script id="pc-backup-preload">
(function(){
  'use strict';
  var PREFIX='pc_backup_page_state_v2:';
  function fileName(){
    var p=location.pathname.split('/').pop()||'index1.html';
    try{return decodeURIComponent(p).toLowerCase();}catch(e){return p.toLowerCase();}
  }
  try{
    var f=fileName();
    if(f!=='index1.html' && f!=='index2.html') return;
    var raw=localStorage.getItem(PREFIX+f);
    if(!raw) return;
    var snap=JSON.parse(raw);
    if(snap && Number.isFinite(Number(snap.lastExercise)) && Number(snap.lastExercise)>0){
      localStorage.setItem('wp_ultimo',String(Number(snap.lastExercise)));
    }
  }catch(e){}
})();
</script>'''

SYSTEM = r'''<script id="pc-backup-system">
(function(){
'use strict';

const MAGIC='PC-de-LuisA3-backup';
const FORMAT_VERSION=2;
const PAGE_PREFIX='pc_backup_page_state_v2:';
const RESTORE_UI_KEY='__pc_backup_restore_ui_v2';
const RESTORE_NOTICE_KEY='__pc_backup_restore_notice_v2';
const VALID_PAGES=new Set(['index1.html','index2.html']);

function isAppKey(key){ return typeof key==='string' && (key.startsWith('wp_') || key.startsWith('pc_')); }
function currentFile(){
  const p=location.pathname.split('/').pop()||'index1.html';
  try{return decodeURIComponent(p).toLowerCase();}catch(e){return p.toLowerCase();}
}
function appDirectory(){
  const p=location.pathname;
  return p.slice(0,p.lastIndexOf('/')+1)||'/';
}
function plainObject(v){ return !!v && typeof v==='object' && !Array.isArray(v); }
function safeDecode(v){ try{return decodeURIComponent(v);}catch(e){return v;} }

function fnv1a(text){
  let h=0x811c9dc5;
  for(let i=0;i<text.length;i++){
    h^=text.charCodeAt(i);
    h=Math.imul(h,0x01000193);
  }
  return ('00000000'+(h>>>0).toString(16)).slice(-8);
}

function captureStorage(storage){
  const out=Object.create(null);
  try{
    for(let i=0;i<storage.length;i++){
      const k=storage.key(i);
      if(isAppKey(k)) out[k]=storage.getItem(k);
    }
  }catch(e){}
  return out;
}
function clearAppStorage(storage){
  const keys=[];
  for(let i=0;i<storage.length;i++){
    const k=storage.key(i);
    if(isAppKey(k)) keys.push(k);
  }
  keys.forEach(k=>storage.removeItem(k));
}
function writeStorage(storage,data){
  Object.entries(data||{}).forEach(([k,v])=>{
    if(!isAppKey(k)) throw new Error('Clave de almacenamiento no válida: '+k);
    storage.setItem(k,String(v));
  });
}

function captureCookies(){
  const out=Object.create(null);
  try{
    if(!document.cookie) return out;
    document.cookie.split(/;\s*/).forEach(part=>{
      const i=part.indexOf('=');
      const rawName=i>=0?part.slice(0,i):part;
      const rawValue=i>=0?part.slice(i+1):'';
      const name=safeDecode(rawName);
      if(isAppKey(name)) out[name]=safeDecode(rawValue);
    });
  }catch(e){}
  return out;
}
function setCookie(name,value,maxAge){
  document.cookie=encodeURIComponent(name)+'='+encodeURIComponent(value)+'; path='+appDirectory()+'; max-age='+maxAge+'; SameSite=Lax';
}
function restoreCookiesExact(data){
  const current=captureCookies();
  Object.keys(current).forEach(k=>{ if(!Object.prototype.hasOwnProperty.call(data,k)) setCookie(k,'',0); });
  Object.entries(data||{}).forEach(([k,v])=>{
    if(!isAppKey(k)) throw new Error('Cookie no válida: '+k);
    setCookie(k,String(v),31536000);
  });
}

function runtimeHints(){
  const out={};
  try{
    if(typeof state!=='undefined' && state && typeof state==='object'){
      const flipKey=['flip','flipped','girado','rotated'].find(k=>Object.prototype.hasOwnProperty.call(state,k) && typeof state[k]==='boolean');
      if(flipKey) out.flip={key:flipKey,value:state[flipKey]};
      if(Number.isFinite(Number(state.i))) out.stateIndex=Number(state.i);
    }
  }catch(e){}
  const filter=document.querySelector('.fbtn.active[data-f]');
  if(filter) out.filter=filter.getAttribute('data-f');
  const active=document.querySelector('.tab.active,.gtab.active');
  if(active){
    out.activeControl={id:active.id||'',attrs:{}};
    ['data-v','data-view','data-tab','data-target'].forEach(a=>{
      if(active.hasAttribute(a)) out.activeControl.attrs[a]=active.getAttribute(a);
    });
  }
  const view=document.querySelector('.view.active[id]');
  if(view) out.activeViewId=view.id;
  return out;
}

function currentExerciseNumber(){
  try{
    if(typeof curr==='function'){
      const p=curr();
      if(p && Number.isFinite(Number(p.n))) return Number(p.n);
    }
  }catch(e){}
  try{
    const n=Number(localStorage.getItem('wp_ultimo'));
    if(Number.isFinite(n) && n>0) return n;
  }catch(e){}
  const el=document.querySelector('.exno');
  if(el){
    const m=(el.textContent||'').match(/\d+/);
    if(m) return Number(m[0]);
  }
  return null;
}

function capturePageState(){
  const file=currentFile();
  if(!VALID_PAGES.has(file)) return null;
  const snap={
    file,
    lastExercise:currentExerciseNumber(),
    runtime:runtimeHints(),
    savedAt:new Date().toISOString()
  };
  try{ localStorage.setItem(PAGE_PREFIX+file,JSON.stringify(snap)); }catch(e){}
  return snap;
}
function readPageState(file=currentFile()){
  try{
    const raw=localStorage.getItem(PAGE_PREFIX+file);
    return raw?JSON.parse(raw):null;
  }catch(e){ return null; }
}
function sameControl(el,desc){
  if(!el || !desc) return false;
  if(desc.id && el.id===desc.id) return true;
  const attrs=desc.attrs||{};
  const names=Object.keys(attrs);
  return names.length>0 && names.every(a=>el.getAttribute(a)===attrs[a]);
}
function findControl(desc){
  if(!desc) return null;
  if(desc.id){ const byId=document.getElementById(desc.id); if(byId) return byId; }
  return Array.from(document.querySelectorAll('.tab,.gtab')).find(el=>sameControl(el,desc))||null;
}
function currentFlipValue(preferredKey){
  try{
    if(typeof state!=='undefined' && state && typeof state==='object'){
      if(preferredKey && typeof state[preferredKey]==='boolean') return state[preferredKey];
      const k=['flip','flipped','girado','rotated'].find(n=>typeof state[n]==='boolean');
      if(k) return state[k];
    }
  }catch(e){}
  return null;
}
function applyPageState(){
  const snap=readPageState();
  if(!snap || !snap.runtime) return;
  const rt=snap.runtime;
  try{
    if(rt.filter!=null){
      const f=Array.from(document.querySelectorAll('.fbtn[data-f]')).find(el=>el.getAttribute('data-f')===String(rt.filter));
      if(f && !f.classList.contains('active')) f.click();
    }
  }catch(e){}
  try{
    if(rt.activeControl){
      const c=findControl(rt.activeControl);
      if(c && !c.classList.contains('active')) c.click();
    }
  }catch(e){}
  try{
    if(rt.flip && typeof rt.flip.value==='boolean'){
      const now=currentFlipValue(rt.flip.key);
      const b=document.getElementById('b-flip');
      if(now!==null && now!==rt.flip.value && b) b.click();
    }
  }catch(e){}
}

function captureUi(){
  const inputs=[];
  document.querySelectorAll('input[id],select[id],textarea[id]').forEach(el=>{
    if(el.id==='pc-backup-file' || (el.tagName==='INPUT' && el.type==='file')) return;
    inputs.push({id:el.id,value:el.value,checked:('checked' in el)?!!el.checked:null,selectedIndex:('selectedIndex' in el)?el.selectedIndex:null});
  });
  const details=[];
  document.querySelectorAll('details[id]').forEach(el=>details.push({id:el.id,open:!!el.open}));
  return {scrollX:window.scrollX||0,scrollY:window.scrollY||0,inputs,details};
}
function restoreUi(ui){
  if(!ui || typeof ui!=='object') return;
  (ui.inputs||[]).forEach(s=>{
    const el=document.getElementById(s.id);
    if(!el || (el.tagName==='INPUT' && el.type==='file')) return;
    try{
      if(s.value!=null) el.value=s.value;
      if(s.checked!==null && 'checked' in el) el.checked=!!s.checked;
      if(s.selectedIndex!==null && 'selectedIndex' in el && Number.isInteger(s.selectedIndex)) el.selectedIndex=s.selectedIndex;
    }catch(e){}
  });
  (ui.details||[]).forEach(s=>{
    const el=document.getElementById(s.id);
    if(el && el.tagName==='DETAILS') el.open=!!s.open;
  });
  requestAnimationFrame(()=>requestAnimationFrame(()=>window.scrollTo(Number(ui.scrollX)||0,Number(ui.scrollY)||0)));
}

function makeEnvelope(payload){
  return {magic:MAGIC,formatVersion:FORMAT_VERSION,checksum:fnv1a(JSON.stringify(payload)),payload};
}
function buildBackup(){
  const currentPageState=capturePageState();
  const payload={
    app:'PC de Luis A3',
    exportedAt:new Date().toISOString(),
    page:{file:currentFile(),search:location.search||'',hash:location.hash||''},
    storage:{local:captureStorage(localStorage),session:captureStorage(sessionStorage)},
    cookies:captureCookies(),
    currentPageState,
    ui:captureUi()
  };
  return makeEnvelope(payload);
}
function validateEnvelope(env){
  if(!plainObject(env) || env.magic!==MAGIC || env.formatVersion!==FORMAT_VERSION || !plainObject(env.payload)) throw new Error('El archivo no es una copia compatible de PC de Luis A3.');
  if(env.checksum!==fnv1a(JSON.stringify(env.payload))) throw new Error('La copia está dañada o fue modificada.');
  const p=env.payload;
  if(!plainObject(p.storage) || !plainObject(p.storage.local) || !plainObject(p.storage.session) || !plainObject(p.cookies)) throw new Error('La estructura de la copia no es válida.');
  for(const group of [p.storage.local,p.storage.session,p.cookies]){
    for(const [k,v] of Object.entries(group)){
      if(!isAppKey(k) || (typeof v!=='string' && typeof v!=='number' && typeof v!=='boolean')) throw new Error('La copia contiene datos no válidos.');
    }
  }
  if(!plainObject(p.page) || !VALID_PAGES.has(String(p.page.file||'').toLowerCase())) throw new Error('La copia no identifica un index válido.');
  return p;
}

function notify(kind,msg){
  try{ if(typeof setStatus==='function'){ setStatus(kind,msg); return; } }catch(e){}
  if(kind==='no') window.alert(msg);
}
function snapshotForRollback(){ return {local:captureStorage(localStorage),session:captureStorage(sessionStorage),cookies:captureCookies()}; }
function restoreRollback(snap){
  try{ clearAppStorage(localStorage); writeStorage(localStorage,snap.local); }catch(e){}
  try{ clearAppStorage(sessionStorage); writeStorage(sessionStorage,snap.session); }catch(e){}
  try{ restoreCookiesExact(snap.cookies); }catch(e){}
}
function applyPayload(payload){
  const rollback=snapshotForRollback();
  try{
    clearAppStorage(localStorage);
    clearAppStorage(sessionStorage);
    writeStorage(localStorage,payload.storage.local);
    writeStorage(sessionStorage,payload.storage.session);
    restoreCookiesExact(payload.cookies);
  }catch(e){
    restoreRollback(rollback);
    throw e;
  }
}
function askRestore(callback){
  const msg='¿Importar esta copia? Se reemplazarán el progreso y la configuración actuales por los de la copia.';
  try{
    if(typeof pedirConfirmacion==='function'){ pedirConfirmacion(msg,callback); return; }
  }catch(e){}
  if(window.confirm(msg)) callback();
}
function navigateAfterImport(payload){
  const target=String(payload.page.file).toLowerCase();
  const search=typeof payload.page.search==='string'?payload.page.search:'';
  const hash=typeof payload.page.hash==='string'?payload.page.hash:'';
  try{ sessionStorage.setItem(RESTORE_UI_KEY,JSON.stringify({file:target,ui:payload.ui||null})); }catch(e){}
  try{ sessionStorage.setItem(RESTORE_NOTICE_KEY,'Copia importada correctamente.'); }catch(e){}
  const next=appDirectory()+target+search+hash;
  if(location.pathname===appDirectory()+target && location.search===search && location.hash===hash) location.reload();
  else location.assign(next);
}
function performImport(payload){
  try{
    applyPayload(payload);
    navigateAfterImport(payload);
  }catch(e){
    notify('no','No se pudo importar la copia. No se cambió tu información. '+(e&&e.message?e.message:''));
  }
}

function exportBackup(){
  try{
    const env=buildBackup();
    const blob=new Blob([JSON.stringify(env,null,2)],{type:'application/json'});
    const a=document.createElement('a');
    const stamp=new Date().toISOString().replace(/[:.]/g,'-');
    a.href=URL.createObjectURL(blob);
    a.download='PC-de-LuisA3-copia-'+stamp+'.json';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(()=>URL.revokeObjectURL(a.href),0);
    notify('ok','Copia de seguridad exportada.');
  }catch(e){ notify('no','No se pudo exportar la copia. '+(e&&e.message?e.message:'')); }
}
async function importSelectedFile(file){
  if(!file) return;
  try{
    if(file.size>25*1024*1024) throw new Error('El archivo es demasiado grande.');
    const text=await file.text();
    const env=JSON.parse(text);
    const payload=validateEnvelope(env);
    askRestore(()=>performImport(payload));
  }catch(e){ notify('no','No se pudo leer la copia. '+(e&&e.message?e.message:'')); }
}

function restorePendingUi(){
  try{
    const raw=sessionStorage.getItem(RESTORE_UI_KEY);
    if(!raw) return;
    const data=JSON.parse(raw);
    if(!data || data.file!==currentFile()) return;
    sessionStorage.removeItem(RESTORE_UI_KEY);
    restoreUi(data.ui);
  }catch(e){ try{sessionStorage.removeItem(RESTORE_UI_KEY);}catch(x){} }
}
function showPendingNotice(){
  try{
    const msg=sessionStorage.getItem(RESTORE_NOTICE_KEY);
    if(!msg) return;
    sessionStorage.removeItem(RESTORE_NOTICE_KEY);
    setTimeout(()=>notify('ok',msg),0);
  }catch(e){}
}

let snapshotTimer=null;
function scheduleSnapshot(){
  clearTimeout(snapshotTimer);
  snapshotTimer=setTimeout(capturePageState,120);
}
function setup(){
  const exp=document.getElementById('b-backup-export');
  const imp=document.getElementById('b-backup-import');
  const input=document.getElementById('pc-backup-file');
  if(!exp || !imp || !input) return;
  capturePageState();
  applyPageState();
  restorePendingUi();
  showPendingNotice();
  exp.addEventListener('click',exportBackup);
  imp.addEventListener('click',()=>{ input.value=''; input.click(); });
  input.addEventListener('change',()=>{ const f=input.files&&input.files[0]; importSelectedFile(f); });
  window.addEventListener('pagehide',capturePageState);
  document.addEventListener('visibilitychange',()=>{ if(document.visibilityState==='hidden') capturePageState(); });
  document.addEventListener('click',scheduleSnapshot,true);
  document.addEventListener('keyup',scheduleSnapshot,true);
  document.addEventListener('change',scheduleSnapshot,true);
}

window.PCBackupTools=Object.freeze({makeEnvelope,validateEnvelope,checksum:fnv1a,isAppKey,buildBackup});
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',setup,{once:true});
else setup();
})();
</script>'''

for path in FILES:
    text = path.read_text(encoding='utf-8')
    if 'id="pc-backup-system"' in text or 'id="b-backup-export"' in text:
        raise SystemExit(f'{path}: backup feature already present')
    if text.count('<div class="moves" id="movelist">') != 1:
        raise SystemExit(f'{path}: movelist insertion point not unique')
    if text.count('Girar tablero</button>') != 1:
        raise SystemExit(f'{path}: expected exactly one Girar tablero button')
    if text.count('</head>') != 1 or text.count('</body>') != 1:
        raise SystemExit(f'{path}: head/body closing tag not unique')

    text = text.replace('</head>', PRELOAD + '\n</head>', 1)
    text = text.replace('Girar tablero</button>', 'Girar</button>', 1)
    text = text.replace('    <div class="moves" id="movelist">', BACKUP_ROW + '\n\n    <div class="moves" id="movelist">', 1)
    text = text.replace('</body>', SYSTEM + '\n</body>', 1)
    path.write_text(text, encoding='utf-8')

# Static verification on the patched files.
report=[]
for path in FILES:
    text=path.read_text(encoding='utf-8')
    checks={
        'export_button_once': text.count('id="b-backup-export"')==1,
        'import_button_once': text.count('id="b-backup-import"')==1,
        'file_input_once': text.count('id="pc-backup-file"')==1,
        'preload_once': text.count('id="pc-backup-preload"')==1,
        'system_once': text.count('id="pc-backup-system"')==1,
        'old_flip_text_absent': 'Girar tablero</button>' not in text,
        'new_flip_text_present': 'Girar</button>' in text,
        'backup_between_solution_and_movelist': text.index('id="b-sol"') < text.index('id="b-backup-export"') < text.index('id="movelist"'),
        'indexeddb_not_used_by_app': 'indexedDB' not in text,
        'backup_local_storage': 'captureStorage(localStorage)' in text,
        'backup_session_storage': 'captureStorage(sessionStorage)' in text,
        'backup_cookies': 'captureCookies()' in text,
        'backup_checksum': 'checksum:fnv1a(JSON.stringify(payload))' in text,
        'page_specific_resume': "PAGE_PREFIX='pc_backup_page_state_v2:'" in text and "localStorage.setItem('wp_ultimo'" in text,
    }
    bad=[k for k,v in checks.items() if not v]
    if bad:
        raise SystemExit(f'{path}: verification failed: {bad}')

    literal_keys=re.findall(r'(?:localStorage|sessionStorage)\.(?:getItem|setItem|removeItem)\(\s*[\'\"]([^\'\"]+)', text)
    unexpected=sorted({k for k in literal_keys if not (k.startswith('wp_') or k.startswith('pc_') or k.startswith('__pc_backup_'))})
    if unexpected:
        raise SystemExit(f'{path}: unexpected storage key namespace: {unexpected}')

    # Syntax-check both injected JavaScript blocks with Node.
    for script_id in ('pc-backup-preload','pc-backup-system'):
        m=re.search(r'<script id="'+re.escape(script_id)+r'">(.*?)</script>', text, re.S)
        if not m:
            raise SystemExit(f'{path}: script {script_id} missing')
        tmp=Path(f'.tmp-{path.stem}-{script_id}.js')
        tmp.write_text(m.group(1),encoding='utf-8')
        subprocess.run(['node','--check',str(tmp)],check=True,capture_output=True,text=True)
        tmp.unlink()

    report.append(f'{path}: OK')
    report.extend('  '+k+': OK' for k in checks)
    report.append(f'  literal_storage_keys_checked: {len(set(literal_keys))}')

# Pure checksum/integrity unit test for the injected backup format.
# We duplicate the exact FNV-1a rule used in JS and verify mutation detection.
def fnv1a_py(s):
    h=0x811c9dc5
    # JS iterates UTF-16 code units; test data below is ASCII for exact parity.
    for ch in s:
        h ^= ord(ch)
        h = ((h * 0x01000193) & 0xffffffff)
    return f'{h:08x}'

sample='{"storage":{"local":{"wp_ultimo":"17","pc_modo":"oscuro"},"session":{}},"cookies":{},"page":{"file":"index1.html"}}'
hash1=fnv1a_py(sample)
hash2=fnv1a_py(sample.replace('17','18'))
if hash1==hash2:
    raise SystemExit('checksum mutation test failed')
report.append('checksum_mutation_test: OK')

Path('backup-feature-validation.txt').write_text('\n'.join(report)+'\n',encoding='utf-8')
print('\n'.join(report))
