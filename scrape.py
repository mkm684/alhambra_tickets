import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

import datetime
import pygame
import threading

# ===== CONFIGURATION =====
# DEBUG MODE - Set to True to see what's happening step by step
DEBUG = True
DEBUG_DELAY = 3  # Seconds to pause after each major step (only used when DEBUG=True)

# Ticket types available:
TICKET_TYPES = {
    'general_alhambra': 'https://compratickets.alhambra-patronato.es/reservarEntradas.aspx?opc=142&gid=432&lg=es-ES&ca=0&m=GENERAL',
    'gardens_generalife_alcazaba': 'https://tickets.alhambra-patronato.es/producto/jardines-generalife-y-alcazaba/',
    'default': 'https://compratickets.alhambra-patronato.es/reservarEntradas.aspx/?opc=2&gid=2&lg=es&ca=0'
}

# SELECT YOUR TICKET TYPE HERE
ticket_type = 'general_alhambra'  # Change to 'gardens_generalife_alcazaba' or 'default'
url_alhambra = TICKET_TYPES[ticket_type]

# audio si hay entradas
clip_good = './alhambra.wav'
clip_error = './error.wav'

# Desired visit dates - specify as (month, day) tuples
# Example: (5, 8) = May 8th, (5, 9) = May 9th, (6, 8) = June 8th, etc.
# IMPORTANT: Configure this together with calendarPressCount below!
mis_dias = {
    (6, 8),   # June 8th
    (6, 9),   # June 9th
    (6, 10),  # June 10th
    (6, 11),  # June 11th
    (6, 12),  # June 12th
}

# Calendar navigation: How many times to press the NEXT button to reach your target month
# Current month shown: May (0 presses)
# June: 1 press
# July: 2 presses
# August: 3 presses, etc.
# MUST MATCH the months in mis_dias above!
calendarPressCount = 1  # Set to 1 because we're looking at June dates

n_entradas = 2  # Number of tickets to book

print(f"Looking for tickets of type: {ticket_type}")
print(f"URL: {url_alhambra}")
print(f"Desired dates: {mis_dias}")

