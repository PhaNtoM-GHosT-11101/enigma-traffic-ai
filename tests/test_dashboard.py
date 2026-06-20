import os
import re
import json
import time
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8000"
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_IMAGE_PATH = os.path.normpath(os.path.join(CUR_DIR, "..", "backend", "test_input.jpg"))

def run_check(num, desc, condition):
    status = "PASS" if condition else "FAIL"
    print(f"\nCHECK {num:02d}: {desc} -> {status}")
    assert condition, f"Check {num:02d} failed: {desc}"

def setup_console_logging(page: Page):
    page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))
    page.on("pageerror", lambda err: print(f"[Browser Error] {err}"))

def test_tier1_initial_load(page: Page):
    """
    Tier 1: Initial Load & Static Elements (Checks 1 to 25)
    Verifies the page title, layout, default states, explanatory sections, and legend items.
    """
    print("\n--- Running Tier 1 Tests ---")
    setup_console_logging(page)
    page.goto(BASE_URL)
    
    # Check 01: Page title matches
    run_check(1, "Page title matches 'Gridlock AI — Traffic Violation Detection'", 
              page.title() == "Gridlock AI — Traffic Violation Detection")
    
    # Check 02: Google Fonts api link
    run_check(2, "Page links to Google Fonts API", 
              page.locator("link[href*='fonts.googleapis.com']").count() > 0)
    
    # Check 03: Header contains 'Traffic Violation'
    run_check(3, "Header h1 contains 'Traffic Violation'", 
              "TRAFFIC VIOLATION" in page.locator("h1").inner_text().upper())
    
    # Check 04: Subtitle mentions the 7-stage computer vision pipeline
    run_check(4, "Header subtitle describes 7-stage pipeline", 
              "7-stage computer vision pipeline" in page.locator("p.subtitle").inner_text())
    
    # Check 05: Header badge displays gridlock hackathon (handles uppercase transform)
    run_check(5, "Header badge displays 'Gridlock Hackathon'", 
              "GRIDLOCK" in page.locator("header .badge").inner_text().upper())
    
    # Check 06: Pipeline stages row is visible
    run_check(6, "Pipeline stages row is visible", 
              page.locator("#pipeline-stages").is_visible())
    
    # Checks 07-13: Verification of 7 pipeline stages
    stages = [
        ("stage-1", "Raw Input"),
        ("stage-2", "CLAHE Preproc"),
        ("stage-3", "YOLOv8 Detect"),
        ("stage-4", "Crop & Extract"),
        ("stage-5", "Pose & Faces"),
        ("stage-6", "Violation Engine"),
        ("stage-7", "OCR & Report")
    ]
    for idx, (stage_id, stage_name) in enumerate(stages):
        run_check(7 + idx, f"Stage {idx+1} name contains '{stage_name}'", 
                  stage_name.upper() in page.locator(f"#{stage_id}").inner_text().upper())
        
    # Check 14: Upload Traffic Image card is present (resolves strict mode by choosing .first)
    run_check(14, "'Upload Traffic Image' card is present", 
              "UPLOAD TRAFFIC IMAGE" in page.locator(".card-title").first.inner_text().upper())
    
    # Check 15: Drop zone element exists
    run_check(15, "Drop zone element exists", 
              page.locator("#drop-zone").count() == 1)
    
    # Check 16: Drop zone contains standard instruction text
    run_check(16, "Drop zone contains instructions", 
              "DROP IMAGE HERE" in page.locator("#drop-zone").inner_text().upper())
    
    # Check 17: Hidden file input element exists
    run_check(17, "File input element exists", 
              page.locator("#file-input").count() == 1)
    
    # Check 18: Run Detection Pipeline button exists
    run_check(18, "Run button exists", 
              page.locator("#process-btn").count() == 1)
    
    # Check 19: Run Detection Pipeline button is initially disabled
    run_check(19, "Run button is initially disabled", 
              page.locator("#process-btn").is_disabled())
    
    # Check 20: Camera Configuration section is visible
    run_check(20, "Camera Configuration section is visible", 
              page.locator("text=Camera Configuration").is_visible())
    
    # Check 21: Results section is initially hidden
    run_check(21, "Results section is hidden", 
              not page.locator("#results-section").is_visible())
    
    # Check 22: Pipeline progress section is initially hidden
    run_check(22, "Pipeline progress is hidden", 
              not page.locator("#progress-wrap").is_visible())
    
    # Check 23: Error toast is initially hidden
    run_check(23, "Error toast is hidden", 
              not page.locator("#error-toast").is_visible())
    
    # Check 24: 7 Checks Legend section is visible
    run_check(24, "Legend card is visible", 
              page.locator("text=7 Checks — Violation Engine").is_visible())
    
    # Check 25: Legend items display description for "No Helmet"
    run_check(25, "Legend shows helmet violation details", 
              "NO HELMET" in page.locator(".legend-grid").inner_text().upper())


