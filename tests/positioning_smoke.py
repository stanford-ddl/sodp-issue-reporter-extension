"""Offline positioning regression test with the real extension; no clipboard writes.
Uses the same installed Python/Playwright/Chromium setup as browser_smoke.py.
"""
from pathlib import Path
import os
import tempfile
from playwright.sync_api import sync_playwright

ROOT = Path(os.environ.get('EXTENSION_ROOT', Path(__file__).resolve().parents[1]))
URL = 'https://stanforddeliberate.org/admin/rooms/16860/viz'
HTML = '''<!doctype html><html><head><style>
body { margin: 8px; } table { border-collapse: collapse; width: 100%; }
td { height: 28px; } #spacer { height: 440px; }
</style></head><body><h3>Fixture (/demo-en-a)</h3><div id="spacer"></div>
<table class="transcript"><tbody>
<tr id="one"><td>00:01</td><td><b>Alice:</b> Synthetic transcript</td></tr>
<tr id="two"><td>00:02</td><td><b>Bob:</b> Second transcript</td></tr>
</tbody></table><div style="height:1500px"></div></body></html>'''


def settle(page):
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')


def stable(panel, original, label):
    actual = panel.bounding_box()
    assert abs(actual['x'] - original['x']) < 1 and abs(actual['y'] - original['y']) < 1, (label, original, actual)


def contained(page, panel):
    box = panel.bounding_box()
    size = page.viewport_size
    assert box['x'] >= 7 and box['y'] >= 7, box
    assert box['x'] + box['width'] <= size['width'] - 7, box
    assert box['y'] + box['height'] <= size['height'] - 7, box


with sync_playwright() as p, tempfile.TemporaryDirectory(prefix='ddl-position-test-') as profile:
    context = p.chromium.launch_persistent_context(
        profile, channel='chromium', executable_path=os.environ.get('CHROMIUM_EXECUTABLE'),
        headless=True, args=[f'--disable-extensions-except={ROOT}', f'--load-extension={ROOT}'])
    context.route('https://stanforddeliberate.org/**', lambda route: route.fulfill(content_type='text/html', body=HTML))
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(URL)
    panel = page.locator('.ddl-report-toolbar')
    # Full-width rows exercise above/below placement; narrow rows exercise beside.
    for width, height, table_width, spacer in [(1000, 800, '100%', 440), (1000, 800, '100%', 20), (1280, 800, '400px', 440), (375, 667, '100%', 20), (375, 300, '100%', 20)]:
        page.keyboard.press('Escape')
        page.set_viewport_size({'width': width, 'height': height})
        page.evaluate('([width, height]) => { scrollTo(0, 0); document.querySelector("table").style.width = width; document.querySelector("#spacer").style.height = height + "px"; }', [table_width, spacer])
        page.locator('#one').click()
        panel.wait_for()
        original = panel.bounding_box()
        select = panel.locator('[name=hearability]')
        for choice in ['Other', 'Fine', 'Other', '', 'Other']:
            select.select_option(choice)
            settle(page)
            stable(panel, original, f'{width}x{height}: {choice}')
            contained(page, panel)
        panel.locator('[name=hearabilityOther]').fill('Synthetic other description')
        field = panel.locator('[name=errorText]')
        field.fill('\n'.join(f'Synthetic line {i}' for i in range(80)))
        field.evaluate('(el) => { el.style.height = "180px"; el.scrollTop = el.scrollHeight; }')
        settle(page)
        stable(panel, original, 'textarea growth and internal scroll')
        panel.evaluate('(el) => { el.scrollTop = el.scrollHeight; }')
        settle(page)
        stable(panel, original, 'panel scroll')
        # Validation text and focus-induced internal scrolling also stay put.
        panel.get_by_role('button', name='Copy A–H', exact=True).click()
        page.get_by_text('Add your name, then copy.', exact=True).wait_for()
        settle(page)
        stable(panel, original, 'validation and focus')
        contained(page, panel)
        # Resizing must constrain the whole panel, including expanded content.
        page.set_viewport_size({'width': 320, 'height': 240})
        settle(page)
        contained(page, panel)
        resized = panel.bounding_box()
        select.select_option('Fine')
        select.select_option('Other')
        settle(page)
        stable(panel, resized, 'editing after resize')
        page.keyboard.press('Escape')
        assert panel.count() == 0
    # Page scroll should follow the row without reselecting a side after expansion.
    page.set_viewport_size({'width': 1280, 'height': 1000})
    page.evaluate('() => { scrollTo(0, 0); document.querySelector("table").style.width = "400px"; document.querySelector("#spacer").style.height = "300px"; }')
    page.locator('#one').click()
    panel.locator('[name=hearability]').select_option('Other')
    before = panel.bounding_box()
    page.evaluate('scrollBy(0, 80)')
    settle(page)
    after = panel.bounding_box()
    assert abs(after['y'] - (before['y'] - 80)) < 1, (before, after)
    assert abs(after['x'] - before['x']) < 1
    # New row resets the placement and draft; reopening still works.
    page.locator('#two').click()
    assert panel.locator('[name=hearability]').input_value() == ''
    assert panel.locator('[name=errorText]').input_value() == 'Second transcript'
    panel.get_by_role('button', name='Close', exact=True).click()
    assert panel.count() == 0
    page.locator('#one').click()
    contained(page, panel)
    # Removed targets cannot leave a stale popover after scroll.
    page.locator('#one').evaluate('(el) => el.remove()')
    page.evaluate('scrollBy(0, 10)')
    settle(page)
    assert panel.count() == 0
    assert not errors, errors
    print('PASS: stable Other toggles, textarea resize/scroll, panel scroll, validation/focus, viewport resize, page scroll, row reset, Close/Escape/reopen and removed row; five layouts; no page errors.')
    context.close()
