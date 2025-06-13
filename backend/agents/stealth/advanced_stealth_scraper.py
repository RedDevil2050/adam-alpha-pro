"""
Advanced Stealth Capabilities with Quad-Channel Headless Browser Support
========================================================================

This module provides advanced stealth capabilities for financial data scraping:
- Headless Chrome and Firefox browser automation
- Quad-channel data collection with browser diversity
- Advanced anti-detection techniques
- Proxy rotation and IP masking
- Dynamic user agent rotation
- Fingerprint randomization
- Advanced request timing patterns
"""

import asyncio
import random
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium_stealth import stealth
import undetected_chromedriver as uc
import httpx
from fake_useragent import UserAgent
from loguru import logger
import json
import base64
from datetime import datetime, timedelta

@dataclass
class BrowserConfig:
    """Configuration for browser-based scraping"""
    browser_type: str  # 'chrome', 'firefox', 'undetected_chrome'
    headless: bool = True
    stealth_mode: bool = True
    proxy: Optional[str] = None
    user_agent: Optional[str] = None
    viewport_size: tuple = (1920, 1080)
    timeout: int = 30
    page_load_strategy: str = "normal"  # normal, eager, none

@dataclass
class StealthProfile:
    """Stealth profile for anti-detection"""
    user_agent: str
    viewport_size: tuple
    timezone: str
    language: str
    platform: str
    webgl_vendor: str
    webgl_renderer: str
    canvas_fingerprint: str
    audio_fingerprint: str

