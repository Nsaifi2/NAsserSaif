from playwright.sync_api import sync_playwright
import shutil
from pathlib import Path

with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1100,'height':950})
 errors=[]
 page.on('pageerror',lambda e: errors.append(str(e)))
 page.set_content((Path(__file__).resolve().parents[1] / 'gameplay.html').read_text())
 page.get_by_role('button',name='Watch bot',exact=True).click()
 result=page.evaluate('''() => {
 const g=window.towerGame;let frames=0;
 while(!g.state.won && frames<100000){g.update(1/120);frames++}
 g.draw();return {frames,seconds:frames/120,...g.state};
 }''')
 print(result)
 assert result['won'], 'Bot did not complete gameplay'
 assert result['power']==5
 assert all(v['floor']==5 and v['power']==5 for v in result['pickups'] if v['name'] in ['Ascended','Forbidden'])
 assert not errors,errors
 page.get_by_role('button',name='Restart',exact=True).click()
 result=page.evaluate('''() => {const g=window.towerGame;g.setKeys({right:true});for(let i=0;i<120;i++)g.update(1/120);g.setKeys({});g.jump();for(let i=0;i<120;i++)g.update(1/120);g.draw();return {...g.state}}''')
 print('Manual movement/jump:',result['x'],result['y'],result['ground'])
 assert result['x']>300 and result['ground']==1
 page.get_by_role('button',name='Collect',exact=True).click()
 # Move into pickup radius using actual physics.
 page.evaluate('''() => {const g=window.towerGame;g.setKeys({right:true});for(let i=0;i<29;i++)g.update(1/120);g.setKeys({});g.collect()}''')
 assert page.evaluate('towerGame.state.carry')=='Common'
 page.evaluate('''() => {const g=window.towerGame;g.drop();g.setKeys({left:true});for(let i=0;i<155;i++)g.update(1/120);g.setKeys({});}''')
 assert page.evaluate('towerGame.state.bank.Common')==1
 page.get_by_role('button',name='Upgrade jump',exact=True).click()
 assert page.evaluate('towerGame.state.power')==2
 page.get_by_role('button',name='Pause',exact=True).click()
 assert page.evaluate('''() => {const g=towerGame,before=g.state.x;g.setKeys({right:true});g.update(1);return g.state.x===before}''')
 page.evaluate('''() => {const g=towerGame;g.reset();g.state.x=365;g.state.y=1000;g.state.ground=5;g.state.top=true;g.state.power=4;g.collect()}''')
 assert page.evaluate('towerGame.state.carry') is None
 page.evaluate('''() => {const g=towerGame;g.reset();g.state.x=270+Math.sin(1)*15;g.state.y=200;g.state.ground=1;g.state.carry='Common';g.update(1/120)}''')
 assert page.evaluate('towerGame.state.falls')==1
 assert page.evaluate('towerGame.state.carry') is None
 print('PASS: actual browser bot, rare gate, manual move/jump/collect/bank/upgrade, pause; no JS errors.')
 browser.close()
