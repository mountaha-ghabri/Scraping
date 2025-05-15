import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

print("Starting imports...")
import os
import re
import time
import random
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from chromedriver_autoinstaller import install

print("Installing ChromeDriver...")
install()
print("ChromeDriver installation completed")

print("\nIMPORTANT: First steps:")
print("1. Close ALL Chrome windows")
print("2. Open a new Command Prompt (cmd.exe, not PowerShell)")
print("3. Run this command:")
print('"chrome path in your machine" --remote-debugging-port=9222 --user-data-dir="C:\\selenium\\ChromeProfile"')
print("\n4. In the Chrome window that opens:")
print("   - Make sure you're logged into LinkedIn")
print("   - Navigate to: https://www.linkedin.com/search/results/people/?geoUrn=%5B%22102134353%22%5D&keywords=finance&origin=FACETED_SEARCH") #linkedin search results example
print("   - Make sure you can see the search results")
input("\nAfter completing these steps, press Enter to continue...")

print("Setting up Chrome options...")
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
chrome_options.add_experimental_option("debuggerAddress", "IP:PORT") #Change IP:PORT with yours

print("Initializing Chrome driver...")
try:
    driver = webdriver.Chrome(options=chrome_options)
    print("Chrome driver initialized successfully")
    
    # Verify we're on LinkedIn search page
    current_url = driver.current_url
    if "linkedin.com/search/results" not in current_url:
        raise Exception("Please navigate to the LinkedIn search results page before continuing")
    
    print("\nReady to start scraping!")
    input("Press Enter to begin...")
    
except Exception as e:
    print(f"Error initializing Chrome driver: {e}")
    raise

def random_sleep(min_seconds=3, max_seconds=7): #this is a mechanism to bypass linkedin's anti-scraping defense
    time.sleep(random.uniform(min_seconds, max_seconds))

def clean_text(text):
    if not text:
        return "N/A"
    return re.sub(r'\s+', ' ', text).strip()

def scroll_to_bottom(driver):
    print("Scrolling through page to load all content...") #to simulate a human behavior
    
    try:
        # Initial wait for page load
        time.sleep(3)
        
        # Get initial height
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        # Scroll in smaller chunks with pauses
        for _ in range(4):  # Increased number of scroll attempts
            # Scroll down in smaller chunks
            for i in range(0, last_height, 300):  # Smaller chunk size
                driver.execute_script(f"window.scrollTo(0, {i})")
                time.sleep(0.3)  # Small pause between chunk scrolls
            
            # Force scroll to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Scroll back up in chunks
            for i in range(last_height, 0, -300):
                driver.execute_script(f"window.scrollTo(0, {i})")
                time.sleep(0.3)
            
            # Calculate new scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            time.sleep(1)
        
        # Final scroll sequence
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
    except Exception as e:
        print(f"Warning: Error during scrolling: {e}")
    
    print("Finished scrolling")