class AdvancedStealthScraper:
    """Advanced stealth scraper with multiple browser engines"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.active_drivers = {}
        self.proxy_list = []
        self.stealth_profiles = []
        self._initialize_stealth_profiles()
        
    def _initialize_stealth_profiles(self):
        """Initialize various stealth profiles"""
        profiles = [
            {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "viewport_size": (1920, 1080),
                "timezone": "America/New_York",
                "language": "en-US,en;q=0.9",
                "platform": "Win32",
                "webgl_vendor": "Google Inc. (NVIDIA)",
                "webgl_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "canvas_fingerprint": self._generate_canvas_fingerprint(),
                "audio_fingerprint": self._generate_audio_fingerprint()
            },
            {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "viewport_size": (1440, 900),
                "timezone": "America/Los_Angeles",
                "language": "en-US,en;q=0.9",
                "platform": "MacIntel",
                "webgl_vendor": "Apple Inc.",
                "webgl_renderer": "Apple GPU",
                "canvas_fingerprint": self._generate_canvas_fingerprint(),
                "audio_fingerprint": self._generate_audio_fingerprint()
            },
            {
                "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "viewport_size": (1920, 1080),
                "timezone": "America/Chicago",
                "language": "en-US,en;q=0.9",
                "platform": "Linux x86_64",
                "webgl_vendor": "Mesa",
                "webgl_renderer": "Mesa DRI Intel(R) UHD Graphics 620",
                "canvas_fingerprint": self._generate_canvas_fingerprint(),
                "audio_fingerprint": self._generate_audio_fingerprint()
            }
        ]
        
        self.stealth_profiles = [StealthProfile(**profile) for profile in profiles]
        
    def _generate_canvas_fingerprint(self) -> str:
        """Generate random canvas fingerprint"""
        return base64.b64encode(f"canvas_{random.randint(1000000, 9999999)}".encode()).decode()
        
    def _generate_audio_fingerprint(self) -> str:
        """Generate random audio fingerprint"""
        return base64.b64encode(f"audio_{random.randint(1000000, 9999999)}".encode()).decode()

    async def create_stealth_driver(self, config: BrowserConfig) -> webdriver.Remote:
        """Create a stealth-enabled browser driver"""
        
        profile = random.choice(self.stealth_profiles)
        
        if config.browser_type == "chrome":
            return await self._create_chrome_driver(config, profile)
        elif config.browser_type == "firefox":
            return await self._create_firefox_driver(config, profile)
        elif config.browser_type == "undetected_chrome":
            return await self._create_undetected_chrome_driver(config, profile)
        else:
            raise ValueError(f"Unsupported browser type: {config.browser_type}")

    async def _create_chrome_driver(self, config: BrowserConfig, profile: StealthProfile) -> webdriver.Chrome:
        """Create Chrome driver with stealth configuration"""
        
        options = ChromeOptions()
        
        # Basic stealth options
        if config.headless:
            options.add_argument("--headless=new")
        
        # Anti-detection arguments
        options.add_argument(f"--user-agent={profile.user_agent}")
        options.add_argument(f"--window-size={profile.viewport_size[0]},{profile.viewport_size[1]}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-javascript")  # Can be enabled selectively
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-ipc-flooding-protection")
        
        # Memory and performance optimizations
        options.add_argument("--memory-pressure-off")
        options.add_argument("--max_old_space_size=4096")
        options.add_argument("--no-zygote")
        options.add_argument("--single-process")
        
        # Proxy configuration
        if config.proxy:
            options.add_argument(f"--proxy-server={config.proxy}")
            
        # Page load strategy
        options.page_load_strategy = config.page_load_strategy
        
        # Additional stealth preferences
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "media_stream": 2,
            },
            "profile.managed_default_content_settings": {
                "images": 2
            }
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            driver = webdriver.Chrome(options=options)
            
            # Apply stealth techniques
            if config.stealth_mode:
                stealth(driver,
                    languages=[profile.language],
                    vendor="Google Inc.",
                    platform=profile.platform,
                    webgl_vendor=profile.webgl_vendor,
                    renderer=profile.webgl_renderer,
                    fix_hairline=True,
                )
                
                # Execute additional stealth scripts
                await self._apply_advanced_stealth(driver, profile)
            
            driver_id = f"chrome_{int(time.time())}_{random.randint(1000, 9999)}"
            self.active_drivers[driver_id] = driver
            
            logger.success(f"✅ Created stealth Chrome driver: {driver_id}")
            return driver
            
        except Exception as e:
            logger.error(f"❌ Failed to create Chrome driver: {e}")
            raise

    async def _create_firefox_driver(self, config: BrowserConfig, profile: StealthProfile) -> webdriver.Firefox:
        """Create Firefox driver with stealth configuration"""
        
        options = FirefoxOptions()
        
        if config.headless:
            options.add_argument("--headless")
            
        # Firefox-specific stealth settings
        options.set_preference("general.useragent.override", profile.user_agent)
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("dom.webnotifications.enabled", False)
        options.set_preference("media.navigator.enabled", False)
        options.set_preference("network.http.connection-timeout", config.timeout)
        
        # Privacy and security settings
        options.set_preference("privacy.trackingprotection.enabled", True)
        options.set_preference("privacy.donottrackheader.enabled", True)
        options.set_preference("datareporting.healthreport.uploadEnabled", False)
        options.set_preference("datareporting.policy.dataSubmissionEnabled", False)
        
        # Performance optimizations
        options.set_preference("browser.cache.disk.enable", False)
        options.set_preference("browser.cache.memory.enable", False)
        options.set_preference("browser.cache.offline.enable", False)
        options.set_preference("network.http.use-cache", False)
        
        # Proxy configuration
        if config.proxy:
            proxy_parts = config.proxy.split(":")
            if len(proxy_parts) == 2:
                options.set_preference("network.proxy.type", 1)
                options.set_preference("network.proxy.http", proxy_parts[0])
                options.set_preference("network.proxy.http_port", int(proxy_parts[1]))
                options.set_preference("network.proxy.ssl", proxy_parts[0])
                options.set_preference("network.proxy.ssl_port", int(proxy_parts[1]))
        
        try:
            driver = webdriver.Firefox(options=options)
            
            # Set viewport size
            driver.set_window_size(profile.viewport_size[0], profile.viewport_size[1])
            
            # Apply additional stealth techniques
            if config.stealth_mode:
                await self._apply_firefox_stealth(driver, profile)
            
            driver_id = f"firefox_{int(time.time())}_{random.randint(1000, 9999)}"
            self.active_drivers[driver_id] = driver
            
            logger.success(f"✅ Created stealth Firefox driver: {driver_id}")
            return driver
            
        except Exception as e:
            logger.error(f"❌ Failed to create Firefox driver: {e}")
            raise

    async def _create_undetected_chrome_driver(self, config: BrowserConfig, profile: StealthProfile) -> uc.Chrome:
        """Create undetected Chrome driver"""
        
        options = uc.ChromeOptions()
        
        if config.headless:
            options.add_argument("--headless=new")
            
        # Undetected Chrome specific options
        options.add_argument(f"--user-agent={profile.user_agent}")
        options.add_argument(f"--window-size={profile.viewport_size[0]},{profile.viewport_size[1]}")
        options.add_argument("--no-first-run")
        options.add_argument("--no-service-autorun")
        options.add_argument("--password-store=basic")
        
        if config.proxy:
            options.add_argument(f"--proxy-server={config.proxy}")
        
        try:
            driver = uc.Chrome(options=options, version_main=120)
            
            # Additional stealth setup
            if config.stealth_mode:
                await self._apply_undetected_stealth(driver, profile)
            
            driver_id = f"undetected_{int(time.time())}_{random.randint(1000, 9999)}"
            self.active_drivers[driver_id] = driver
            
            logger.success(f"✅ Created undetected Chrome driver: {driver_id}")
            return driver
            
        except Exception as e:
            logger.error(f"❌ Failed to create undetected Chrome driver: {e}")
            raise

    async def _apply_advanced_stealth(self, driver: webdriver.Remote, profile: StealthProfile):
        """Apply advanced stealth techniques to Chrome driver"""
        
        # Remove webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Randomize navigator properties
        stealth_script = f"""
        Object.defineProperty(navigator, 'languages', {{
            get: () => ['{profile.language.split(',')[0]}']
        }});
        
        Object.defineProperty(navigator, 'platform', {{
            get: () => '{profile.platform}'
        }});
        
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {random.randint(2, 16)}
        }});
        
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {random.choice([2, 4, 8, 16])}
        }});
        
        // Override canvas fingerprinting
        const getContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(contextType) {{
            if (contextType === '2d') {{
                const context = getContext.apply(this, arguments);
                const getImageData = context.getImageData;
                context.getImageData = function() {{
                    const imageData = getImageData.apply(this, arguments);
                    // Add noise to canvas data
                    for (let i = 0; i < imageData.data.length; i += 4) {{
                        imageData.data[i] += Math.floor(Math.random() * 3) - 1;
                        imageData.data[i + 1] += Math.floor(Math.random() * 3) - 1;
                        imageData.data[i + 2] += Math.floor(Math.random() * 3) - 1;
                    }}
                    return imageData;
                }};
                return context;
            }}
            return getContext.apply(this, arguments);
        }};
        
        // Override WebGL fingerprinting
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) return '{profile.webgl_vendor}';
            if (parameter === 37446) return '{profile.webgl_renderer}';
            return getParameter.apply(this, arguments);
        }};
        """
        
        driver.execute_script(stealth_script)
        
        # Add random mouse movements
        await self._simulate_human_behavior(driver)

    async def _apply_firefox_stealth(self, driver: webdriver.Firefox, profile: StealthProfile):
        """Apply stealth techniques to Firefox driver"""
        
        stealth_script = f"""
        // Override navigator properties
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined
        }});
        
        Object.defineProperty(navigator, 'languages', {{
            get: () => ['{profile.language.split(',')[0]}']
        }});
        
        // Add canvas noise
        const getContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(contextType) {{
            const context = getContext.apply(this, arguments);
            if (contextType === '2d') {{
                const getImageData = context.getImageData;
                context.getImageData = function() {{
                    const imageData = getImageData.apply(this, arguments);
                    // Add subtle noise
                    for (let i = 0; i < imageData.data.length; i += 10) {{
                        imageData.data[i] += Math.floor(Math.random() * 2);
                    }}
                    return imageData;
                }};
            }}
            return context;
        }};
        """
        
        driver.execute_script(stealth_script)
        await self._simulate_human_behavior(driver)

    async def _apply_undetected_stealth(self, driver: uc.Chrome, profile: StealthProfile):
        """Apply additional stealth to undetected Chrome"""
        
        # Undetected Chrome handles most detection automatically
        # Add minimal additional stealth
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        await self._simulate_human_behavior(driver)

    async def _simulate_human_behavior(self, driver: webdriver.Remote):
        """Simulate human-like behavior patterns"""
        
        try:
            # Random scroll
            scroll_height = random.randint(100, 500)
            driver.execute_script(f"window.scrollBy(0, {scroll_height});")
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Random mouse movement (if elements are available)
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                ActionChains(driver).move_to_element_with_offset(
                    body, 
                    random.randint(0, 100), 
                    random.randint(0, 100)
                ).perform()
            except:
                pass
                
            await asyncio.sleep(random.uniform(0.2, 0.8))
            
        except Exception as e:
            logger.debug(f"Human behavior simulation skipped: {e}")

    async def quad_channel_scrape(self, urls: List[str], selectors: Dict[str, str]) -> Dict[str, Any]:
        """Perform quad-channel scraping with different browsers"""
        
        configs = [
            BrowserConfig("chrome", headless=True, stealth_mode=True),
            BrowserConfig("firefox", headless=True, stealth_mode=True),
            BrowserConfig("undetected_chrome", headless=True, stealth_mode=True),
            BrowserConfig("chrome", headless=True, stealth_mode=True, proxy=None)  # Backup Chrome
        ]
        
        results = {}
        tasks = []
        
        for i, (url, config) in enumerate(zip(urls[:4], configs)):
            task = asyncio.create_task(
                self._single_channel_scrape(f"channel_{i+1}", url, selectors, config)
            )
            tasks.append(task)
        
        # Execute all channels concurrently
        channel_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(channel_results):
            channel_name = f"channel_{i+1}"
            if isinstance(result, Exception):
                logger.error(f"❌ {channel_name} failed: {result}")
                results[channel_name] = {"error": str(result), "data": None}
            else:
                results[channel_name] = result
                logger.success(f"✅ {channel_name} completed successfully")
        
        return results

    async def _single_channel_scrape(self, channel_name: str, url: str, selectors: Dict[str, str], config: BrowserConfig) -> Dict[str, Any]:
        """Perform single channel scraping"""
        
        driver = None
        try:
            logger.info(f"🌐 {channel_name} starting scrape: {url}")
            
            # Create stealth driver
            driver = await self.create_stealth_driver(config)
            
            # Navigate to URL with random delay
            await asyncio.sleep(random.uniform(0.5, 2.0))
            driver.get(url)
            
            # Wait for page load
            WebDriverWait(driver, config.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional human-like delay
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            # Extract data using selectors
            extracted_data = {}
            for field, selector in selectors.items():
                try:
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    extracted_data[field] = element.text.strip()
                except TimeoutException:
                    logger.warning(f"⚠️ {channel_name}: Selector '{selector}' not found for field '{field}'")
                    extracted_data[field] = None
                except Exception as e:
                    logger.warning(f"⚠️ {channel_name}: Error extracting '{field}': {e}")
                    extracted_data[field] = None
            
            # Simulate additional human behavior
            await self._simulate_human_behavior(driver)
            
            return {
                "channel": channel_name,
                "url": url,
                "browser": config.browser_type,
                "data": extracted_data,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"❌ {channel_name} scraping failed: {e}")
            return {
                "channel": channel_name,
                "url": url,
                "browser": config.browser_type if config else "unknown",
                "data": {},
                "error": str(e),
                "success": False
            }
        finally:
            if driver:
                try:
                    driver.quit()
                    # Remove from active drivers
                    driver_ids_to_remove = [k for k, v in self.active_drivers.items() if v == driver]
                    for driver_id in driver_ids_to_remove:
                        del self.active_drivers[driver_id]
                except Exception as e:
                    logger.warning(f"⚠️ Error closing {channel_name} driver: {e}")

    async def cleanup_drivers(self):
        """Cleanup all active drivers"""
        for driver_id, driver in self.active_drivers.items():
            try:
                driver.quit()
                logger.info(f"🧹 Cleaned up driver: {driver_id}")
            except Exception as e:
                logger.warning(f"⚠️ Error cleaning up driver {driver_id}: {e}")
        
        self.active_drivers.clear()

    def add_proxy(self, proxy: str):
        """Add proxy to rotation list"""
        self.proxy_list.append(proxy)
        logger.info(f"➕ Added proxy: {proxy}")

    def get_random_proxy(self) -> Optional[str]:
        """Get random proxy from list"""
        if self.proxy_list:
            return random.choice(self.proxy_list)
        return None
