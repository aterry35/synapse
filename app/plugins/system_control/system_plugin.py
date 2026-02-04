import subprocess
import time
import shlex
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from app.core.plugin_base import PluginBase

class SystemPlugin(PluginBase):
    def on_load(self):
        self.running = False

    def shutdown(self):
        pass

    def is_busy(self) -> bool:
        return self.running

    def heartbeat(self):
        return {"status": "running" if self.running else "idle", "progress": "N/A", "message": "System Ready"}

    def execute(self, command: str, context: dict) -> str:
        self.running = True
        try:
            # /stop is handled by orchestrator usually, but if it falls through:
            if context.get('trigger') == '/stop':
                return "Use the global stop button."
                
            if "download" in command or context.get('trigger') == '/browse':
                if not self.config.get("allow_network", False):
                    raise PermissionError("Network access disabled for System plugin.")
                return f"Simulated download of {command} (Browser automation not installed in this env)"

            if context.get('trigger') in ['/sysctl', '/sys', '/system']:
                cmd_lower = command.lower().strip()
                if cmd_lower.startswith("run ") or cmd_lower.startswith("exec "):
                    if not self.config.get("allow_terminal", False):
                        raise PermissionError("Terminal access disabled for System plugin.")
                    # Strip command prefix
                    cmd_to_run = command.strip()[4:] if cmd_lower.startswith("run ") else command.strip()[5:]
                    cmd_to_run = cmd_to_run.strip()
                    if not cmd_to_run:
                        return "Usage: /sysctl run <cmd>"
                    return self._run_terminal(cmd_to_run)
            
            if context.get('trigger') == '/sysctl':
                cmd_lower = command.lower()
                
                if "find cost of" in cmd_lower:
                    product = cmd_lower.replace("find cost of", "").strip()
                    return self._search_product(product)
                
                if "play" in cmd_lower or "youtube" in cmd_lower:
                    query = cmd_lower.replace("play", "").replace("youtube", "").replace("on", "").strip()
                    return self._play_video(query)
                    
                if "download" in cmd_lower:
                    url = command.replace("download", "").replace("file", "").strip()
                    return self._download_file(url)

                return "Usage: /sysctl [find cost of <item> | play <video> | download <url> | run <cmd>]"
            
            return f"Echo: {command}"
        finally:
            self.running = False

    def _run_terminal(self, cmd):
        # Blocking call
        args = shlex.split(cmd)
        res = subprocess.run(args, capture_output=True, text=True)
        return res.stdout if res.returncode == 0 else f"Error: {res.stderr}"

    def _get_driver(self):
        options = webdriver.ChromeOptions()
        # Add arguments to make it look less like an automated bot
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Additional stealth
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def _search_product(self, product):
        try:
            driver = self._get_driver()
            
            # Try Amazon to avoid direct Google Shopping Captcha if possible, or stick to Google
            # Let's try Google Shopping again but with better headers
            driver.get("https://www.google.com/shopping")
            
            # Find search bar
            try:
                search_box = driver.find_element(By.NAME, "q")
                search_box.send_keys(product)
                search_box.send_keys(Keys.RETURN)
            except:
                return "Failed to find search box. Browser is open for you to check."
            
            # Allow user to solve captcha if it appears. We won't close immediately.
            # We will wait a bit longer to try and scrape, but fail gracefully.
            time.sleep(5) 
            
            # Attempt scrape
            results = driver.find_elements(By.CLASS_NAME, "a8Pemb")
            prices = []
            for r in results[:3]:
                prices.append(r.text)

            if not prices:
                # Keep browser open for user
                return f"Browser opened. I couldn't auto-extract prices (maybe Captcha?), but you can browse the results."
                
            return f"Found prices for {product}: {', '.join(prices)}"
            
        except Exception as e:
            return f"Automation failed: {e}"

    def _play_video(self, query):
        try:
            driver = self._get_driver()
            # If query is a URL, just go there
            if "http" in query:
                driver.get(query)
            else:
                # Search youtube
                driver.get(f"https://www.youtube.com/results?search_query={query}")
                # Optional: Click first video? 
                # Let's just show results to be safe, user said "play" but selecting the right one is hard.
                # But to impress, let's try clicking the first video thumbnail.
                time.sleep(2)
                try:
                    video_title = driver.find_element(By.ID, "video-title")
                    video_title.click()
                except:
                    pass
            
            return f"Playing (or searching for) '{query}' on YouTube."
        except Exception as e:
            return f"Video playback failed: {e}"

    def _download_file(self, url):
        try:
            driver = self._get_driver()
            driver.get(url)
            return f"Browser navigated to {url} for download."
        except Exception as e:
            return f"Download navigation failed: {e}"