def create_driver():
    """Create a Chrome driver with proper options"""
    chrome_options = Options()
    
    # Disable the "Chrome is being controlled by automated test software" notification
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    # Optional: Disable notifications (can help with some websites)
    prefs = {"profile.default_content_setting_values.notifications": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Optional: Uncomment these if you want headless mode (no visible window)
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--disable-gpu")
    
    # Use webdriver-manager to automatically get the correct ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    if DEBUG:
        print("  ✓ Chrome driver created with automation options disabled")
    
    return driver

def wait_for_captcha():
    """
    Check if CAPTCHA is present. If found, wait for user to solve it manually.
    Only pauses when CAPTCHA is actually detected.
    """
    try:
        captcha_elements = driver.find_elements(By.XPATH, '//*[contains(@class, "captcha") or contains(@class, "recaptcha")]')
        if captcha_elements:
            print("\n⚠️  CAPTCHA DETECTED!")
            print("Please solve the CAPTCHA manually in the browser window.")
            print("Once solved, press Enter here to continue...")
            input()
            return True
    except:
        pass
    return False

def press_next_button(times=1):
    """
    Press the calendar next button to navigate to future months.
    Args:
        times: Number of times to press the next button
    """
    try:
        for i in range(times):
            # Find and click the next button
            next_button = driver.find_element(By.XPATH, '//a[contains(@class, "next")]')
            print(f"  ✓ Pressing next button... ({i+1}/{times})")
            next_button.click()
            time.sleep(2)  # Wait for calendar to update
        print(f"  ✓ Calendar navigated {times} month(s) forward")
        return True
    except Exception as e:
        if DEBUG:
            print(f"  ⚠️  Could not find/press next button: {e}")
        return False

def click_paso1_button_if_exists():
    """
    Try to click 'Ir a paso 1' button if it exists.
    Returns True if button was clicked, False otherwise.
    """
    try:
        boton_paso1 = driver.find_element(By.NAME, "ctl00$ContentMaster1$ucReservarEntradasBaseAlhambra1$btnIrPaso1")
        if boton_paso1.is_displayed():
            print("  ✓ Found 'Ir a paso 1' button, clicking it...")
            boton_paso1.click()
            time.sleep(3)
            return True
    except:
        pass
    return False

def calendar_is_visible():
    """
    Check if the calendar has appeared on the page.
    Returns True if calendar is visible, False otherwise.
    """
    try:
        calendar = driver.find_element(By.ID, "ctl00_ContentMaster1_ucReservarEntradasBaseAlhambra1_ucCalendarioPaso1_calendarioFecha")
        return calendar.is_displayed()
    except:
        return False

def sacar_entrada():
    print("[Step 1] Opening website...")
    driver.get(url_alhambra)
    time.sleep(5)
    if DEBUG:
        print(f"  ⏸️  DEBUG MODE: Pausing for {DEBUG_DELAY}s to see the page")
        time.sleep(DEBUG_DELAY)
    
    # Keep clicking "Ir a paso 1" button until calendar appears
    print("[Step 1.5] Clicking 'Ir a paso 1' button (will repeat if needed)...")
    max_attempts = 10
    attempt = 0
    while attempt < max_attempts and not calendar_is_visible():
        if click_paso1_button_if_exists():
            attempt += 1
            print(f"  Attempt {attempt}: Button clicked, waiting and checking for calendar...")
            time.sleep(2)  # Short wait between button clicks
        else:
            print("  ℹ️  Button not found, checking if calendar is visible...")
            time.sleep(2)
            break
    
    if calendar_is_visible():
        print("  ✓ Calendar is now visible!")
        if DEBUG:
            print(f"  ⏸️  DEBUG MODE: Pausing for {DEBUG_DELAY}s to see the calendar")
            time.sleep(DEBUG_DELAY)
    else:
        print("  ⚠️  Calendar not yet visible, but proceeding...")
    
    # Check for CAPTCHA ONCE after all button clicks (not during each click)
    print("[Step 1.75] Checking for CAPTCHA...")
    if wait_for_captcha():
        print("  ✓ CAPTCHA was solved")
        time.sleep(2)
    else:
        print("  ℹ️  No CAPTCHA found, proceeding to calendar navigation")
    
    # Navigate calendar to the target month
    print(f"[Step 1.9] Navigating calendar to target dates (pressing next {calendarPressCount} time(s))...")
    press_next_button(calendarPressCount)
    time.sleep(3)
    
    if DEBUG:
        print(f"  ⏸️  DEBUG MODE: Pausing for {DEBUG_DELAY}s to see the calendar after navigation")
        time.sleep(DEBUG_DELAY)
    
    # chequea si hay libres tus dias
    try:
        print("[Step 2] Checking available dates...")
        naranjas = driver.find_elements(By.XPATH, '//td[@data-estado="naranja"]')
        print(f"  Found {len(naranjas)} available date cells (data-estado='naranja')")
        dias_dispo = []
        
        for n in naranjas:
            try:
                day = int(n.text)
                # Get the current month from mis_dias to check against
                target_months = set(month for month, day_val in mis_dias)
                
                # Check if date matches any of our desired dates
                # After pressing next N times, we're viewing month+N
                for target_month in target_months:
                    if (target_month, day) in mis_dias:
                        dias_dispo.append(day)
                        if DEBUG:
                            print(f"    ✓ Found desired date: {target_month}/{day}")
                        break
            except ValueError:
                continue
        
        if len(dias_dispo) > 0:
            print(f"✅ TICKETS FOUND for days: {dias_dispo}")
            if DEBUG:
                print(f"  ⏸️  DEBUG MODE: Pausing for {DEBUG_DELAY}s to see the found tickets")
                time.sleep(DEBUG_DELAY)
            return True
        else:
            if DEBUG:
                print(f"  ℹ️  No matching dates found. Pausing for {DEBUG_DELAY}s")
                time.sleep(DEBUG_DELAY)
            return False

    except Exception as e:
        print(f"❌ Error checking dates: {e}")
        if DEBUG:
            import traceback
            traceback.print_exc()
        return False

def play_clip(clip, sleep_time, times=5):
    """Play audio notification"""
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(clip)
        for _ in range(times):
            pygame.mixer.music.play()
            time.sleep(sleep_time)
    except Exception as e:
        print(f"Could not play sound: {e}")

# Main loop
if __name__ == "__main__":
    print("=" * 60)
    print(f"DEBUG MODE: {'ON ✓' if DEBUG else 'OFF'}")
    if DEBUG:
        print(f"Debug delay: {DEBUG_DELAY} seconds between steps")
    print("=" * 60)
    
    for j in range(50):
        print(f'\n{"="*60}')
        print(f'Session {j} - {datetime.datetime.now().ctime()}')
        print("="*60)
        driver = None
        try:
            driver = create_driver()

            for i in range(1000):
                if sacar_entrada():
                    print('🎉 ENTRADAS ENCONTRADAS!')
                    play_clip(clip_good, sleep_time=6, times=3)
                    print("\n⚠️  Chrome window is still open - tickets found! Check the browser.")
                    print("Press Ctrl+C to exit or let the script continue...\n")
                    break
                else:
                    if i % 20 == 0:
                        print(f'{i} attempts - No tickets yet - {datetime.datetime.now().ctime()}')
                    time.sleep(5)

        except Exception as e:
            print(f'❌ ERROR in session {j}: {e}')
            print(f'Time: {datetime.datetime.now().ctime()}')
            print("⚠️  Chrome window remains open for inspection")
            if driver:
                print("You can manually close the browser or the script will continue to next session...")
            time.sleep(10)  # Wait before retrying
