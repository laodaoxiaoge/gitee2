import time
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import requests
import re
import os
import threading
from queue import Queue
import eventlet
import base64
import random
from fake_useragent import UserAgent
import json
from datetime import datetime

eventlet.monkey_patch()

# 配置区域 - 请根据实际情况修改
CONFIG = {
    # FOFA API配置（推荐使用）
    "fofa_email": "your_email@example.com",  # 替换为您的FOFA邮箱
    "fofa_key": "your_api_key_here",         # 替换为您的FOFA API密钥
    
    # 地区搜索词（可以根据需要调整）
    "regions": {
        "hebei": '"iptv/live/zh_cn.js" && country="CN" && region="河北"',
        "beijing": '"iptv/live/zh_cn.js" && country="CN" && region="北京"',
        "guangdong": '"iptv/live/zh_cn.js" && country="CN" && region="广东"',
        "shanghai": '"iptv/live/zh_cn.js" && country="CN" && region="上海"',
        "tianjin": '"iptv/live/zh_cn.js" && country="CN" && region="天津"',
        "chongqing": '"iptv/live/zh_cn.js" && country="CN" && region="重庆"',
        "shanxi": '"iptv/live/zh_cn.js" && country="CN" && region="山西"',
        "shaanxi": '"iptv/live/zh_cn.js" && country="CN" && region="陕西"',
        "liaoning": '"iptv/live/zh_cn.js" && country="CN" && region="辽宁"',
        "jiangsu": '"iptv/live/zh_cn.js" && country="CN" && region="江苏"',
        "zhejiang": '"iptv/live/zh_cn.js" && country="CN" && region="浙江"',
        "anhui": '"iptv/live/zh_cn.js" && country="CN" && region="安徽"',
        "fujian": '"iptv/live/zh_cn.js" && country="CN" && region="福建"',
        "jiangxi": '"iptv/live/zh_cn.js" && country="CN" && region="江西"',
        "shandong": '"iptv/live/zh_cn.js" && country="CN" && region="山东"',
        "henan": '"iptv/live/zh_cn.js" && country="CN" && region="河南"',
        "hubei": '"iptv/live/zh_cn.js" && country="CN" && region="湖北"',
        "hunan": '"iptv/live/zh_cn.js" && country="CN" && region="湖南"'
    },
    
    # 请求设置
    "timeout": 3,           # 请求超时时间（秒）
    "max_workers": 50,      # 最大线程数
    "max_retries": 3,       # 最大重试次数
    
    # 频道设置
    "result_counter": 8,    # 每个频道保留的最大数量
    "min_speed": 0.1,       # 最低速度要求（MB/s）
}

