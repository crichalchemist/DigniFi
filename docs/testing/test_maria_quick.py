"""Quick test: Maria only — verify analytics 401s are gone."""
import json, urllib.request, re
from playwright.sync_api import sync_playwright

PASSWORD = "DigniFi-Demo-2026!"

data = json.dumps({"username": "demo_maria", "password": PASSWORD}).encode()
req = urllib.request.Request(
    "http://localhost:8000/api/token/obtain/",
    data=data, headers={"Content-Type": "application/json"}
)
resp = urllib.request.urlopen(req)
tokens = json.loads(resp.read())

req2 = urllib.request.Request(
    "http://localhost:8000/api/intake/sessions/",
    headers={"Authorization": f"Bearer {tokens['access']}"}
)
resp2 = urllib.request.urlopen(req2)
sessions = json.loads(resp2.read())
session_id = next(s["id"] for s in sessions["results"] if s["status"] == "completed")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    page.goto("http://localhost:5173")
    page.wait_for_load_state("domcontentloaded")
    page.evaluate(f"""() => {{
        localStorage.setItem('refresh_token', '{tokens["refresh"]}');
        localStorage.setItem('current_session_id', '{session_id}');
    }}""")

    page.goto("http://localhost:5173/forms")
    for _ in range(10):
        page.wait_for_timeout(1000)
        if "Your Court Forms" in (page.text_content("body") or ""):
            print("Dashboard: OK")
            break

    page.get_by_role("button", name=re.compile("Generate All")).click()
    page.wait_for_selector("[role='dialog']", timeout=5000)
    page.locator(".upl-modal-checkbox").check()
    page.wait_for_timeout(500)
    page.locator(".upl-modal-footer button:has-text('Continue')").click()
    print("Generate All: clicked")

    for _ in range(30):
        page.wait_for_timeout(2000)
        body = page.text_content("body") or ""
        if "All 13 forms have been generated" in body or "13 of 13" in body:
            print("Forms: All 13 generated!")
            break

    page.wait_for_timeout(2000)
    survey = page.locator(".post-task-survey")
    if survey.count() > 0 and survey.is_visible():
        page.locator("input[name='comprehension'][value='5']").check()
        page.locator("input[name='dignity'][value='5']").check()
        page.locator("input[name='confidence'][value='4']").check()
        page.get_by_role("button", name="Submit Feedback").click()
        page.wait_for_timeout(1500)
        if page.locator(".survey-thanks").is_visible():
            print("Survey: OK")

    auth_401 = [e for e in console_errors if "401" in e]
    other = [e for e in console_errors if "401" not in e and "favicon" not in e.lower()]
    print(f"\nConsole errors: {len(auth_401)} 401s, {len(other)} other")
    for e in auth_401[:3]:
        print(f"  401: {e[:80]}")
    for e in other[:3]:
        print(f"  Other: {e[:80]}")

    browser.close()