def extract_profile_data(result):
    try:
        profile_data = {
            "name": "N/A",
            "linkedin_url": "N/A",
            "location": "N/A",
            "title": "N/A",
            "company": "N/A"
        }
        
        # Scroll the result into view and wait for content
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", result)
        time.sleep(1)
        
        # Print full text for debugging
        print("\nFull text content:")
        full_text = result.text
        print(full_text)
        
        if not full_text:
            print("Warning: Empty text content")
            return None
            
        # Split into lines and clean up
        lines = [clean_text(line) for line in full_text.split('\n') if clean_text(line)]
        
        if not lines:
            print("Warning: No text lines found after cleaning")
            return None
            
        # Find profile link and name
        anchors = result.find_elements(By.TAG_NAME, "a")
        for anchor in anchors:
            try:
                href = anchor.get_attribute('href')
                if href and '/in/' in href:
                    profile_data["linkedin_url"] = href.split('?')[0]
                    
                    # Try different ways to get the name
                    anchor_text = clean_text(anchor.text)
                    if anchor_text and not any(skip in anchor_text.lower() for skip in ['view', 'profile', 'connect', 'message']):
                        profile_data["name"] = anchor_text
                        break
                    
                    # Try getting name from spans inside anchor
                    spans = anchor.find_elements(By.TAG_NAME, "span")
                    for span in spans:
                        span_text = clean_text(span.text)
                        if span_text and not any(skip in span_text.lower() for skip in ['view', 'profile', 'connect', 'message']):
                            profile_data["name"] = span_text
                            break
            except:
                continue
        
        # If we still don't have a name, try to find it in the first few lines
        if profile_data["name"] == "N/A":
            for line in lines[:3]:  # Check first 3 lines
                if not any(skip in line.lower() for skip in ['view', 'profile', 'connect', 'message', '• 2nd', '• 3rd', 'mutual']):
                    profile_data["name"] = line
                    break
        
        # Process each line for information
        for line in lines:
            # Skip empty lines and common irrelevant text
            if not line or any(skip in line.lower() for skip in [
                'view profile', 'connect', 'message', 'follow', 'mutual connection',
                '• 2nd', '• 3rd', 'degree connection', 'mutual'
            ]):
                continue
            
            # Look for location
            if any(loc in line.lower() for loc in ['tunisia', 'tunis', 'sfax', 'sousse']): #i wanted more specific results
                profile_data["location"] = line
                continue
            
            # Look for title/company with "at"
            if " at " in line:
                parts = line.split(" at ")
                if len(parts) == 2:
                    # Check if we already have a title
                    if profile_data["title"] == "N/A":
                        profile_data["title"] = clean_text(parts[0])
                    profile_data["company"] = clean_text(parts[1])
                    continue
            
            # Look for Current/Past/Skills prefixes
            for prefix in ['Current:', 'Past:', 'Skills:']:
                if line.startswith(prefix):
                    title = line.replace(prefix, '').strip()
                    if " at " in title:
                        parts = title.split(" at ")
                        if len(parts) == 2:
                            if profile_data["title"] == "N/A":
                                profile_data["title"] = clean_text(parts[0])
                            profile_data["company"] = clean_text(parts[1])
                    else:
                        if profile_data["title"] == "N/A":
                            profile_data["title"] = title
                    break
            
            # Look for title indicators if we still don't have one
            if profile_data["title"] == "N/A" and any(keyword in line.lower() for keyword in [
                'student', 'engineer', 'manager', 'analyst', 'consultant', 'director',
                'finance', 'accounting', 'professor', 'teacher', 'phd', 'master'
            ]):
                profile_data["title"] = line
        
        # Return the profile if we found either a name or title
        if profile_data["name"] != "N/A" or profile_data["title"] != "N/A":
            return profile_data
            
        print("Warning: Could not find name or title in profile")
        return None
        
    except Exception as e:
        print(f"Error in extract_profile_data: {e}")
        return None

def save_to_csv(data, filename="linkedin_finance_profiles.csv"):
    df_new = pd.DataFrame(data)
    df_new.drop_duplicates(subset="linkedin_url", inplace=True)
    
    try:
        # Try to read existing CSV
        if os.path.exists(filename):
            df_existing = pd.read_csv(filename)
            # Combine existing and new data
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            # Remove duplicates based on LinkedIn URL
            df_combined.drop_duplicates(subset="linkedin_url", inplace=True)
            df_combined.to_csv(filename, index=False)
            print(f"✅ Appended to existing CSV - Total profiles: {len(df_combined)}")
        else:
            # If no existing file, create new one
            df_new.to_csv(filename, index=False)
            print(f"✅ Created new CSV with {len(df_new)} profiles")
    except Exception as e:
        # If there's any error, save to a new timestamped file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_filename = f"linkedin_finance_profiles_{timestamp}.csv"
        df_new.to_csv(backup_filename, index=False)
        print(f"⚠️ Error appending to existing CSV: {e}")
        print(f"✅ Saved {len(df_new)} profiles to backup file: {backup_filename}")

def check_and_handle_login(driver):
    # Check if we're on login page
    if "login" in driver.current_url.lower() or "sign in" in driver.page_source.lower():
        print("\n⚠️ LinkedIn login page detected!")
        print("Please follow these steps:")
        print("1. Go to your Chrome window")
        print("2. Log in to LinkedIn")
        print("3. Navigate back to the search results")
        input("Once you're logged in and can see search results, press Enter to continue...")
        return True
    return False

def process_results_with_retry(driver, results, all_data):
    successful_extractions = 0
    
    for idx, result in enumerate(results, 1):
        max_retries = 3
        for retry in range(max_retries):
            try:
                print(f"\nProcessing result {idx}/{len(results)} (attempt {retry + 1}/{max_retries})")
                
                # Scroll the result into view
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", result)
                time.sleep(1)  # Wait for lazy loading
                
                # Additional scroll around the element
                element_location = result.location['y']
                driver.execute_script(f"window.scrollTo(0, {max(0, element_location - 300)});")
                time.sleep(0.5)
                driver.execute_script(f"window.scrollTo(0, {element_location + 100});")
                time.sleep(0.5)
                
                profile_data = extract_profile_data(result)
                if profile_data:
                    all_data.append(profile_data)
                    successful_extractions += 1
                    print(f"Extracted: {profile_data['name']} - {profile_data['title']} - {profile_data['location']}")
                    break  # Success, move to next profile
                else:
                    print(f"Attempt {retry + 1}: Failed to extract data, retrying...")
                    
            except Exception as e:
                print(f"Error on attempt {retry + 1}: {e}")
                if retry == max_retries - 1:
                    print(f"Failed to process result {idx} after {max_retries} attempts")
                time.sleep(1)
    
    return successful_extractions