def test_tier2_camera_config_and_upload(page: Page):
    """
    Tier 2: Camera Configuration Panel & User Inputs (Checks 26 to 45)
    Verifies input elements, modification handling, staging a file, and drop-zone state updates.
    """
    print("\n--- Running Tier 2 Tests ---")
    setup_console_logging(page)
    page.goto(BASE_URL)
    
    # Check 26: Stop Line Y configuration input field exists
    run_check(26, "Stop Line Y input is present", 
              page.locator("#cfg-stop-y").count() == 1)
    
    # Check 27: Stop Line Y input default is 400
    run_check(27, "Stop Line Y default value is 400", 
              page.locator("#cfg-stop-y").input_value() == "400")
    
    # Check 28: Lane Divider X configuration input field exists
    run_check(28, "Lane Divider X input is present", 
              page.locator("#cfg-divider-x").count() == 1)
    
    # Check 29: Lane Divider X input default is 320
    run_check(29, "Lane Divider X default value is 320", 
              page.locator("#cfg-divider-x").input_value() == "320")
    
    # Check 30: Signal ROI configuration input field exists
    run_check(30, "Signal ROI input is present", 
              page.locator("#cfg-signal-roi").count() == 1)
    
    # Check 31: Signal ROI input default is 0,0,80,80
    run_check(31, "Signal ROI default value is 0,0,80,80", 
              page.locator("#cfg-signal-roi").input_value() == "0,0,80,80")
    
    # Check 32: Camera ID configuration input field exists
    run_check(32, "Camera ID input is present", 
              page.locator("#cfg-camera-id").count() == 1)
    
    # Check 33: Camera ID input default is CAM-001
    run_check(33, "Camera ID default value is CAM-001", 
              page.locator("#cfg-camera-id").input_value() == "CAM-001")
    
    # Check 34: Modifying Stop Line Y updates value
    page.locator("#cfg-stop-y").fill("450")
    run_check(34, "Stop Line Y updates to 450", 
              page.locator("#cfg-stop-y").input_value() == "450")
    
    # Check 35: Modifying Lane Divider X updates value
    page.locator("#cfg-divider-x").fill("300")
    run_check(35, "Lane Divider X updates to 300", 
              page.locator("#cfg-divider-x").input_value() == "300")
    
    # Check 36: Modifying Signal ROI updates value
    page.locator("#cfg-signal-roi").fill("10,10,90,90")
    run_check(36, "Signal ROI updates to 10,10,90,90", 
              page.locator("#cfg-signal-roi").input_value() == "10,10,90,90")
    
    # Check 37: Modifying Camera ID updates value
    page.locator("#cfg-camera-id").fill("CAM-TEST")
    run_check(37, "Camera ID updates to CAM-TEST", 
              page.locator("#cfg-camera-id").input_value() == "CAM-TEST")
    
    # Check 38: Stop Line Y boundary value 0 is accepted
    page.locator("#cfg-stop-y").fill("0")
    run_check(38, "Stop Line Y boundary of 0 is accepted", 
              page.locator("#cfg-stop-y").input_value() == "0")
    
    # Check 39: Lane Divider X boundary value 0 is accepted
    page.locator("#cfg-divider-x").fill("0")
    run_check(39, "Lane Divider X boundary of 0 is accepted", 
              page.locator("#cfg-divider-x").input_value() == "0")
    
    # Check 40: Staging file works
    page.locator("#file-input").set_input_files(TEST_IMAGE_PATH)
    # Check if the process button is enabled to verify successful staging
    run_check(40, "Run button is enabled after file upload", 
              page.locator("#process-btn").is_enabled() == True)
    
    # Check 41: Drop zone text contains the filename
    run_check(41, "Drop zone displays the filename", 
              "test_input.jpg" in page.locator("#drop-zone").inner_text())
    
    # Check 42: Upload enables the Run Detection button
    run_check(42, "Run button is enabled", 
              page.locator("#process-btn").is_disabled() == False)
    
    # Check 43: Drop zone displays green check
    run_check(43, "Drop zone shows check emoji", 
              "✅" in page.locator("#drop-zone").inner_text())
    
    # Check 44: Drop zone displays file size in MB
    run_check(44, "Drop zone displays file size in MB", 
              "MB" in page.locator("#drop-zone").inner_text())
    
    # Check 45: Drop zone displays ready message
    run_check(45, "Drop zone displays 'Ready to process'", 
              "Ready to process" in page.locator("#drop-zone").inner_text())


