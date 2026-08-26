from pathlib import Path

p=Path('.backup-feature-patch.py')
s=p.read_text(encoding='utf-8')

repls=[
("function isAppKey(key){ return typeof key==='string' && (key.startsWith('wp_') || key.startsWith('pc_')); }",
 "function isAppKey(key){ return typeof key==='string' && (key.startsWith('wp_') || key.startsWith('wp2_') || key.startsWith('pc_')); }"),
("      localStorage.setItem('wp_ultimo',String(Number(snap.lastExercise)));",
 "      localStorage.setItem(f==='index2.html'?'wp2_ultimo':'wp_ultimo',String(Number(snap.lastExercise)));"),
("    const n=Number(localStorage.getItem('wp_ultimo'));",
 "    const ultimoKey=currentFile()==='index2.html'?'wp2_ultimo':'wp_ultimo';\n    const n=Number(localStorage.getItem(ultimoKey));"),
("not (k.startswith('wp_') or k.startswith('pc_') or k.startswith('__pc_backup_'))",
 "not (k.startswith('wp_') or k.startswith('wp2_') or k.startswith('pc_') or k.startswith('__pc_backup_'))"),
("\"PAGE_PREFIX='pc_backup_page_state_v2:'\" in text and \"localStorage.setItem('wp_ultimo'\" in text",
 "\"PAGE_PREFIX='pc_backup_page_state_v2:'\" in text and \"wp_ultimo\" in text and \"wp2_ultimo\" in text")
]

for old,new in repls:
    count=s.count(old)
    if count!=1:
        raise SystemExit(f'Expected exactly one patch target, got {count}: {old[:90]}')
    s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')
print('index2 namespace fix applied')
