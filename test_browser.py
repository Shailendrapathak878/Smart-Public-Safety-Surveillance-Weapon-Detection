from playwright.sync_api import sync_playwright
import time
import os

def test_fastapi_ui():
    print("Starting Playwright UI tests...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Grant camera permissions for webcam testing
        context = browser.new_context(permissions=['camera'])
        page = context.new_page()
        
        # 1. Login page
        print("Navigating to http://127.0.0.1:8000...")
        page.goto("http://127.0.0.1:8000", timeout=30000)
        page.wait_for_selector("#login-view", timeout=30000)
        time.sleep(1)
        page.screenshot(path="screenshot_1_login.png")
        
        # 2. Invalid login
        print("Testing invalid login...")
        page.locator("#login-username").fill("test")
        page.locator("#login-password").fill("wrong")
        page.locator("button[type='submit']").click()
        time.sleep(1)
        page.screenshot(path="screenshot_2_invalid_login.png")
        
        # 3. Valid login
        print("Testing valid login...")
        page.locator("#login-username").fill("admin")
        page.locator("#login-password").fill("admin123")
        page.locator("button[type='submit']").click()
        time.sleep(2)
        page.screenshot(path="screenshot_3_dashboard.png")
        
        # 4. Overview
        print("Testing Overview Navigation...")
        page.locator("li[data-target='overview-section']").click()
        time.sleep(1)
        page.screenshot(path="screenshot_4_overview.png")

        # 5. Live Monitoring
        print("Testing Live Monitoring UI...")
        page.locator("li[data-target='monitoring-section']").click()
        time.sleep(1)
        
        # Test Laptop Webcam (Default)
        print("Testing Laptop Webcam Mode...")
        start_btn = page.locator("#start-monitoring-btn")
        if start_btn.count() > 0:
            start_btn.click()
            time.sleep(3)
            page.screenshot(path="screenshot_5_webcam_running.png")
            page.locator("#stop-monitoring-btn").click()
            time.sleep(1)
            
        # Test Phone/IP Camera
        print("Testing Phone/IP Camera Mode...")
        page.locator("#monitoring-source").select_option("ip_camera")
        time.sleep(1)
        page.screenshot(path="screenshot_6_ip_camera.png")
        
        # 6. Image Analysis
        print("Testing Image Analysis UI...")
        page.locator("li[data-target='image-analysis-section']").click()
        time.sleep(1)
        # Attempt upload if dummy image exists
        if os.path.exists("dummy_upload.png"):
            page.locator("#image-upload").set_input_files("dummy_upload.png")
            time.sleep(1)
            page.locator("#analyze-image-btn").click()
            time.sleep(3)
        page.screenshot(path="screenshot_7_image_analysis.png")

        # 7. Video Analysis
        print("Testing Video Analysis UI...")
        page.locator("li[data-target='video-analysis-section']").click()
        time.sleep(1)
        page.screenshot(path="screenshot_8_video_analysis.png")
        
        # 8. Events
        print("Testing Events UI...")
        page.locator("li[data-target='events-section']").click()
        time.sleep(1)
        page.screenshot(path="screenshot_9_events.png")
        
        # 9. Settings
        print("Testing Settings UI...")
        page.locator("li[data-target='settings-section']").click()
        time.sleep(1)
        page.screenshot(path="screenshot_10_settings.png")
        
        # 10. Logout
        print("Logging out...")
        logout_btn = page.locator("#logout-btn")
        if logout_btn.count() > 0:
            logout_btn.click()
            time.sleep(1)
            page.screenshot(path="screenshot_11_logout.png")
        
        browser.close()
        print("Playwright UI tests completed.")

if __name__ == "__main__":
    test_fastapi_ui()