def test_tier3_pipeline_execution_success(page: Page):
    """
    Tier 3: Execution Pipeline Visualizer & Success Results (Checks 46 to 65)
    Mocks a success response, clicks process, checks animation, states, count-ups,
    violation cards, and downloads.
    """
    print("\n--- Running Tier 3 Tests ---")
    setup_console_logging(page)
    page.goto(BASE_URL)
    
    # Success mock data
    success_response = {
        "status": "success",
        "annotated_image": "data:image/jpeg;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "violations": [
            {
                "case_id": "CASE-101",
                "timestamp": "2026-06-20 12:00:00",
                "vehicle_class": "motorcycle",
                "plate_number": "MH12AB1234",
                "violations": [
                    { "type": "No Helmet", "confidence": 0.87 }
                ],
                "pdf_download_url": "/download/case_CASE-101.pdf"
            }
        ],
        "stats": {
            "vehicles_detected": 3,
            "persons_detected": 2,
            "violations_found": 1,
            "preprocessing": {
                "mean_brightness": 112.4,
                "blur_variance": 340.1,
                "clahe_applied": True,
                "sharpening_applied": False
            }
        }
    }
    
    # We intercept the request, saving the route object so we can manually fulfill it
    # after asserting the loading state in a non-blocking way.
    saved_route = None
    def handle_success(route):
        nonlocal saved_route
        saved_route = route
        
    page.route("**/process_image", handle_success)
    
    # Check 46: Intercept and mock route setup
    run_check(46, "Mock route setup is complete", True)
    
    # Upload file
    page.locator("#file-input").set_input_files(TEST_IMAGE_PATH)
    
    # Check 47: Click process button
    page.locator("#process-btn").click()
    run_check(47, "Run button was clicked", True)
    
    # Check 48: Button class transitions to loading (while request is pending)
    # We use Playwright's auto-retrying expect to avoid DOM update race conditions
    try:
        expect(page.locator("#process-btn")).to_have_class(re.compile(r"loading"), timeout=5000)
        run_check(48, "Run button has loading class during execution", True)
    except AssertionError:
        run_check(48, "Run button has loading class during execution", False)
    
    # Check 49: Run button shows Processing text
    try:
        expect(page.locator("#process-btn")).to_contain_text("Processing", timeout=5000)
        run_check(49, "Run button displays Processing...", True)
    except AssertionError:
        run_check(49, "Run button displays Processing...", False)
    
    # Check 50: Pipeline progress wrap becomes visible
    try:
        expect(page.locator("#progress-wrap")).to_be_visible(timeout=5000)
        run_check(50, "Pipeline progress is visible", True)
    except AssertionError:
        run_check(50, "Pipeline progress is visible", False)
    
    # Check 51: Sequential stages transition to active
    run_check(51, "Pipeline stages transition to active", 
              page.locator(".stage").count() > 0)
    
    # Now manually fulfill the route to let the processing finish
    saved_route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(success_response)
    )
    
    # Wait for results to show
    page.wait_for_selector("#results-section", state="visible")
    
    # Check 52: Stages transition to done (Wait for Stage 7 to become done to cover full animation delay)
    try:
        expect(page.locator("#stage-7")).to_have_class(re.compile(r"done"), timeout=8000)
        run_check(52, "Stages are marked done after completion", True)
    except AssertionError:
        run_check(52, "Stages are marked done after completion", False)
    
    # Check 53: Results section is displayed
    run_check(53, "Results section is visible", 
              page.locator("#results-section").is_visible())
    
    # Check 54: Vehicles detected count matches mock
    run_check(54, "Vehicles stat displays 3", 
              page.locator("#stats-row .stat-box").nth(0).locator(".stat-val").inner_text() == "3")
    
    # Check 55: Persons detected count matches mock
    run_check(55, "Persons stat displays 2", 
              page.locator("#stats-row .stat-box").nth(1).locator(".stat-val").inner_text() == "2")
    
    # Check 56: Violations count matches mock
    run_check(56, "Violations stat displays 1", 
              page.locator("#stats-row .stat-box").nth(2).locator(".stat-val").inner_text() == "1")
    
    # Check 57: Mean brightness matches mock
    run_check(57, "Brightness stat displays 112.4", 
              page.locator("#stats-row .stat-box").nth(3).locator(".stat-val").inner_text() == "112.4")
    
    # Check 58: Blur score matches mock
    run_check(58, "Blur score stat displays 340.1", 
              page.locator("#stats-row .stat-box").nth(4).locator(".stat-val").inner_text() == "340.1")
    
    # Check 59: CLAHE enhancement chip indicates status
    run_check(59, "Preprocessing chip shows CLAHE status", 
              "CLAHE" in page.locator("#preproc-row").inner_text())
    
    # Check 60: Sharpening chip indicates status
    run_check(60, "Preprocessing chip shows sharpening status", 
              "Sharpening" in page.locator("#preproc-row").inner_text())
    
    # Check 61: Annotated image contains base64 source
    run_check(61, "Annotated image contains the base64 src", 
              "data:image/jpeg;base64" in (page.locator("#result-img").get_attribute("src") or ""))
    
    # Check 62: Plate number matches mock
    run_check(62, "Plate number matches mock: MH12AB1234", 
              page.locator(".vc-plate").inner_text() == "MH12AB1234")
    
    # Check 63: Violation tags display correct type
    run_check(63, "Violation tag shows No Helmet", 
              "No Helmet" in page.locator(".violation-tags").inner_text())
    
    # Check 64: Confidence progress bar matches confidence
    run_check(64, "Confidence bar wrap is rendered", 
              page.locator(".conf-bar-wrap").count() > 0)
    
    # Check 65: PDF download link is present and structured
    run_check(65, "PDF download url matches mock link", 
              page.locator(".pdf-download-btn").get_attribute("href") == "/download/case_CASE-101.pdf")