class SecureFOFACrawler:
    def __init__(self):
        self.ua = UserAgent()
        self.results = []
        self.channels = []
        self.error_channels = []
        
    def search_fofa_api(self, query, page=1, size=100):
        """使用FOFA官方API搜索"""
        if not CONFIG["fofa_email"] or not CONFIG["fofa_key"]:
            print("⚠️ 警告: 未配置FOFA API密钥，将尝试使用爬取方式")
            return []
            
        try:
            query_base64 = base64.b64encode(query.encode()).decode()
            api_url = "https://fofa.info/api/v1/search/all"
            params = {
                'email': CONFIG["fofa_email"],
                'key': CONFIG["fofa_key"],
                'qbase64': query_base64,
                'page': page,
                'size': size,
                'fields': 'ip,port,protocol,host'
            }
            
            response = requests.get(api_url, params=params, timeout=CONFIG["timeout"])
            if response.status_code == 200:
                data = response.json()
                if data.get('error'):
                    print(f"❌ API错误: {data.get('errmsg', '未知错误')}")
                    return []
                return data.get('results', [])
        except Exception as e:
            print(f"❌ API请求失败: {e}")
            
        return []
    
    def create_stealth_driver(self):
        """创建隐形的浏览器实例"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument(f'--user-agent={self.ua.random}')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_exmental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    
    def crawl_fofa(self, url, max_retries=3):
        """爬取FOFA搜索结果"""
        for attempt in range(max_retries):
            try:
                driver = self.create_stealth_driver()
                
                # 随机延迟
                time.sleep(random.uniform(5, 15))
                
                driver.get(url)
                
                # 模拟人类行为
                self.simulate_human_behavior(driver)
                
                # 等待页面加载
                time.sleep(random.uniform(8, 15))
                
                page_content = driver.page_source
                driver.quit()
                
                # 检查是否被封禁
                if "IP访问异常" in page_content or "爬虫" in page_content:
                    print(f"❌ 第{attempt+1}次尝试被检测为爬虫")
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 60
                        print(f"⏳ 等待{wait_time}秒后重试...")
                        time.sleep(wait_time)
                    continue
                    
                return page_content
                
            except Exception as e:
                print(f"❌ 第{attempt+1}次爬取失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(30)
                    
        return None
    
    def simulate_human_behavior(self, driver):
        """模拟人类浏览行为"""
        # 随机滚动页面
        scroll_actions = [
            "window.scrollTo(0, document.body.scrollHeight * 0.3);",
            "window.scrollTo(0, document.body.scrollHeight * 0.7);", 
            "window.scrollTo(0, document.body.scrollHeight);"
        ]
        
        for action in scroll_actions:
            driver.execute_script(action)
            time.sleep(random.uniform(1, 3))
    
    def extract_ips_from_page(self, page_content):
        """从页面内容提取IP地址"""
        pattern = r"http://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+"
        urls_all = re.findall(pattern, page_content)
        urls = set(urls_all)
        
        # 处理IP，将第四位改为1
        processed_urls = []
        for url in urls:
            url = url.strip()
            ip_start_index = url.find("//") + 2
            ip_end_index = url.find(":", ip_start_index)
            ip_dot_start = url.find(".") + 1
            ip_dot_second = url.find(".", ip_dot_start) + 1
            ip_dot_three = url.find(".", ip_dot_second) + 1
            base_url = url[:ip_start_index]
            ip_address = url[ip_start_index:ip_dot_three]
            port = url[ip_end_index:]
            modified_ip = f"{ip_address}1"
            processed_url = f"{base_url}{modified_ip}{port}"
            processed_urls.append(processed_url)
            
        return set(processed_urls)
    
    def extract_ips_from_api(self, api_results):
        """从API结果提取IP地址"""
        processed_urls = []
        for result in api_results:
            ip = result[0]
            port = result[1]
            protocol = result[2].lower() if len(result) > 2 else "http"
            processed_url = f"{protocol}://{ip[:-1]}1:{port}"
            processed_urls.append(processed_url)
            
        return set(processed_urls)
    
    def modify_urls(self, url):
        """生成测试URL"""
        modified_urls = []
        ip_start_index = url.find("//") + 2
        ip_end_index = url.find(":", ip_start_index)
        base_url = url[:ip_start_index]
        ip_address = url[ip_start_index:ip_end_index]
        port = url[ip_end_index:]
        ip_end = "/iptv/live/1000.json?key=txiptv"
        
        for i in range(1, 256):
            modified_ip = f"{ip_address[:-1]}{i}"
            modified_url = f"{base_url}{modified_ip}{port}{ip_end}"
            modified_urls.append(modified_url)
            
        return modified_urls
    
    def is_url_accessible(self, url):
        """检查URL是否可访问"""
        for attempt in range(CONFIG["max_retries"]):
            try:
                response = requests.get(url, timeout=CONFIG["timeout"])
                if response.status_code == 200:
                    return url
            except:
                if attempt < CONFIG["max_retries"] - 1:
                    time.sleep(1)
        return None
    
    def fetch_all_ips(self):
        """获取所有IP地址"""
        all_ips = set()
        
        for region, query in CONFIG["regions"].items():
            print(f"🔍 搜索地区: {region}")
            
            # 优先使用API
            api_results = self.search_fofa_api(query)
            if api_results:
                ips = self.extract_ips_from_api(api_results)
                all_ips.update(ips)
                print(f"✅ 通过API找到 {len(ips)} 个IP")
                continue
                
            # API失败时使用爬取
            query_base64 = base64.b64encode(query.encode()).decode()
            fofa_url = f"https://fofa.info/result?qbase64={query_base64}"
            
            page_content = self.crawl_fofa(fofa_url)
            if page_content:
                ips = self.extract_ips_from_page(page_content)
                all_ips.update(ips)
                print(f"✅ 通过爬取找到 {len(ips)} 个IP")
            else:
                print(f"❌ 无法获取 {region} 的IP")
                
        return all_ips
    
    def test_urls(self, urls):
        """测试URL可用性"""
        valid_urls = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONFIG["max_workers"]) as executor:
            futures = []
            for url in urls:
                modified_urls = self.modify_urls(url)
                for modified_url in modified_urls:
                    futures.append(executor.submit(self.is_url_accessible, modified_url))
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    valid_urls.append(result)
                    print(f"✅ 可用URL: {result}")
        
        return valid_urls
    
    def parse_json_data(self, url):
        """解析JSON数据获取频道信息"""
        try:
            ip_start_index = url.find("//") + 2
            ip_dot_start = url.find(".") + 1
            ip_index_second = url.find("/", ip_dot_start)
            base_url = url[:ip_start_index]
            ip_address = url[ip_start_index:ip_index_second]
            url_x = f"{base_url}{ip_address}"
            
            response = requests.get(url, timeout=CONFIG["timeout"])
            json_data = response.json()
            
            channels = []
            for item in json_data['data']:
                if isinstance(item, dict):
                    name = item.get('name')
                    urlx = item.get('url')
                    
                    if not name or not urlx:
                        continue
                    
                    if ',' in urlx:
                        continue
                        
                    if 'http' in urlx:
                        urld = f"{urlx}"
                    else:
                        urld = f"{url_x}{urlx}"
                    
                    # 清理频道名称
                    name = self.clean_channel_name(name)
                    channels.append((name, urld))
            
            return channels
            
        except Exception as e:
            print(f"❌ 解析JSON失败: {e}")
            return []
    
    def clean_channel_name(self, name):
        """清理频道名称"""
        replacements = {
            "cctv": "CCTV",
            "中央": "CCTV",
            "央视": "CCTV",
            "高清": "",
            "超高": "",
            "HD": "",
            "标清": "",
            "频道": "",
            "-": "",
            " ": "",
            "PLUS": "+",
            "＋": "+",
            "(": "",
            ")": "",
            "CCTV1综合": "CCTV1",
            "CCTV2财经": "CCTV2",
            "CCTV3综艺": "CCTV3",
            "CCTV4国际": "CCTV4",
            "CCTV4中文国际": "CCTV4",
            "CCTV4欧洲": "CCTV4",
            "CCTV5体育": "CCTV5",
            "CCTV6电影": "CCTV6",
            "CCTV7军事": "CCTV7",
            "CCTV7军农": "CCTV7",
            "CCTV7农业": "CCTV7",
            "CCTV7国防军事": "CCTV7",
            "CCTV8电视剧": "CCTV8",
            "CCTV9记录": "CCTV9",
            "CCTV9纪录": "CCTV9",
            "CCTV10科教": "CCTV10",
            "CCTV11戏曲": "CCTV11",
            "CCTV12社会与法": "CCTV12",
            "CCTV13新闻": "CCTV13",
            "CCTV新闻": "CCTV13",
            "CCTV14少儿": "CCTV14",
            "CCTV15音乐": "CCTV15",
            "CCTV16奥林匹克": "CCTV16",
            "CCTV17农业农村": "CCTV17",
            "CCTV17农业": "CCTV17",
            "CCTV5+体育赛视": "CCTV5+",
            "CCTV5+体育赛事": "CCTV5+",
            "CCTV5+体育": "CCTV5+"
        }
        
        for old, new in replacements.items():
            name = name.replace(old, new)
        
        # 使用正则表达式处理模式匹配
        name = re.sub(r"CCTV(\d+)台", r"CCTV\1", name)
        
        return name
    
    def test_channel_speed(self, channel_name, channel_url):
        """测试频道速度"""
        try:
            channel_url_t = channel_url.rstrip(channel_url.split('/')[-1])
            response = requests.get(channel_url, timeout=CONFIG["timeout"])
            lines = response.text.strip().split('\n')
            ts_lists = [line.split('/')[-1] for line in lines if not line.startswith('#')]
            
            if not ts_lists:
                return None
                
            ts_lists_0 = ts_lists[0].rstrip(ts_lists[0].split('.ts')[-1])
            ts_url = channel_url_t + ts_lists[0]
            
            # 使用eventlet设置超时
            with eventlet.Timeout(5, False):
                start_time = time.time()
                content = requests.get(ts_url, timeout=CONFIG["timeout"]).content
                end_time = time.time()
                
                if content:
                    file_size = len(content)
                    download_speed = file_size / (end_time - start_time) / 1024 / 1024  # MB/s
                    
                    if download_speed >= CONFIG["min_speed"]:
                        return channel_name, channel_url, f"{download_speed:.3f} MB/s"
        
        except:
            pass
            
        return None
    
    def worker(self):
        """工作线程函数"""
        while True:
            channel_name, channel_url = self.task_queue.get()
            if channel_name is None:  # 终止信号
                break
                
            try:
                result = self.test_channel_speed(channel_name, channel_url)
                if result:
                    self.results.append(result)
                else:
                    self.error_channels.append((channel_name, channel_url))
            except Exception as e:
                self.error_channels.append((channel_name, channel_url))
                
            # 更新进度
            processed = len(self.results) + len(self.error_channels)
            total = len(self.channels)
            percentage = (processed / total) * 100 if total > 0 else 0
            print(f"📊 进度: {processed}/{total} ({percentage:.1f}%)")
            
            self.task_queue.task_done()
    
    def test_all_channels(self):
        """测试所有频道速度"""
        print("🚀 开始测试频道速度...")
        
        # 创建任务队列
        self.task_queue = Queue()
        for channel in self.channels:
            self.task_queue.put(channel)
        
        # 创建工作线程
        threads = []
        for _ in range(CONFIG["max_workers"]):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()
            threads.append(t)
        
        # 等待所有任务完成
        self.task_queue.join()
        
        # 发送终止信号
        for _ in range(CONFIG["max_workers"]):
            self.task_queue.put((None, None))
        
        for t in threads:
            t.join()
    
    def generate_playlist(self):
        """生成播放列表"""
        print("📝 生成播放列表...")
        
        # 对频道进行排序
        def channel_key(channel_name):
            match = re.search(r'\d+', channel_name)
            if match:
                return int(match.group())
            else:
                return float('inf')
        
        self.results.sort(key=lambda x: (x[0], -float(x[2].split()[0])))
        self.results.sort(key=lambda x: channel_key(x[0]))
        
        # 生成itvlist.txt
        with open("itvlist.txt", 'w', encoding='utf-8') as file:
            file.write('央视频道,#genre#\n')
            channel_counters = {}
            for result in self.results:
                channel_name, channel_url, speed = result
                if 'CCTV' in channel_name:
                    if channel_name not in channel_counters:
                        channel_counters[channel_name] = 0
                    if channel_counters[channel_name] < CONFIG["result_counter"]:
                        file.write(f"{channel_name},{channel_url}\n")
                        channel_counters[channel_name] +=
