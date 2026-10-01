"""Browser gate for migrated Odoo 20 actions.

Opens every act_window / client action supplied by the caller as a real user, waits for the view,
optionally opens the "New" form, and records error dialogs, JS errors and console errors.

Usage: odoo20_browser_gate.py BASE DB LOGIN PASSWORD [OUTDIR]
The list of actions comes from stdin (one `module.xmlid` per line; produce it with the SQL in the README of this dir).
"""
import os, sys
from playwright.sync_api import sync_playwright

BASE, DB, LOGIN, PASSWORD = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3], sys.argv[4]
OUT = sys.argv[5] if len(sys.argv) > 5 else '/tmp/odoo20_browser_gate'
os.makedirs(OUT, exist_ok=True)
actions = [l.strip() for l in sys.stdin if l.strip()]
IGNORE = ('favicon', 'Failed to load resource: the server responded with a status of 404 (Not Found)')
results = []


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={'width': 1500, 'height': 950})
        page = ctx.new_page()
        errors = []
        page.on('console', lambda m: errors.append('console: ' + m.text[:300]) if m.type == 'error' else None)
        page.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)[:300]))
        page.goto(f'{BASE}/web/login?db={DB}')
        page.fill('input[name=login]', LOGIN)
        page.fill('input[name=password]', PASSWORD)
        page.click('button[type=submit]')
        page.wait_for_selector('.o_main_navbar', timeout=90000)
        for xmlid in actions:
            errors.clear()
            status, detail = 'PASS', ''
            try:
                page.goto(f'{BASE}/odoo/action-{xmlid}')
                page.wait_for_selector('.o_action_manager, .o_error_dialog, .modal-dialog', timeout=60000)
                page.wait_for_timeout(1200)
                if page.locator('.o_error_dialog, .modal-dialog .o_error, .o_notification.border-danger').count():
                    status = 'FAIL'
                    detail = 'error dialog: ' + page.locator('.modal-dialog').first.inner_text()[:200].replace('\n', ' ')
                elif page.locator('.o_action_manager > *').count() == 0 and page.locator('.modal-dialog .o_form_view, .modal-dialog .modal-body').count():
                    detail = 'wizard dialog opened'   # target=new actions render as a dialog, not a page
                elif page.locator('.o_action_manager > *').count() == 0:
                    status, detail = 'FAIL', 'empty action manager'
                else:
                    new = page.locator('.o_list_button_add, .o_form_button_create, .o-kanban-button-new').first
                    if new.count() and new.is_visible():
                        new.click()
                        page.wait_for_timeout(1500)
                        if page.locator('.o_error_dialog, .modal-dialog .o_error').count():
                            status = 'FAIL'
                            detail = 'error dialog on New: ' + page.locator('.modal-dialog').first.inner_text()[:200].replace('\n', ' ')
                real = [e for e in errors if not any(i in e for i in IGNORE)]
                if real and status == 'PASS':
                    status, detail = 'FAIL', '; '.join(real)[:300]
            except Exception as exc:  # noqa: BLE001
                status, detail = 'FAIL', f'{type(exc).__name__}: {str(exc)[:200]}'
            if status == 'FAIL':
                page.screenshot(path=os.path.join(OUT, xmlid.replace('.', '_') + '.png'))
            results.append((status, xmlid, detail))
            print(f'{status} {xmlid} {detail}', flush=True)
        browser.close()
    failed = [r for r in results if r[0] == 'FAIL']
    print(f'\n{len(results) - len(failed)}/{len(results)} passed')
    sys.exit(1 if failed else 0)


main()
