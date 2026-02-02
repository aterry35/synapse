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
        self.running = True
        try:
            # Parse command: /deals iphone 15
            product = command.replace("/deals", "").strip()
            if not product:
                return "Usage: /deals <product name>"
            
            # Scrape concurrently using threads
            import concurrent.futures
            
            # Reduce workers to 2 to see if stability improves
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                
                # Wrapper to handle driver lifecycle per thread
                def scrape_wrapper(scrape_func, prod):
                    driver = self._get_driver()
                    try:
                        return scrape_func(driver, prod)
                    finally:
                        try:
                            driver.quit()
                        except:
                            pass

                future_ebay = executor.submit(scrape_wrapper, self._scrape_ebay, product)
                future_amzn = executor.submit(scrape_wrapper, self._scrape_amazon, product)
                future_sd = executor.submit(scrape_wrapper, self._scrape_slickdeals, product)
                
                ebay_price, ebay_link, ebay_name = future_ebay.result()
                amzn_price, amzn_link, amzn_name = future_amzn.result()
                sd_price, sd_link, sd_name = future_sd.result()
            
            # Compare
            candidates = []
            if ebay_price: candidates.append({"source": "eBay", "price": ebay_price, "link": ebay_link, "name": ebay_name})
            if amzn_price: candidates.append({"source": "Amazon", "price": amzn_price, "link": amzn_link, "name": amzn_name})
            if sd_price: candidates.append({"source": "Slickdeals", "price": sd_price, "link": sd_link, "name": sd_name})
            
            if not candidates:
                 return f"Could not find valid prices for '{product}' on Amazon, eBay, or Slickdeals. (Websites might be blocking the bot)."
            
            # Use Gemini to find the best deal if available
            best_deal = self._analyze_with_gemini(candidates, product)
            
            if best_deal:
                winner = best_deal
                reason = "AI Selected for Best Value"
            else:
                # Fallback to cheapest
                candidates.sort(key=lambda x: x['price'])
                winner = candidates[0]
                reason = "Lowest Price"

            return f"Found best deal on {winner['source']}: ${winner['price']}\nProduct: {winner['name']}\nReason: {reason}\nLink: {winner['link']}"

        finally:
            self.running = False
            pass

    def _analyze_with_gemini(self, candidates, product):
        import os
        import google.generativeai as genai
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return None
            
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            prompt = f"""
            You are a shopping assistant. I am looking for: "{product}".
            Here are the available options found:
            
            {candidates}
            
            Task:
            1. Identify which option is the real product (ignore accessories, cases, or misleading titles if possible).
            2. Comparison: Pick the best value (lowest price for the actual item).
            3. Return the JSON object of the winner EXACTLY as provided in the list.
            4. If all are bad, return the cheapest one.
            
            Output ONLY the JSON of the single best option. No markdown.
            """
            
            response = model.generate_content(prompt)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            
            import json
            try:
                return json.loads(clean_text)
            except:
                return eval(clean_text)
                
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
        # options.add_argument("--headless")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def _parse_price(self, price_str):
        if not price_str: return None
        # Remove $ and ,
        clean = re.sub(r'[^\d.]', '', price_str)
        try:
            return float(clean)
        except:
            return None

    def _scrape_ebay(self, driver, product):
        try:
            url = f"https://www.ebay.com/sch/i.html?_nkw={product.replace(' ', '+')}&_sop=15"
            driver.get(url)
            # Better waiting
            try:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "s-item__info")))
            except:
                pass # Timeout, try parsing anyway
            
            items = driver.find_elements(By.CLASS_NAME, "s-item__info")
            for item in items:
                if "Shop on eBay" in item.text: continue
                try:
                    link_elem = item.find_element(By.CLASS_NAME, "s-item__link")
                    price_elem = item.find_element(By.CLASS_NAME, "s-item__price")
                    title_elem = item.find_element(By.CLASS_NAME, "s-item__title")
                    
                    link = link_elem.get_attribute("href")
                    # Price might be "$20.00 to $30.00", take first
                    price_text = price_elem.text.split(" to ")[0]
                    price = self._parse_price(price_text)
                    name = title_elem.text
                    
                    if price:
                        return price, link, name
                except:
                    continue
            return None, None, None
        except Exception as e:
            print(f"eBay Error: {e}")
            return None, None, None

    def _scrape_amazon(self, driver, product):
        try:
            url = f"https://www.amazon.com/s?k={product.replace(' ', '+')}"
            driver.get(url)
            
            try:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-component-type='s-search-result']")))
            except:
                pass

            # Fallback selectors for items
            selectors = [
                 "div[data-component-type='s-search-result']",
                 ".s-result-item",
                 "div.sg-col-inner"
            ]
            
            items = []
            for sel in selectors:
                items = driver.find_elements(By.CSS_SELECTOR, sel)
                if items: break
            
            for item in items:
                try:
                    # Try Whole + Fraction first
                    try:
                        wh = item.find_element(By.CLASS_NAME, "a-price-whole").text
                        fr = item.find_element(By.CLASS_NAME, "a-price-fraction").text
                        price_text = f"{wh}.{fr}"
                    except:
                        # Fallback to just text search for $
                        txt = item.text
                        match = re.search(r'\$(\d+\.\d{2})', txt)
                        if match:
                            price_text = match.group(1)
                        else:
                            continue

                    price = self._parse_price(price_text)
                    
                    # Link
                    try:
                        link_elem = item.find_element(By.CSS_SELECTOR, "a.a-link-normal.s-no-outline")
                    except:
                         link_elem = item.find_element(By.TAG_NAME, "a")
                         
                    link = link_elem.get_attribute("href")
                    
                    # Name
                    try:
                         name_elem = item.find_element(By.CSS_SELECTOR, "h2 span")
                         name = name_elem.text
                    except:
                         name = "Amazon Product"

                    if price and "http" in link:
                         return price, link, name
                except:
                    continue
            return None, None, None
        except Exception as e:
            print(f"Amazon Error: {e}")
            return None, None, None
            
    def _scrape_slickdeals(self, driver, product):
        try:
            url = f"https://slickdeals.net/newsearch.php?q={product.replace(' ', '+')}&searcharea=deals&searchin=first"
            driver.get(url)
            
            try:
                 WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "resultRow")))
            except:
                 pass
                 
            items = driver.find_elements(By.CLASS_NAME, "resultRow")
            
            for item in items:
                try:
                    link_elem = item.find_element(By.CSS_SELECTOR, "a.dealTitle")
                    link = link_elem.get_attribute("href")
                    name = link_elem.text
                    
                    price_text = ""
                    try:
                        price_elem = item.find_element(By.CLASS_NAME, "price")
                        price_text = price_elem.text
                    except:
                        pass
                        
                    price = self._parse_price(price_text)
                    if not price:
                        match = re.search(r'\$(\d+\.?\d*)', name)
                        if match: price = float(match.group(1))
                            
                    if price:
                        return price, link, name
                except:
                    continue
            return None, None, None
        except Exception as e:
            print(f"Slickdeals Error: {e}")
            return None, None, None
