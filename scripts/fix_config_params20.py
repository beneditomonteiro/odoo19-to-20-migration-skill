"""get_param -> typed getters (Odoo 20). Rules: caller-side comparison/parsing decides the type."""
import re,sys,os
BOOL_KEY=re.compile(r'(enable|disable|_enabled|require_contact|capture_raw|auto_subscribe)')
def split_args(a):
    out=[];d=0;cur='';q=None
    for ch in a:
        if q:
            cur+=ch
            if ch==q: q=None
            continue
        if ch in '\'"': q=ch;cur+=ch;continue
        if ch in '([{': d+=1
        if ch in ')]}': d-=1
        if ch==',' and d==0: out.append(cur);cur=''
        else: cur+=ch
    if cur.strip(): out.append(cur)
    return [x.strip() for x in out]
def boolify(d):
    if d in (None,"'True'",'"True"','True'): return 'True' if d else 'False'
    if d in ("'False'",'"False"','False'): return 'False'
    return d
def conv(path):
    s=open(path).read(); out='';pos=0;n=0
    for m in re.finditer(r'\.get_param\(',s):
        if m.start()<pos: continue
        i=m.end();d=1
        while d: d+=(s[i]=='(')-(s[i]==')'); i+=1
        args=split_args(s[m.end():i-1])
        pos_args=[a for a in args if not re.match(r'\w+\s*=',a)]
        kw={a.split('=',1)[0].strip():a.split('=',1)[1].strip() for a in args if re.match(r'\w+\s*=',a)}
        key=pos_args[0]; default=pos_args[1] if len(pos_args)>1 else kw.get('default')
        pre=s[:m.start()]; post=s[i:]
        kind='str'; strip_post=0; neg=False
        mm=re.match(r"\s*==\s*['\"]True['\"]",post)
        mn=re.match(r"\s*!=\s*['\"]True['\"]",post)
        ml=re.match(r"\.lower\(\)\s+in\s+\([^)]*\)",post)
        if mm: kind='bool';strip_post=mm.end()
        elif mn: kind='bool';strip_post=mn.end();neg=True
        elif ml: kind='bool';strip_post=ml.end()
        elif re.search(r'\bint\(\s*$',pre): kind='int'
        elif re.search(r'\bfloat\(\s*$',pre): kind='float'
        elif re.search(r"_id['\"]",key): kind='int'
        elif BOOL_KEY.search(key.split('.')[-1]): kind='bool'
        if kind=='bool': default=boolify(default) if default is not None else 'False'
        elif kind=='int':
            default = 'HASH_VERSION' if default and 'HASH_VERSION' in default else (re.sub(r"^['\"](\d+)['\"]$",r'\1',default) if default else '0')
            if default in ('None','False'): default='0'
        elif kind=='float':
            default = re.sub(r"^['\"]([\d.]+)['\"]$",r'\1',default) if default else '0.0'
        new=f".get_{kind}({key}" + (f", {default}" if default is not None else "") + ")"
        seg=s[pos:m.start()]+new
        if neg:
            # rewrite: <recv>.get_param(...) != 'True'  ->  not <recv>.get_bool(...)
            j=len(seg)-len(new)
            k=j
            while k>0 and re.match(r"[\w\.\[\]'\"()]",seg[k-1]) : k-=1
            seg=seg[:k]+'not '+seg[k:]
        out+=seg; pos=i+strip_post; n+=1
    out+=s[pos:]
    if out!=s: open(path,'w').write(out)
    return n
tot=0
for r in sys.argv[1:]:
    for dp,dn,fn in os.walk(r):
        if 'tests' in dp.split(os.sep) or '__pycache__' in dp: continue
        for f in fn:
            if f.endswith('.py'):
                k=conv(os.path.join(dp,f)); tot+=k
                if k: print(k,os.path.join(dp,f))
print('total',tot)
