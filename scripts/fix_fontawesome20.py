#!/usr/bin/env python3
"""FontAwesome -> Odoo 20 icons in XML: `icon="fa-x"` on buttons and `<i class="fa fa-x ...">` glyphs.
Every target name comes from fontawesome_to_material_symbols_map.json (validated against
odoo/addons/web/tooling/icons/icons_wishlist.txt, the shipped font subset). Unknown icons are REPORTED, never guessed.
Usage: fix_fontawesome20.py <tree>...   (edits in place)"""
import glob, json, os, re, sys
M = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fontawesome_to_material_symbols_map.json')))
unknown, n_attr, n_tag = set(), 0, 0
for root in sys.argv[1:]:
    for p in glob.glob(root + '/**/*.xml', recursive=True):
        if '/i18n/' in p: continue
        s = o = open(p, encoding='utf-8').read()
        def attr(m):
            global n_attr
            v = M.get(m.group(2))
            if not v: unknown.add(m.group(2)); return m.group(0)
            n_attr += 1; return f'{m.group(1)}"{v}"'
        s = re.sub(r'(\bicon=)"fa-([a-z0-9-]+)"', attr, s)
        def tag(m):
            global n_tag
            head, cls, rest = m.group(1), m.group(2), m.group(3)
            toks = cls.split()
            if 'fa' not in toks or 'data-icon' in head + rest: return m.group(0)
            names = [t[3:] for t in toks if t.startswith('fa-') and t not in ('fa-fw', 'fa-lg', 'fa-2x', 'fa-3x', 'fa-spin')]
            if len(names) != 1: return m.group(0)
            v = M.get(names[0])
            if not v: unknown.add(names[0]); return m.group(0)
            new = []
            for t in toks:
                if t == 'fa': new.append('oi')
                elif t in ('fa-fw', 'fa-lg', 'fa-spin', 'fa-2x', 'fa-3x'): new.append(t.replace('fa-', 'oi-'))
                elif t.startswith('fa-'): continue
                else: new.append(t)
            n_tag += 1
            return f'{head}class="{" ".join(new)}" data-icon="{v}"{rest}'
        s = re.sub(r'(<(?:i|span)\b[^>]*?\s)class="([^"]*)"([^>]*>)', tag, s)
        if s != o: open(p, 'w', encoding='utf-8').write(s)
print(f'attributes {n_attr}, glyph tags {n_tag}, unknown icons: {sorted(unknown) or "none"}')
