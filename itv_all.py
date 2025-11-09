import eventlet
eventlet.monkey_patch()  # 必须在所有导入之前调用

import time
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import requests
import re
import os
import threading
from queue import Queue
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FOFA搜索URL（与您原有代码相同）
urls = [
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iSGViZWki",  # Hebei (河北)
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iYmVpamluZyI%3D",  # Beijing (北京)
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iZ3Vhbmdkb25nIg%3D%3D",  # Guangdong (广东)
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0ic2hhbmdoYWki",  # Shanghai (上海)
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0idGlhbmppbiI%3D",  # Tianjin (天津)
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iY2hvbmdxaW5nIg%3D%3D",  # Chongqing (重庆)
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0ic2hhbnhpIg%3D%3D",  # Shanxi (山西)
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iU2hhYW54aSI%3D",  # Shaanxi (陕西)
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0ibGlhb25pbmci",  # Liaoning (辽宁)
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iamlhbmdzdSI%3D",  # Jiangsu (江苏)
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iemhlamlhbmci",  # Zhejiang (浙江)
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0i5a6J5b69Ig%3D%3D",  # Anhui (安徽)
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iRnVqaWFuIg%3D%3D",  # 福建
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0i5rGf6KW%2FIg%3D%3D",  # 江西
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0i5bGx5LicIg%3D%3D",  # 山东
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0i5rKz5Y2XIg%3D%3D",  # 河南
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0i5rmW5YyXIg%3D%3D",  # 湖北
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0i5rmW5Y2XIg%3D%3D"  # 湖南
]

