import time
import re
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from app.core.plugin_base import PluginBase

class DealsPlugin(PluginBase):
    def on_load(self):
        self.running = False

    def shutdown(self):
        pass

    def is_busy(self) -> bool:
        return self.running

    def heartbeat(self):
        return {"status": "running" if self.running else "idle", "progress": "N/A", "message": "Price Engine Ready"}

    def execute(self, command: str, context: dict) -> str:
        # Debug Logger
        import logging
        logging.basicConfig(filename='debug_deals.log', level=logging.DEBUG, format='%(asctime)s %(message)s')
        logging.info(f"Starting deals command for: {command}")
        
        self.running = True
        try:
            # Parse command: /deals iphone 15
            product = command.replace("/deals", "").strip()
            if not product:
                return "Usage: /deals <product name>"
            
            # Scrape sequentially to prevent ChromeDriver crashes/resource exhaustion
            # All scrapers now return a LIST of dicts: [{source, price, link, name}, ...]
            ebay_results = self._safe_scrape(self._scrape_ebay, product) or []
            amzn_results = self._safe_scrape(self._scrape_amazon, product) or []
            sd_results = self._safe_scrape(self._scrape_slickdeals, product) or []
            
            # Combine all candidates
            candidates = []
            candidates.extend(ebay_results)
            candidates.extend(amzn_results)
            candidates.extend(sd_results)
            
            if not candidates:
                 return f"Could not find valid prices for '{product}' on Amazon, eBay, or Slickdeals. (Websites might be blocking the bot)."
            
            # Use Gemini to find the best deal if available
            best_deal = self._analyze_with_gemini(candidates, product)
            
            if best_deal:
                winner = best_deal
                reason = "AI Selected for Best Value"
                return f"Found best deal on {winner['source']}: ${winner['price']}\nProduct: {winner['name']}\nReason: {reason}\nLink: {winner['link']}"
            else:
                return f"I found {len(candidates)} listings, but my AI analysis determined they were likely accessories or cases, not the actual '{product}'. Please try a more specific query."

        finally:
            self.running = False
            pass

    def _safe_scrape(self, scrape_func, product):
        import logging
        driver = None
        try:
            logging.info(f"Scraping {scrape_func.__name__}...")
            driver = self._get_driver()
            result = scrape_func(driver, product)
            logging.info(f"Result from {scrape_func.__name__}: Found {len(result) if result else 0} items")
            return result
        except Exception as e:
            logging.error(f"Scrape Error ({scrape_func.__name__}): {e}")
            print(f"Scrape Error ({scrape_func.__name__}): {e}")
            return []
        finally:
            if driver:
                try:
                    driver.quit()
                    logging.info("Driver closed.")
                except:
                    pass

    def _analyze_with_gemini(self, candidates, product):
        import os
        import google.generativeai as genai
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return None
            
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            prompt = f"""
            You are a smart shopping assistant. I am searching for: "{product}".
            
            Here are the candidate products found on Amazon/eBay:
            {candidates}
            
            YOUR TASK:
            1.  **FILTER**: Identify which candidates are the **ACTUAL DEVICE** and which are accessories/cases.
            2.  **EXCLUDE**: Discard any item that is a case, skin, cover, or accessory.
            3.  **SELECT**: From the valid actual devices, pick the one with the **lowest price**.
            
            If NO valid actual devices are found (all are cases), return {{ "error": "No valid products found" }}.
            
            Otherwise, return the JSON object of the best winner EXACTLY as it appears in the list.
            
            Example Output Format:
            {{
                "source": "Amazon",
                "price": 999.00,
                "link": "...",
                "name": "Iphone 16 Pro 128GB"
            }}
            
            Return ONLY valid JSON. No markdown formatting.
            """
            
            response = model.generate_content(prompt)
            # Robust JSON cleaning
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            import json
            try:
                data = json.loads(text)
                if "error" in data: return None
                return data
            except:
                # Fallback: try eval but be careful
                try:
                    return eval(text)
                except:
                    print(f"JSON Parse Failed. Text: {text}")
                    return None
                
        except Exception as e:
            print(f"Gemini Analysis Failed: {e}")
            return None


    def _get_driver(self):
        options = webdriver.ChromeOptions()
        # Randomized User Agents
        uas = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        options.add_argument(f"user-agent={random.choice(uas)}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--headless") # Reverted to standard headless for stability
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=en-US")
        options.add_argument("--accept-lang=en-US,en;q=0.9")
        # Stability Flags
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        # Force re-install and log to file
        service = Service(ChromeDriverManager().install(), log_output="chromedriver.log")
        driver = webdriver.Chrome(service=service, options=options)
        
        # Additional undetectable scripts
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })
        return driver

    def _parse_price(self, price_str):
        if not price_str: return None
        # Remove $ and , and ' to '
        clean = price_str.replace('$', '').replace(',', '').strip()
        try:
            # Handle range: "10 to 20"
            if ' ' in clean:
                clean = clean.split(' ')[0]
            return float(re.findall(r"\d+\.\d+", clean)[0])
        except:
            return None

    def _scrape_ebay(self, driver, product):
        results = []
        try:
            # Simplified search
            url = f"https://www.ebay.com/sch/i.html?_nkw={product.replace(' ', '+')}&_sop=15"
            driver.get(url)
            
            # Wait for items
            try:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".s-item")))
            except:
                pass 
            
            # 1. Structured Scraping
            items = driver.find_elements(By.CSS_SELECTOR, "li.s-item")
            for item in items:
                if "Shop on eBay" in item.text: continue
                if len(results) >= 5: break
                try:
                    link_elem = item.find_element(By.CSS_SELECTOR, ".s-item__link")
                    title_elem = item.find_element(By.CSS_SELECTOR, ".s-item__title")
                    
                    # Price: try multiple classes
                    price_text = ""
                    try:
                        price_text = item.find_element(By.CSS_SELECTOR, ".s-item__price").text
                    except:
                        continue # No price, skip

                    link = link_elem.get_attribute("href")
                    name = title_elem.text
                    price = self._parse_price(price_text)
                    
                    if price:
                        results.append({"source": "eBay", "price": price, "link": link, "name": name})
                except:
                    continue
            
            # 2. Fuzzy Fallback if 0 results
            if not results:
                print("eBay: Structured scrape failed. Trying fuzzy fallback...")
                links = driver.find_elements(By.TAG_NAME, "a")
                for lnk in links:
                    if len(results) >= 5: break
                    try:
                        href = lnk.get_attribute("href")
                        if href and "/itm/" in href:
                            # Check text for price
                            text = lnk.text
                            # often price is in the link text or parent text
                            if "$" not in text:
                                try:
                                    text = lnk.find_element(By.XPATH, "..").text
                                except:
                                    pass
                            
                            match = re.search(r'\$(\d+\.\d{2})', text)
                            if match:
                                price = float(match.group(1))
                                if price > 10: # filtering junk
                                    results.append({"source": "eBay", "price": price, "link": href, "name": text.split('$')[0].strip()[:50]})
                    except:
                        continue

            if not results:
                # DEBUG: Log page source to check for CAPTCHA/Block
                import logging
                src = driver.page_source[:2000].replace("\n", " ")
                logging.warning(f"eBay found 0 items. Page Source Dump: {src}")
                
            return results
        except Exception as e:
            print(f"eBay Error: {e}")
            return []

    def _scrape_amazon(self, driver, product):
        results = []
        try:
            url = f"https://www.amazon.com/s?k={product.replace(' ', '+')}"
            driver.get(url)
            
            try:
                # Wait for any Result item
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.s-result-item")))
            except:
                pass

            # 1. Structured Scraping
            items = driver.find_elements(By.CSS_SELECTOR, "div.s-result-item[data-component-type='s-search-result']")
            if not items:
                items = driver.find_elements(By.CSS_SELECTOR, "div.s-result-item")
            
            for item in items:
                if len(results) >= 5: break
                try:
                    # Skip if ad holder or special content
                    if "AdHolder" in item.get_attribute("class"): continue

                    # Name & Link
                    try:
                        title_el = item.find_element(By.CSS_SELECTOR, "h2 a")
                        name = title_el.text
                        link = title_el.get_attribute("href")
                    except:
                        continue

                    # Price
                    try:
                        price_el = item.find_element(By.CSS_SELECTOR, ".a-price .a-offscreen")
                        price_text = price_el.get_attribute("textContent")
                    except:
                        # try visible price
                        try:
                            price_text = item.find_element(By.CSS_SELECTOR, ".a-price").text
                        except:
                            continue # no price
                    
                    price = self._parse_price(price_text)
                    
                    if price and link and name:
                        results.append({"source": "Amazon", "price": price, "link": link, "name": name})
                except:
                   continue

            # 2. Fuzzy Fallback
            if not results:
                print("Amazon: Structured scrape failed. Trying fuzzy fallback...")
                links = driver.find_elements(By.TAG_NAME, "a")
                for lnk in links:
                    if len(results) >= 5: break
                    try:
                        href = lnk.get_attribute("href")
                        if href and "/dp/" in href:
                             # Look for price in parent text
                             try:
                                 parent_text = lnk.find_element(By.XPATH, "../../..").text
                                 match = re.search(r'\$(\d+\.\d{2})', parent_text)
                                 if match:
                                     price = float(match.group(1))
                                     if price > 10:
                                         name = lnk.text or "Amazon Product"
                                         results.append({"source": "Amazon", "price": price, "link": href, "name": name})
                             except:
                                 pass
                    except:
                        continue

            if not results:
                # DEBUG: Log page source
                import logging
                src = driver.page_source[:2000].replace("\n", " ")
                logging.warning(f"Amazon found 0 items. Page Source Dump: {src}")

            return results

        except Exception as e:
            print(f"Amazon Scrape Error: {e}")
            return []

    def _scrape_slickdeals(self, driver, product):
        return []
