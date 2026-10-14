import json, collections, urllib.request, urllib.error, ssl, concurrent.futures as cf, os
ssl._create_default_https_context = ssl._create_unverified_context
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36',
   'Referer':'https://www.bilibili.com/','Origin':'https://www.bilibili.com',
   'Range':'bytes=0-2047','Accept':'*/*'}
d=json.load(open('database.json',encoding='utf-8'))
tracks=d['tracks']
def chk(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=20)
        return r.status in (200,206)
    except Exception:
        return False
items=[(i,(x.get('_song') or {}).get('download_url') or '') for i,x in enumerate(tracks)]
items=[(i,u) for i,u in items if u]
with cf.ThreadPoolExecutor(24) as ex:
    res=list(ex.map(chk,[u for _,u in items]))
alive=[tracks[i]['id'] for (i,_),ok in zip(items,res) if ok]
stat=collections.Counter(tracks[i]['source_cn'] for (i,_),ok in zip(items,res) if ok)
print('ALIVE', len(alive), 'of', len(items))
print(dict(stat))
os.makedirs('data',exist_ok=True)
json.dump({'probed_at':__import__('time').time(),'alive_ids':alive},open('data/alive.json','w',encoding='utf-8'),ensure_ascii=False)
print('written data/alive.json')
