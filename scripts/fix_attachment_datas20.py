import re,sys,os
n=0
pat=re.compile(r"""(['"])datas\1(\s*):(\s*)(?:__import__\('base64'\)|base64)\.b64encode\(""")
for r in sys.argv[1:]:
    for dp,dn,fn in os.walk(r):
        if '__pycache__' in dp: continue
        for f in fn:
            if not f.endswith('.py'): continue
            p=os.path.join(dp,f); s=open(p).read(); out='';pos=0;changed=False
            for m in pat.finditer(s):
                if m.start()<pos: continue
                i=m.end();d=1
                while d: d+=(s[i]=='(')-(s[i]==')'); i+=1
                expr=s[m.end():i-1]
                rest=s[i:]
                dec=re.match(r"\.decode\([^)]*\)",rest)
                end=i+(dec.end() if dec else 0)
                out+=s[pos:m.start()]+f"'raw'{m.group(2)}:{m.group(3)}{expr}"; pos=end; changed=True; n+=1
            out+=s[pos:]
            if changed: open(p,'w').write(out); print(p)
print('replaced',n)
