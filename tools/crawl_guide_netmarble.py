import json,sys
from playwright.sync_api import sync_playwright
# Usage : python3 tools/crawl_guide_netmarble.py DEBUT FIN DOSSIER_SORTIE
# Lit les pages du guide officiel Netmarble (guide.netmarble.com/sololv/<n>) avec Playwright
# (CHROMIUM_PATH facultatif) et écrit DOSSIER_SORTIE/<n>.txt ; puis tools/parse_guide_netmarble.py.
import os
S=sys.argv[3].rstrip('/')+'/'
os.makedirs(S,exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/opt/pw-browsers/chromium'),args=['--no-sandbox'])
    pg=b.new_page()
    for n in range(int(sys.argv[1]),int(sys.argv[2])):
        try:
            pg.goto(f'https://guide.netmarble.com/sololv/{n}',wait_until='domcontentloaded',timeout=30000)
            pg.wait_for_timeout(1200)
            t=pg.title(); body=pg.inner_text('body')
            i=body.find('Game Mode Reward Rate'); 
            # content after menu
            c=body[i+len('Game Mode Reward Rate'):] if i>=0 else body
            open(S+f'{n}.txt','w').write(t+'\n'+c)
            imgs=pg.evaluate("()=>[...document.querySelectorAll('img')].map(i=>i.src).filter(u=>u.startsWith('http')&&u.includes('/images/'))")
            if imgs: open(S+f'{n}.img.json','w').write(json.dumps(imgs))
            print(n,t,len(c),flush=True)
        except Exception as e: print(n,'ERR',str(e)[:60],flush=True)
    b.close()
