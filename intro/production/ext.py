import pickle,re,os
ents=pickle.load(open('ents.pkl','rb'))
f=open('/home/user/chronica-ipad/index.pck','rb')
want=re.compile(r'imported/(logo_|lion_|crest_|shield_|realm_banner|unit_|building_|tech_|game_over|vignette|night|phase_|den|ruin|menu_|millefleurs|satin|frame|topbar|res_|stat_)')
cnt=0
for p,off,size in ents:
    if not p.endswith('.ctex') or not want.search(p): continue
    f.seek(off);d=f.read(size)
    name=re.sub(r'-[0-9a-f]{32}\.ctex','',p.split('/')[-1])
    i=d.find(b'RIFF'); j=d.find(b'\x89PNG')
    if j>=0 and (i<0 or j<i): ext='png';s=j
    elif i>=0: ext='webp';s=i
    else: print('??',name,d[:40]);continue
    open(f'ex/{name}.{ext}','wb').write(d[s:]);cnt+=1
print(cnt)