def scrape_search_results(start_page=1, max_pages=None):
    all_data = []
    current_page = start_page
    base_url = driver.current_url
    
    # Extract the base URL without page parameter and sid
    if "page=" not in base_url:
        base_url = base_url + "&page=1"
    base_url = re.sub(r'&page=\d+', '', base_url)
    base_url = re.sub(r'&sid=[^&]+', '', base_url)  # Remove sid parameter as it changes

    while True:
        try:
            # Construct the URL for the current page
            page_url = f"{base_url}&page={current_page}"
            print(f"\nNavigating to page {current_page}")
            print(f"URL: {page_url}")
            
            # Navigate to the page and wait for initial load
            driver.get(page_url)
            time.sleep(5)  # Initial wait time
            
            try:
                # Wait for the search results container
                print("Waiting for search results to load...")
                list_container = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ul[role='list']"))
                )
                
                # Initial scroll through page
                scroll_to_bottom(driver)
                time.sleep(2)
                
                # Try to find results multiple times
                max_result_attempts = 3
                best_results = []
                max_results_found = 0
                
                for attempt in range(max_result_attempts):
                    results = list_container.find_elements(By.TAG_NAME, "li")
                    print(f"Attempt {attempt + 1}: Found {len(results)} results")
                    
                    if len(results) > max_results_found:
                        max_results_found = len(results)
                        best_results = results
                    
                    if len(results) >= 10:  # Full page of results
                        break
                        
                    print(f"Attempting to load more results...")
                    scroll_to_bottom(driver)
                    time.sleep(2)
                
                if not best_results:
                    print("No results found after multiple attempts")
                    break
                
                print(f"Processing {len(best_results)} results")
                
                # Process results with retry logic
                successful_extractions = process_results_with_retry(driver, best_results, all_data)
                
                # Save progress after each page
                if successful_extractions > 0:
                    save_to_csv(all_data)
                    print(f"Progress saved - {len(all_data)} new profiles collected so far")
                    print(f"Successfully extracted {successful_extractions} profiles from page {current_page}")
                
                # Handle no successful extractions
                if successful_extractions == 0:
                    print("No profiles extracted from this page")
                    response = input("Would you like to retry this page? (y/n): ")
                    if response.lower() == 'y':
                        continue  # Retry the same page
                    #in case linkedin detects robot behavior
                    response = input("Would you like to move to the next page? (y/n): ")
                    if response.lower() != 'y':
                        break
                
                # Optional: stop at max_pages if specified
                if max_pages and current_page >= start_page + max_pages - 1:
                    print(f"Reached maximum page limit of {max_pages} pages from start page")
                    break
                
                current_page += 1
                time.sleep(3)  # Wait before next page
                
            except TimeoutException:
                print(f"Timeout waiting for results on page {current_page}")
                response = input("Would you like to retry this page? (y/n): ")
                if response.lower() == 'y':
                    continue  # Retry the same page
                else:
                    break
                
        except KeyboardInterrupt:
            print("\nUser interrupted the scraping process")
            break
            
        except Exception as e:
            print(f"Error on page {current_page}: {e}")
            if all_data:
                save_to_csv(all_data)
            
            response = input("Would you like to retry this page? (y/n): ")
            if response.lower() == 'y':
                continue  # Retry the same page
            else:
                break
    
    print(f"\nScraping completed!")
    print(f"Total new profiles collected: {len(all_data)}")
    return all_data

try:
    print("\n=== Starting LinkedIn Scraper ===")
    
    # Ask user for starting page
    start_page = int(input("Enter the page number to start from (default is 1): ") or "1")
    max_pages = int(input("Enter the number of pages to scrape (press Enter for unlimited): ") or "0")
    
    all_data = scrape_search_results(
        start_page=start_page,
        max_pages=max_pages if max_pages > 0 else None
    )
    
    if all_data:
        save_to_csv(all_data)
        print("✅ Scraping completed successfully!")
    else:
        print("⚠️ No new data was collected")

except Exception as e:
    print(f"❌ Fatal error: {e}")
    raise

finally:
    print("Closing Chrome driver...")
    driver.quit()
    print("Chrome driver closed successfully")
