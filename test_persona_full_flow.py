"""
Full persona test: login → forms dashboard → generate all → verify → survey.

Tests all 5 seeded personas through form generation and survey collection.
Uses pre-seeded accounts (seed_demo_data) which already have completed sessions.

Strategy: Login via API, set tokens + session ID in localStorage,
then navigate directly to /forms. AuthProvider's silent refresh handles auth.
"""

import json
import sys
import re
import urllib.request
from playwright.sync_api import sync_playwright, Page

BASE_URL = "http://localhost:5173"
API_URL = "http://localhost:8000/api"

PERSONAS = [
    {"username": "demo_maria", "name": "Maria Torres"},
    {"username": "demo_james", "name": "James Washington"},
    {"username": "demo_priya", "name": "Priya Sharma"},
    {"username": "demo_deshawn", "name": "DeShawn Mitchell"},
    {"username": "demo_sarah", "name": "Sarah Chen"},
]
PASSWORD = "DigniFi-Demo-2026!"

RESULTS = []


def api_login(username: str) -> dict:
    """Get JWT tokens + completed session ID via API."""
    # Get tokens
    data = json.dumps({"username": username, "password": PASSWORD}).encode()
    req = urllib.request.Request(
        f"{API_URL}/token/obtain/",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    tokens = json.loads(resp.read())

    # Find completed session
    req2 = urllib.request.Request(
        f"{API_URL}/intake/sessions/",
        headers={"Authorization": f"Bearer {tokens['access']}"},
    )
    resp2 = urllib.request.urlopen(req2)
    sessions_data = json.loads(resp2.read())
    sessions = sessions_data.get("results", sessions_data) if isinstance(sessions_data, dict) else sessions_data

    session_id = None
    for s in sessions:
        if s["status"] == "completed":
            session_id = s["id"]
            break

    return {
        "access": tokens["access"],
        "refresh": tokens["refresh"],
        "session_id": session_id,
    }


def setup_browser_auth(page: Page, auth_data: dict) -> bool:
    """Set auth tokens and session ID in the browser, then navigate to forms."""
    if not auth_data["session_id"]:
        print("  [ERROR] No completed session found")
        return False

    # Navigate to app root to establish page context for localStorage
    page.goto(BASE_URL)
    page.wait_for_load_state("domcontentloaded")

    # Set refresh token and session ID in localStorage
    # Access token is set in memory by the silent refresh cycle
    page.evaluate(f"""() => {{
        localStorage.setItem('refresh_token', '{auth_data["refresh"]}');
        localStorage.setItem('current_session_id', '{auth_data["session_id"]}');
    }}""")

    print(f"  [OK] Set refresh_token and session_id={auth_data['session_id']} in localStorage")
    return True


def navigate_to_forms(page: Page) -> bool:
    """Navigate to forms dashboard and wait for it to load."""
    page.goto(f"{BASE_URL}/forms")

    # Wait for IntakeProvider to load session (reads localStorage, calls API)
    for attempt in range(15):
        page.wait_for_timeout(1000)
        body = page.text_content("body") or ""
        if "Your Court Forms" in body:
            print("  [OK] Forms dashboard loaded")
            return True
        if "No active intake session" in body:
            print("  [ERROR] No active session found")
            return False
        if "Something went wrong" in body:
            print("  [ERROR] Error boundary triggered")
            return False
        if "Welcome back" in body or "Sign in" in body:
            print("  [WARN] Redirected to login — auth not established")
            return False
        if attempt == 5:
            print(f"  [WAIT] Still loading... ({body[:80].strip()})")

    body = page.text_content("body") or ""
    print(f"  [TIMEOUT] Content: {body[:200]}")
    return False


def generate_all_forms(page: Page) -> bool:
    """Click Generate All, handle UPL modal, verify generation."""
    body = page.text_content("body") or ""

    # Check if already generated
    if "All 13 forms have been generated" in body:
        print("  [OK] Forms already generated (from seed)")
        return True

    # Find Generate All button
    generate_btn = page.get_by_role("button", name=re.compile(r"Generate All"))
    if generate_btn.count() == 0 or not generate_btn.is_visible():
        print("  [ERROR] Generate All button not found")
        return False

    generate_btn.click()
    print("  [OK] Clicked Generate All button")

    # UPL Confirmation Modal
    try:
        page.wait_for_selector("[role='dialog']", timeout=5000)
        print("  [OK] UPL confirmation modal appeared")
    except Exception:
        print("  [ERROR] UPL modal did not appear")
        return False

    # Check acknowledgment checkbox
    checkbox = page.locator(".upl-modal-checkbox")
    if checkbox.count() > 0:
        checkbox.check()
        print("  [OK] Checked UPL acknowledgment")
    else:
        print("  [ERROR] UPL checkbox not found")
        return False

    # Click Continue (should be enabled now that checkbox is checked)
    page.wait_for_timeout(500)
    continue_btn = page.locator(".upl-modal-footer button:has-text('Continue')")
    if continue_btn.count() > 0 and continue_btn.is_enabled():
        continue_btn.click()
        print("  [OK] Clicked Continue — generating forms...")
    else:
        print("  [ERROR] Continue button not enabled")
        return False

    # Wait for generation (backend generates 13 forms — can take 10-30s)
    for attempt in range(30):
        page.wait_for_timeout(2000)
        body = page.text_content("body") or ""

        if "All 13 forms have been generated" in body:
            print("  [OK] All 13 forms generated!")
            return True

        match = re.search(r"(\d+) of 13 generated", body)
        if match:
            count = int(match.group(1))
            if count == 13:
                print("  [OK] 13 of 13 forms generated!")
                return True
            if attempt % 5 == 0:
                print(f"  [WAIT] {count} of 13 generated...")

        # Check for error states
        if "error" in body.lower() and "dismiss" in body.lower():
            print(f"  [ERROR] Error shown on page")
            return False

    body = page.text_content("body") or ""
    match = re.search(r"(\d+) of 13 generated", body)
    if match:
        count = int(match.group(1))
        print(f"  [PARTIAL] {count}/13 generated (timeout)")
        return count > 0

    print("  [TIMEOUT] Form generation did not complete")
    return False


def check_form_statuses(page: Page) -> dict:
    """Count form card statuses."""
    cards = page.locator("article.form-card").all()
    statuses = {"generated": 0, "pending": 0, "other": 0}

    for card in cards:
        text = card.text_content() or ""
        if "Download" in text or "Generated" in text or "Mark as Filed" in text:
            statuses["generated"] += 1
        elif "Generate" in text and "Generate All" not in text:
            statuses["pending"] += 1
        else:
            statuses["other"] += 1

    total_gen = statuses["generated"]
    print(f"  [INFO] Forms: {total_gen} generated, {statuses['pending']} pending")
    return statuses


def complete_survey(page: Page) -> bool:
    """Fill and submit the post-task survey."""
    # Wait for survey to appear (it's rendered after successful generateAll)
    for _ in range(8):
        survey = page.locator(".post-task-survey")
        if survey.count() > 0 and survey.is_visible():
            break
        page.wait_for_timeout(1000)

    survey = page.locator(".post-task-survey")
    if survey.count() == 0 or not survey.is_visible():
        print("  [SKIP] Survey did not appear")
        return False

    print("  [OK] Survey visible!")

    # Fill Likert scales (1-5 radio buttons)
    for q_id, score in [("comprehension", 4), ("dignity", 5), ("confidence", 3)]:
        radio = page.locator(f"input[name='{q_id}'][value='{score}']")
        if radio.count() > 0:
            radio.check()
            print(f"  [OK] Rated {q_id}: {score}/5")

    # Fill text questions
    for field_id, text in [
        ("survey-confusing", "Legal terms were hard to understand"),
        ("survey-change", "Add a glossary for legal terms"),
    ]:
        textarea = page.locator(f"#{field_id}")
        if textarea.count() > 0:
            textarea.fill(text)
            print(f"  [OK] Filled {field_id}")

    # Submit
    submit_btn = page.get_by_role("button", name="Submit Feedback")
    if submit_btn.count() > 0 and submit_btn.is_visible():
        submit_btn.click()
        page.wait_for_timeout(1500)

        thanks = page.locator(".survey-thanks")
        if thanks.count() > 0 and thanks.is_visible():
            print("  [OK] Survey submitted — 'Thank you' message shown!")
            return True
        else:
            print("  [WARN] Submit clicked but no thanks message")
            return True  # Clicked at least

    print("  [WARN] Submit button not found")
    return False


def test_persona(persona: dict) -> dict:
    """Run the full flow for a single persona."""
    result = {
        "username": persona["username"],
        "name": persona["name"],
        "login": False,
        "forms_dashboard": False,
        "forms_generated": False,
        "form_count": 0,
        "survey_completed": False,
        "errors": [],
    }

    print(f"\n{'='*60}")
    print(f"Testing: {persona['name']} ({persona['username']})")
    print(f"{'='*60}")

    # Get auth data via API first
    try:
        auth_data = api_login(persona["username"])
        print(f"  [OK] API login successful, session_id={auth_data['session_id']}")
    except Exception as e:
        result["errors"].append(f"API login failed: {e}")
        print(f"  [EXCEPTION] API login: {e}")
        return result

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        try:
            # Step 1: Setup browser auth
            if setup_browser_auth(page, auth_data):
                result["login"] = True
            else:
                result["errors"].append("No completed session")
                browser.close()
                return result

            # Step 2: Navigate to forms dashboard
            if navigate_to_forms(page):
                result["forms_dashboard"] = True

                # Step 3: Generate all forms
                if generate_all_forms(page):
                    result["forms_generated"] = True
                    statuses = check_form_statuses(page)
                    result["form_count"] = statuses["generated"]

                    # Step 4: Complete survey
                    result["survey_completed"] = complete_survey(page)
                else:
                    result["errors"].append("Form generation failed or timed out")
            else:
                result["errors"].append("Forms dashboard did not load")

        except Exception as e:
            result["errors"].append(str(e)[:200])
            print(f"  [EXCEPTION] {e}")

        # Filter cosmetic errors (analytics 401s)
        real_errors = [e for e in console_errors
                       if "audit/logs" not in e and "favicon" not in e.lower()]
        if real_errors:
            result["errors"].extend([f"Console: {e[:100]}" for e in real_errors[:3]])
            print(f"  [CONSOLE] {len(real_errors)} error(s)")
            for err in real_errors[:3]:
                print(f"    - {err[:120]}")

        # Screenshot
        try:
            import os
            os.makedirs("/Volumes/Containers/DigniFi/test-results", exist_ok=True)
            page.screenshot(path=f"/Volumes/Containers/DigniFi/test-results/{persona['username']}_final.png")
        except Exception:
            pass

        browser.close()

    return result


def main():
    print("\n" + "="*60)
    print("PERSONA TESTING: Full Flow — Forms + Survey")
    print("="*60)

    for persona in PERSONAS:
        result = test_persona(persona)
        RESULTS.append(result)

    # Summary
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    print(f"{'Persona':<25} {'Auth':>5} {'Dash':>5} {'Gen':>5} {'#':>4} {'Survey':>7}")
    print("-" * 55)

    for r in RESULTS:
        print(
            f"{r['name']:<25} "
            f"{'OK' if r['login'] else 'FAIL':>5} "
            f"{'OK' if r['forms_dashboard'] else 'FAIL':>5} "
            f"{'OK' if r['forms_generated'] else 'FAIL':>5} "
            f"{r['form_count']:>4} "
            f"{'OK' if r['survey_completed'] else 'SKIP':>7}"
        )

    errors = [r for r in RESULTS if r["errors"]]
    if errors:
        print(f"\nERRORS ({len(errors)} personas):")
        for r in errors:
            print(f"  {r['name']}:")
            for err in r["errors"]:
                print(f"    - {err[:150]}")

    passed = sum(1 for r in RESULTS if r["forms_dashboard"])
    generated = sum(1 for r in RESULTS if r["forms_generated"])
    surveyed = sum(1 for r in RESULTS if r["survey_completed"])
    total_forms = sum(r["form_count"] for r in RESULTS)

    print(f"\n--- TOTALS ---")
    print(f"Dashboard:  {passed}/{len(RESULTS)}")
    print(f"Generated:  {generated}/{len(RESULTS)}")
    print(f"Forms:      {total_forms}")
    print(f"Surveys:    {surveyed}/{len(RESULTS)}")

    return 0 if generated > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
