"""Validate the offline 3D game in Chromium with actual WebGL and game physics."""
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),
        headless=True,args=['--no-sandbox','--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1280,'height':800})
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.set_content((ROOT/'gameplay3d.html').read_text())
    page.wait_for_function('window.game3d || window.game3dError')
    assert page.evaluate('typeof game3dError')=='undefined', 'WebGL initialization failed'
    page.get_by_role('button',name='Overview',exact=True).click()
    page.screenshot(path=str(ROOT/'artifacts/3d-overview.png'))
    page.get_by_role('button',name='Watch bot',exact=True).click()
    result=page.evaluate('''() => {const g=game3d;let steps=0;
        while(!g.state.won&&steps<50000){g.update(1/120);steps++}
        g.render(1);return {...g.state,steps,seconds:steps/120}}''')
    assert result['won'],result
    assert result['bank']['Ascended']==result['bank']['Forbidden']==1
    assert all(v['floor']==5 and v['power']==5 for v in result['pickups'] if v['name'] in ['Ascended','Forbidden'])
    print(f"Bot completed in {result['seconds']:.1f} simulated seconds; both top-floor rarities banked.")
    page.screenshot(path=str(ROOT/'artifacts/3d-win.png'))
    page.get_by_role('button',name='Restart',exact=True).click()
    # Default camera-relative WASD moves in both x and z, then jumps onto green tier.
    manual=page.evaluate('''() => {const g=game3d;g.setCamera(0);g.setKeys({forward:true});
        for(let i=0;i<90;i++)g.update(1/120);g.jump();
        for(let i=0;i<100;i++)g.update(1/120);g.setKeys({});for(let i=0;i<20;i++)g.update(1/120);g.render(1);return {...g.state}}''')
    assert manual['ground']==1,manual
    page.get_by_role('button',name='Collect [E]',exact=True).click()
    assert page.evaluate('game3d.state.carry')=='Common'
    page.evaluate('''() => {const g=game3d;g.setKeys({back:true});for(let i=0;i<200;i++)g.update(1/120);g.setKeys({})}''')
    assert page.evaluate('game3d.state.bank.Common')==1
    page.get_by_role('button',name='Upgrade [U]',exact=True).click()
    assert page.evaluate('game3d.state.power')==2
    page.get_by_role('button',name='Pause',exact=True).click()
    assert page.evaluate('''() => {const g=game3d,b=g.state.z;g.setKeys({forward:true});g.update(1);return g.state.z===b}''')
    page.get_by_role('button',name='Restart',exact=True).click()
    page.evaluate('''() => {const g=game3d;g.state.x=-2;g.state.z=-40;g.state.y=20;g.state.ground=5;g.state.top=true;g.state.power=4;g.collect()}''')
    assert page.evaluate('game3d.state.carry') is None
    page.evaluate('''() => {const g=game3d;g.reset();g.state.x=4.7+Math.sin(1)*.35;g.state.z=-6.4;g.state.y=4;g.state.ground=1;g.state.carry='Common';g.update(1/120)}''')
    assert page.evaluate('game3d.state.falls')==1
    assert page.evaluate('game3d.state.carry') is None
    # Canvas drag and wheel affect view without requiring pointer lock.
    page.get_by_role('button',name='Restart',exact=True).click()
    page.mouse.move(650,400);page.mouse.down();page.mouse.move(800,350,steps=8);page.mouse.up();page.mouse.wheel(0,200)
    page.get_by_role('button',name='Halloween look',exact=True).click()
    page.get_by_role('button',name='Overview',exact=True).click()
    page.evaluate('game3d.render(1)')
    page.screenshot(path=str(ROOT/'artifacts/3d-halloween.png'))
    assert not errors,errors
    print('PASS: WebGL, manual move/jump/collect/bank/upgrade, pause, rare gate, obstacle loss, camera, theme.')
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(ROOT/'artifacts/3d-mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Mobile layout overflows'
    browser.close()
