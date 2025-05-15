from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from chromedriver_autoinstaller import install

print("1. Starting test...")

print("2. Installing ChromeDriver...")
install()

print("3. Setting up Chrome options...")
chrome_options = Options()
chrome_options.add_argument("--start-maximized")

print("4. Initializing Chrome driver...")
try:
    driver = webdriver.Chrome(options=chrome_options)
    print("5. Chrome driver initialized successfully!")
    print("6. Attempting to open Google...")
    driver.get("https://www.google.com")
    print("7. Successfully opened Google!")
    input("Press Enter to close the browser...")
except Exception as e:
    print(f"Error occurred: {e}")
finally:
    try:
        driver.quit()
        print("8. Browser closed successfully!")
    except:
        pass 