def setup_chrome_driver():
    """设置Chrome浏览器驱动，适配GitHub Actions环境"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    # GitHub Actions中正确的Chrome路径
    chrome_options.binary_location = '/usr/bin/chromium-browser'
    
    try:
        # 尝试使用系统ChromeDriver
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("Chrome驱动初始化成功")
        return driver
    except Exception as e:
        logger.error(f"Chrome驱动初始化失败: {e}")
        return None

def modify_urls(url):
    """修改URL生成测试地址（与您原有代码相同）"""
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

def is_url_accessible(url):
    """检查URL是否可访问（增加超时时间）"""
    try:
        response = requests.get(url, timeout=3.0)  # 增加超时时间
        if response.status_code == 200:
            return url
    except requests.exceptions.RequestException:
        pass
    return None

def clean_channel_name(name):
    """清理频道名称（与您原有代码相同）"""
    if not name:
        return ""
    
    # 替换规则
    replacements = {
        "cctv": "CCTV", "中央": "CCTV", "央视": "CCTV",
        "高清": "", "超高": "", "HD": "", "标清": "", 
        "频道": "", "-": "", " ": "", "PLUS": "+", "＋": "+",
        "(": "", ")": "",
        "CCTV1综合": "CCTV1", "CCTV2财经": "CCTV2", "CCTV3综艺": "CCTV3",
        "CCTV4国际": "CCTV4", "CCTV4中文国际": "CCTV4", "CCTV4欧洲": "CCTV4",
        "CCTV5体育": "CCTV5", "CCTV6电影": "CCTV6", "CCTV7军事": "CCTV7",
        "CCTV7军农": "CCTV7", "CCTV7农业": "CCTV7", "CCTV7国防军事": "CCTV7",
        "CCTV8电视剧": "CCTV8", "CCTV9记录": "CCTV9", "CCTV9纪录": "CCTV9",
        "CCTV10科教": "CCTV10", "CCTV11戏曲": "CCTV11", "CCTV12社会与法": "CCTV12",
        "CCTV13新闻": "CCTV13", "CCTV新闻": "CCTV13", "CCTV14少儿": "CCTV14",
        "CCTV15音乐": "CCTV15", "CCTV16奥林匹克": "CCTV16", "CCTV17农业农村": "CCTV17",
        "CCTV17农业": "CCTV17", "CCTV5+体育赛视": "CCTV5+", "CCTV5+体育赛事": "CCTV5+",
        "CCTV5+体育": "CCTV5+"
    }
    
    for old, new in replacements.items():
        name = name.replace(old, new)
    
    # 正则替换
    name = re.sub(r"CCTV(\d+)台", r"CCTV\1", name)
    
    return name

def test_channel_speed(channel_name, channel_url):
    """测试频道速度（修复eventlet使用）"""
    try:
        # 获取M3U8文件内容
        response = requests.get(channel_url, timeout=3)
        lines = response.text.strip().split('\n')
        
        # 提取TS文件列表
        ts_lists = [line.split('/')[-1] for line in lines if not line.startswith('#')]
        
        if not ts_lists:
            return None
            
        # 获取第一个TS文件的URL
        channel_url_t = channel_url.rstrip(channel_url.split('/')[-1])
        ts_url = channel_url_t + ts_lists[0]
        
        # 使用eventlet设置超时
        with eventlet.Timeout(5, False):
            start_time = time.time()
            content = requests.get(ts_url, timeout=3).content
            end_time = time.time()
            
            if content:
                file_size = len(content)
                download_time = end_time - start_time
                download_speed = file_size / download_time / 1024 / 1024  # MB/s
                
                if download_speed >= 0.1:  # 最低速度要求
                    return channel_name, channel_url, f"{download_speed:.3f} MB/s"
    
    except Exception as e:
        logger.debug(f"测试频道 {channel_name} 速度失败: {e}")
    
    return None

def main():
    """主函数"""
    logger.info("开始从FOFA提取视频流")
    all_results = []
    
    for i, url in enumerate(urls):
        logger.info(f"处理URL {i+1}/{len(urls)}: {url}")
        
        try:
            # 设置Chrome驱动
            driver = setup_chrome_driver()
            if not driver:
                logger.error("无法创建Chrome驱动，跳过此URL")
                continue
                
            # 访问网页
            driver.get(url)
            time.sleep(10)  # 等待页面加载
            
            # 获取页面内容
            page_content = driver.page_source
            driver.quit()
            
            # 查找IP地址
            pattern = r"http://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+"
            urls_all = re.findall(pattern, page_content)
            urls_set = set(urls_all)
            
            if not urls_set:
                logger.warning("未找到IP地址，跳过此URL")
                continue
                
            logger.info(f"找到 {len(urls_set)} 个IP地址")
            
            # 处理IP地址（将第四位改为1）
            processed_urls = []
            for url_item in urls_set:
                url_item = url_item.strip()
                ip_start_index = url_item.find("//") + 2
                ip_end_index = url_item.find(":", ip_start_index)
                ip_dot_start = url_item.find(".") + 1
                ip_dot_second = url_item.find(".", ip_dot_start) + 1
                ip_dot_three = url_item.find(".", ip_dot_second) + 1
                base_url = url_item[:ip_start_index]
                ip_address = url_item[ip_start_index:ip_dot_three]
                port = url_item[ip_end_index:]
                modified_ip = f"{ip_address}1"
                processed_url = f"{base_url}{modified_ip}{port}"
                processed_urls.append(processed_url)
                
            unique_urls = set(processed_urls)
            logger.info(f"处理后有 {len(unique_urls)} 个唯一URL")
            
            # 测试URL可用性
            valid_urls = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                futures = []
                for url_item in unique_urls:
                    modified_urls_list = modify_urls(url_item)
                    for modified_url in modified_urls_list:
                        futures.append(executor.submit(is_url_accessible, modified_url))
                
                for j, future in enumerate(concurrent.futures.as_completed(futures)):
                    result = future.result()
                    if result:
                        valid_urls.append(result)
                    if j % 50 == 0:  # 每50个打印一次进度
                        logger.info(f"URL测试进度: {j+1}/{len(futures)}")
            
            logger.info(f"找到 {len(valid_urls)} 个可用URL")
            
            # 处理可用URL获取频道信息
            for j, url_item in enumerate(valid_urls):
                try:
                    # 构建基础URL
                    ip_start_index = url_item.find("//") + 2
                    ip_dot_start = url_item.find(".") + 1
                    ip_index_second = url_item.find("/", ip_dot_start)
                    base_url = url_item[:ip_start_index]
                    ip_address = url_item[ip_start_index:ip_index_second]
                    url_x = f"{base_url}{ip_address}"
                    
                    # 获取JSON数据
                    response = requests.get(url_item, timeout=3)
                    json_data = response.json()
                    
                    if 'data' not in json_data:
                        continue
                    
                    # 解析频道信息
                    for item in json_data['data']:
                        if isinstance(item, dict):
                            name = item.get('name')
                            urlx = item.get('url')
                            
                            if not name or not urlx:
                                continue
                                
                            if ',' in urlx:
                                continue
                                
                            # 构建完整URL
                            if 'http' in urlx:
                                urld = f"{urlx}"
                            else:
                                urld = f"{url_x}{urlx}"
                            
                            # 清理频道名称
                            name = clean_channel_name(name)
                            all_results.append(f"{name},{urld}")
                            logger.info(f"添加频道: {name}")
                
                except Exception as e:
                    logger.debug(f"处理URL {url_item} 时出错: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"处理主URL {url} 时出错: {e}")
            continue
    
    # 去重结果
    unique_results = list(set(all_results))
    logger.info(f"总共找到 {len(unique_results)} 个唯一频道")
    
    if not unique_results:
        logger.warning("未找到任何频道，程序结束")
        return
    
    # 准备测试频道速度
    channels = []
    for result in unique_results:
        if ',' in result:
            channel_name, channel_url = result.split(',', 1)
            channels.append((channel_name, channel_url))
    
    # 多线程测试频道速度
    tested_results = []
    error_channels = []
    
    def worker():
        while True:
            channel_name, channel_url = task_queue.get()
            if channel_name is None:
                break
                
            result = test_channel_speed(channel_name, channel_url)
            if result:
                tested_results.append(result)
            else:
                error_channels.append((channel_name, channel_url))
            
            # 更新进度
            processed = len(tested_results) + len(error_channels)
            total = len(channels)
            percentage = (processed / total) * 100 if total > 0 else 0
            logger.info(f"进度: {processed}/{total} ({percentage:.1f}%)")
            
            task_queue.task_done()
    
    # 创建任务队列和工作线程
    task_queue = Queue()
    num_threads = 10
    
    for _ in range(num_threads):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
    
    # 添加任务到队列
    for channel in channels:
        task_queue.put(channel)
    
    # 等待所有任务完成
    task_queue.join()
    
    # 发送终止信号
    for _ in range(num_threads):
        task_queue.put((None, None))
    
    logger.info(f"测试完成: {len(tested_results)} 个可用频道, {len(error_channels)} 个不可用频道")
    
    # 对频道进行排序
    def channel_key(channel_name):
        match = re.search(r'\d+', channel_name)
        if match:
            return int(match.group())
        else:
            return float('inf')
    
    tested_results.sort(key=lambda x: (x[0], -float(x[2].split()[0])))
    tested_results.sort(key=lambda x: channel_key(x[0]))
    
    # 生成播放列表文件
    generate_playlist_files(tested_results)
    logger.info("程序执行完成")

def generate_playlist_files(results):
    """生成播放列表文件（修复文件创建逻辑）"""
    result_counter = 8  # 每个频道需要的个数
    
    # 生成txt文件
    with open("itvlist.txt", 'w', encoding='utf-8') as file:
        file.write('央视频道,#genre#\n')
        channel_counters = {}
        for result in results:
            channel_name, channel_url, speed = result
            if 'CCTV' in channel_name:
                if channel_name not in channel_counters:
                    channel_counters[channel_name] = 0
                if channel_counters[channel_name] < result_counter:
                    file.write(f"{channel_name},{channel_url}\n")
                    channel_counters[channel_name] += 1
        
        file.write('\n卫视频道,#genre#\n')
        channel_counters = {}
        for result in results:
            channel_name, channel_url, speed = result
            if '卫视' in channel_name:
                if channel_name not in channel_counters:
                    channel_counters[channel_name] = 0
                if channel_counters[channel_name] < result_counter:
                    file.write(f"{channel_name},{channel_url}\n")
                    channel_counters[channel_name] += 1
        
        file.write('\n其他频道,#genre#\n')
        channel_counters = {}
        for result in results:
            channel_name, channel_url, speed = result
            if 'CCTV' not in channel_name and '卫视' not in channel_name and '测试' not in channel_name:
                if channel_name not in channel_counters:
                    channel_counters[channel_name] = 0
                if channel_counters[channel_name] < result_counter:
                    file.write(f"{channel_name},{channel_url}\n")
                    channel_counters[channel_name] += 1
    
    # 生成m3u文件
    with open("itvlist.m3u", 'w', encoding='utf-8') as file:
        file.write('#EXTM3U\n')
        channel_counters = {}
        for result in results:
            channel_name, channel_url, speed = result
            if 'CCTV' in channel_name:
                if channel_name not in channel_counters:
                    channel_counters[channel_name] = 0
                if channel_counters[channel_name] < result_counter:
                    file.write(f'#EXTINF:-1 group-title="央视频道",{channel_name}\n')
                    file.write(f"{channel_url}\n")
                    channel_counters[channel_name] += 1
        
        channel_counters = {}
        for result in results:
            channel_name, channel_url, speed = result
            if '卫视' in channel_name:
                if channel_name not in channel_counters:
                    channel_counters[channel_name] = 0
                if channel_counters[channel_name] < result_counter:
                    file.write(f'#EXTINF:-1 group-title="卫视频道",{channel_name}\n')
                    file.write(f"{channel_url}\n")
                    channel_counters[channel_name] += 1
        
        channel_counters = {}
        for result in results:
            channel_name, channel_url, speed = result
            if 'CCTV' not in channel_name and '卫视' not in channel_name and '测试' not in channel_name:
                if channel_name not in channel_counters:
                    channel_counters[channel_name] = 0
                if channel_counters[channel_name] < result_counter:
                    file.write(f'#EXTINF:-1 group-title="其他频道",{channel_name}\n')
                    file.write(f"{channel_url}\n")
                    channel_counters[channel_name] += 1

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
