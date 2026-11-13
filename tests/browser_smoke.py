"""Offline real-extension smoke test using installed Playwright/Chromium.
Run with the Stanford DDL environment Python; no dependency installation needed.
"""
from pathlib import Path
import tempfile, hashlib, csv, io, os
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
URL='https://stanforddeliberate.org/admin/rooms/16860/viz'
HTML='''<!doctype html><html><head><title>Fixture</title></head><body><h3>Test room (/demo-en-a)</h3><div style="height:180px"></div><table class="transcript"><tbody>
<tr id="one"><td>00:01</td><td><b>Alice (Interrupting):</b> Hello "team". <a href="#native">link text</a></td><td>(0.9)</td></tr>
<tr id="two"><td>00:02</td><td><b>Bob:</b> [Transcript Missing]</td></tr>
<tr id="three"><td>00:03</td><td><b>Eve:</b> =HYPERLINK("bad")</td></tr>
<tr id="system"><td>00:04</td><td>System: recording started</td></tr>
</tbody></table><textarea id="paste" aria-label="Paste target"></textarea></body></html>'''
def columns(text): return next(csv.reader(io.StringIO(text), delimiter='\t'))
with sync_playwright() as p, tempfile.TemporaryDirectory(prefix='ddl-viz-test-') as profile:
    context=p.chromium.launch_persistent_context(profile, channel='chromium', executable_path=os.environ.get('CHROMIUM_EXECUTABLE'), headless=True, args=[f'--disable-extensions-except={ROOT}',f'--load-extension={ROOT}'])
    context.route('https://stanforddeliberate.org/**', lambda route: route.fulfill(status=200,content_type='text/html',body=HTML))
    context.grant_permissions(['clipboard-read','clipboard-write'], origin='https://stanforddeliberate.org')
    page=context.new_page(); errors=[]; page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(URL); page.locator('#one').click(); panel=page.locator('.ddl-report-toolbar'); panel.wait_for()
    page.get_by_role('button',name='Copy A–H',exact=True).click(); assert 'Add your name' in panel.inner_text()
    panel.locator('[name=helperName]').fill('Test Reporter'); page.get_by_role('button',name='Copy A–H',exact=True).click()
    page.get_by_text('Copied A–H. Paste into column A of the sheet.',exact=True).wait_for()
    text=page.evaluate('navigator.clipboard.readText()'); cols=columns(text)
    assert len(cols)==8 and cols[0]==URL and cols[1]=='Test Reporter' and cols[3]=='' and cols[4]=='Alice' and cols[5]=='00:01' and cols[6]=='Hello "team". link text' and cols[7]=='https://stanforddeliberate.org/demo-en-a',cols
    # Real paste event from native clipboard into an ordinary browser textarea.
    page.locator('#paste').focus(); page.keyboard.press('Meta+V'); assert page.locator('#paste').input_value()==text
    # Editable G starts from the parsed text. Editing it must leave A–F alone.
    field=panel.locator('[name=errorText]')
    assert field.input_value()=='Hello "team". link text'
    original_cols=cols[:]
    field.fill('Custom "error"\twith\n<img src=x onerror=alert(1)>')
    page.locator('#one').click()
    assert field.input_value().startswith('Custom "error"') # Same row retains the draft.
    page.get_by_role('button',name='Copy A–H',exact=True).click()
    page.get_by_text('Copied A–H. Paste into column A of the sheet.',exact=True).wait_for()
    edited=columns(page.evaluate('navigator.clipboard.readText()'))
    assert edited[:6]==original_cols[:6] and edited[6]=='Custom "error" with <img src=x onerror=alert(1)>',edited
    assert panel.locator('img').count()==0
    field.fill('')
    page.get_by_role('button',name='Copy A–H',exact=True).click()
    page.get_by_text('Copied A–H. Paste into column A of the sheet.',exact=True).wait_for()
    blank=columns(page.evaluate('navigator.clipboard.readText()'))
    assert len(blank)==8 and blank[:6]==original_cols[:6] and blank[6]=='',blank
    field.fill('=HYPERLINK("bad")')
    page.get_by_role('button',name='Copy A–H',exact=True).click()
    page.get_by_text('Copied A–H. Paste into column A of the sheet.',exact=True).wait_for()
    assert columns(page.evaluate('navigator.clipboard.readText()'))[6].startswith("'=HYPERLINK")
    page.locator('#two').click(); assert panel.locator('[name=helperName]').input_value()=='Test Reporter'
    assert panel.locator('[name=errorText]').input_value()=='[Transcript Missing]'
    panel.locator('[name=hearability]').select_option('Badly'); page.get_by_role('button',name='Copy A–H',exact=True).click()
    page.get_by_text('Copied A–H. Paste into column A of the sheet.',exact=True).wait_for()
    cols=columns(page.evaluate('navigator.clipboard.readText()')); assert cols[3]=='Badly' and cols[4]=='Bob' and cols[6]=='[Transcript Missing]',cols
    page.locator('#three').click(); assert panel.locator('[name=hearability]').input_value()==''
    assert panel.locator('[name=errorText]').input_value()=='=HYPERLINK("bad")'
    panel.locator('[name=hearability]').select_option('Other'); panel.locator('[name=hearabilityOther]').fill('Choppy\t audio')
    page.get_by_role('button',name='Copy A–H',exact=True).click(); page.get_by_text('Copied A–H. Paste into column A of the sheet.',exact=True).wait_for()
    cols=columns(page.evaluate('navigator.clipboard.readText()')); assert cols[3]=='Choppy audio' and cols[6].startswith("'=HYPERLINK"),cols
    page.keyboard.press('Escape'); assert panel.count()==0
    page.locator('#system').click(); page.get_by_role('button',name='Copy A–H',exact=True).click(); page.get_by_text('Copied A–H. Paste into column A of the sheet.',exact=True).wait_for()
    cols=columns(page.evaluate('navigator.clipboard.readText()')); assert cols[4]=='' and cols[6]=='System: recording started',cols
    page.get_by_role('button',name='Close',exact=True).click(); assert panel.count()==0
    page.locator('#one a').click(); assert page.url.endswith('#native') and panel.count()==0
    page.reload(); page.locator('#two').click(); assert panel.locator('[name=helperName]').input_value()=='Test Reporter'
    page.set_viewport_size({'width':375,'height':667}); bounds=panel.bounding_box(); assert bounds['x']>=0 and bounds['x']+bounds['width']<=375
    page.screenshot(path=str(ROOT/'tests/smoke-preview.png'))
    # Unpacked extension IDs derive from the absolute path in Chromium.
    extension_id=''.join(chr(ord('a')+int(c,16)) for c in hashlib.sha256(str(ROOT).encode()).hexdigest()[:32])
    popup=context.new_page(); popup.goto(f'chrome-extension://{extension_id}/popup.html')
    popup.locator('#save').wait_for(); popup.wait_for_function("!document.querySelector('#save').disabled")
    assert popup.locator('#helperName').input_value()=='Test Reporter'
    popup.locator('#helperName').fill('Updated Reporter'); popup.locator('#save').click()
    popup.get_by_text('Reporting as Updated Reporter.',exact=True).wait_for()
    page.bring_to_front(); panel.locator('[name=helperName]').wait_for()
    page.wait_for_function("document.querySelector('.ddl-report-toolbar [name=helperName]').value === 'Updated Reporter'")
    popup.close()
    # Visible shortcut, keyboard-accessible label, and reduced-motion support.
    live_button=page.get_by_role('button',name='Open live room in a new tab',exact=True)
    assert live_button.is_visible()
    assert page.locator('.ddl-live-room-dot').get_attribute('aria-hidden')=='true'
    assert page.locator('.ddl-live-room-dot').evaluate('(el) => getComputedStyle(el).animationName')=='ddl-live-room-pulse'
    page.emulate_media(reduced_motion='reduce')
    assert page.locator('.ddl-live-room-dot').evaluate('(el) => getComputedStyle(el).animationName')=='none'
    page.emulate_media(reduced_motion='no-preference')
    with page.expect_popup() as opened:
        live_button.click()
    room_page=opened.value; room_page.wait_for_load_state('domcontentloaded')
    assert room_page.url=='https://stanforddeliberate.org/demo-en-a'
    room_page.close()
    page.screenshot(path=str(ROOT/'tests/smoke-preview.png'))
    # H must come from an unambiguous heading, never transcript/body text.
    page.set_viewport_size({'width':1280,'height':800})
    for heading, expected in [('Test (/new-room)', 'https://stanforddeliberate.org/new-room'), ('No slug here', ''), ('Ambiguous (/first) (/second)', ''), ('Malformed (/bad/path)', '')]:
        page.keyboard.press('Escape')
        page.evaluate('(heading) => {document.querySelector("h3").textContent=heading; document.querySelector("#system td:nth-child(2)").textContent="Transcript mentions (/wrong-room)";}', heading)
        page.locator('#two').click()
        button=page.locator('.ddl-live-room-button')
        assert button.count()==(1 if expected else 0)
        if expected: assert button.get_attribute('title')==expected
        page.get_by_role('button',name='Copy A–H',exact=True).click()
        page.get_by_text('Copied A–H. Paste into column A of the sheet.',exact=True).wait_for()
        copied=columns(page.evaluate('navigator.clipboard.readText()'))
        assert len(copied)==8 and copied[7]==expected,copied
    # If the heading disappears altogether, a transcript-like slug still must not populate H.
    page.keyboard.press('Escape'); page.locator('h3').evaluate('(el) => el.remove()')
    page.locator('#two').click(); page.get_by_role('button',name='Copy A–H',exact=True).click()
    page.get_by_text('Copied A–H. Paste into column A of the sheet.',exact=True).wait_for()
    assert columns(page.evaluate('navigator.clipboard.readText()'))[7]==''
    assert not errors,errors
    print('PASS: real extension, native clipboard and paste, eight columns, optional/Other hearability, multiple successive rows, name persistence, system rows, formula safety, Close/Escape, native link, narrow viewport, real extension popup and cross-context name update, editable G defaults/custom/blank/reset/injection safety; no page errors.')
    context.close()