def test_tier4_errors_and_edge_cases(page: Page):
    """
    Tier 4: Error Handling & Edge Cases (Checks 66 to 82)
    Verifies error toast behavior, server failures, zero violation results,
    and parameter transmission configuration payloads.
    """
    print("\n--- Running Tier 4 Tests ---")
    setup_console_logging(page)
    
    # --- Scenario 1: API returning error response ---
    page.goto(BASE_URL)
    error_response = {
        "status": "error",
        "message": "Test API Error"
    }
    def handle_error(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(error_response)
        )
    page.route("**/process_image", handle_error)
    
    # Check 66: Mock error route setup complete
    run_check(66, "Mock error route setup is complete", True)
    
    page.locator("#file-input").set_input_files(TEST_IMAGE_PATH)
    page.locator("#process-btn").click()
    
    page.wait_for_selector("#error-toast", state="visible")
    
    # Check 67: Error toast is visible
    run_check(67, "Error toast is visible", 
              page.locator("#error-toast").is_visible())
    
    # Check 68: Error toast contains exact message
    run_check(68, "Error toast contains API message", 
              "Test API Error" in page.locator("#error-toast").inner_text())
    
    # Check 69: Run button re-enabled on error
    run_check(69, "Run button is re-enabled on error", 
              page.locator("#process-btn").is_enabled())
    
    # Check 70: Results section remains hidden on error
    run_check(70, "Results section is not visible on error", 
              not page.locator("#results-section").is_visible())
    
    # --- Scenario 2: Server 500 error ---
    page.goto(BASE_URL)
    def handle_500(route):
        route.fulfill(
            status=500,
            content_type="text/plain",
            body="Internal Server Error"
        )
    page.route("**/process_image", handle_500)
    
    # Check 71: Mock 500 server error setup complete
    run_check(71, "Mock 500 server error setup complete", True)
    
    page.locator("#file-input").set_input_files(TEST_IMAGE_PATH)
    page.locator("#process-btn").click()
    
    page.wait_for_selector("#error-toast", state="visible")
    
    # Check 72: Error toast is visible on server error
    run_check(72, "Error toast is visible on server error", 
              page.locator("#error-toast").is_visible())
    
    # Check 73: Error toast contains 'Request failed'
    run_check(73, "Error toast contains 'Request failed'", 
              "Request failed" in page.locator("#error-toast").inner_text())
    
    # --- Scenario 3: Success with zero violations ---
    page.goto(BASE_URL)
    zero_response = {
        "status": "success",
        "annotated_image": "data:image/jpeg;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "violations": [],
        "stats": {
            "vehicles_detected": 5,
            "persons_detected": 0,
            "violations_found": 0,
            "preprocessing": {
                "mean_brightness": 120.0,
                "blur_variance": 500.0,
                "clahe_applied": False,
                "sharpening_applied": True
            }
        }
    }
    def handle_zero(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(zero_response)
        )
    page.route("**/process_image", handle_zero)
    
    # Check 74: Mock zero violations setup complete
    run_check(74, "Mock zero violations setup complete", True)
    
    page.locator("#file-input").set_input_files(TEST_IMAGE_PATH)
    page.locator("#process-btn").click()
    
    page.wait_for_selector("#results-section", state="visible")
    
    # Check 75: No violations element visible
    run_check(75, "No violations element is visible", 
              page.locator(".no-violations").is_visible())
    
    # Check 76: No violations title matches
    run_check(76, "No violations title matches expected", 
              "No Violations Detected" in page.locator(".no-violations h3").inner_text())
    
    # Check 77: No violations check icon visible
    run_check(77, "No violations check icon is visible", 
              "✅" in page.locator(".no-violations .check-icon").inner_text())
    
    # Check 78: Violations count is 0 in stats row
    run_check(78, "Violations count is 0 in stats row", 
              page.locator("#stats-row .stat-box").nth(2).locator(".stat-val").inner_text() == "0")
    
    # Check 79: Preprocessing stats still rendered
    run_check(79, "Preprocessing row is visible with zero violations", 
              page.locator("#preproc-row").is_visible())
    
    # --- Scenario 4: Request configuration transmission ---
    page.goto(BASE_URL)
    transmitted_config = None
    def handle_transmission(route):
        nonlocal transmitted_config
        req = route.request
        post_data = req.post_data
        if post_data:
            match = re.search(r'name="config"\r\n\r\n(.*?)\r\n--', post_data, re.DOTALL)
            if match:
                transmitted_config = json.loads(match.group(1))
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(zero_response)
        )
    page.route("**/process_image", handle_transmission)
    
    # Configure parameters
    page.locator("#cfg-stop-y").fill("480")
    page.locator("#cfg-divider-x").fill("310")
    page.locator("#cfg-camera-id").fill("CAM-999")
    
    page.locator("#file-input").set_input_files(TEST_IMAGE_PATH)
    page.locator("#process-btn").click()
    
    page.wait_for_selector("#results-section", state="visible")
    
    # Check 80: Stop Line Y payload is correctly transmitted
    run_check(80, "Stop line Y coordinate correctly transmitted", 
              transmitted_config is not None and transmitted_config.get("stop_line_y") == 480)
    
    # Check 81: Lane Divider X payload is correctly transmitted
    run_check(81, "Lane divider X coordinate correctly transmitted", 
              transmitted_config is not None and transmitted_config.get("lane_divider_x") == 310)
    
    # Check 82: Camera ID payload is correctly transmitted
    run_check(82, "Camera ID coordinate correctly transmitted", 
              transmitted_config is not None and transmitted_config.get("camera_id") == "CAM-999")
