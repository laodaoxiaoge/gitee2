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

eventlet.monkey_patch()

urls = [
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iSGViZWki",
    # ... 其他URL保持不变
]

def modify_urls(url):
    """修改URL生成测试地址"""
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
    """检查URL是否可访问"""
    try:
        response = requests.get(url, timeout=0.5)
        if response.status_code == 200:
            return url
    except:
        pass
    return None

def main():
    """主函数"""
    results = []
    
    for url in urls:
        # 创建Chrome浏览器实例
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # 访问网页
            driver.get(url)
            time.sleep(10)
            
            # 获取页面内容
            page_content = driver.page_source

            # 查找URL
            pattern = r"http://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+"
            urls_all = re.findall(pattern, page_content)
            urls_set = set(urls_all)
            
            # 处理URL（将IP第四位改为1）
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
            
            # 去重
            unique_urls = set(processed_urls)
            valid_urls = []

            # 多线程测试URL可用性
            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                futures = []
                for url_item in unique_urls:
                    modified_urls_list = modify_urls(url_item)
                    for modified_url in modified_urls_list:
                        futures.append(executor.submit(is_url_accessible, modified_url))

                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        valid_urls.append(result)
                        print(f"✅ 可用URL: {result}")

            # 处理每个可用的URL
            for url_item in valid_urls:
                try:
                    # 获取JSON数据
                    response = requests.get(url_item, timeout=0.5)
                    json_data = response.json()

                    # 解析频道数据
                    if 'data' in json_data:
                        for item in json_data['data']:
                            if isinstance(item, dict):
                                name = item.get('name', '')
                                urlx = item.get('url', '')
                                
                                if not name or not urlx:
                                    continue
                                
                                # 处理URL格式
                                if ',' in urlx:
                                    continue
                                    
                                if 'http' in urlx:
                                    final_url = urlx
                                else:
                                    # 构建完整URL
                                    ip_start_index = url_item.find("//") + 2
                                    ip_dot_start = url_item.find(".") + 1
                                    ip_index_second = url_item.find("/", ip_dot_start)
                                    base_url_part = url_item[:ip_start_index]
                                    ip_address_part = url_item[ip_start_index:ip_index_second]
                                    url_base = f"{base_url_part}{ip_address_part}"
                                    final_url = f"{url_base}{urlx}"

                                # 清理频道名称
                                if name:
                                    name = name.replace("cctv", "CCTV")
                                    name = name.replace("中央", "CCTV")
                                    name = name.replace("央视", "CCTV")
                                    name = name.replace("高清", "")
                                    name = name.replace("超高", "")
                                    name = name.replace("HD", "")
                                    name = name.replace("标清", "")
                                    name = name.replace("频道", "")
                                    name = name.replace("-", "")
                                    name = name.replace(" ", "")
                                    name = name.replace("PLUS", "+")
                                    name = name.replace("＋", "+")
                                    name = name.replace("(", "")
                                    name = name.replace(")", "")
                                    name = re.sub(r"CCTV(\d+)台", r"CCTV\1", name)
                                    
                                    # 添加更多清理规则...
                                    
                                    results.append(f"{name},{final_url}")
                                    print(f"📺 找到频道: {name}")
                except Exception as e:
                    print(f"❌ 处理URL失败: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ 处理主URL失败: {e}")
        finally:
            driver.quit()

    # 去重结果
    unique_results = list(set(results))
    
    # 测试频道速度
    channels = []
    for result in unique_results:
        if ',' in result:
            channel_name, channel_url = result.split(',', 1)
            channels.append((channel_name, channel_url))

    # 多线程测试频道速度
    def test_channel(channel_name, channel_url):
        try:
            # 获取M3U8内容
            channel_url_base = channel_url.rstrip(channel_url.split('/')[-1])
            response = requests.get(channel_url, timeout=1)
            lines = response.text.strip().split('\n')
            ts_files = [line.split('/')[-1] for line in lines if line and not line.startswith('#')]
            
            if ts_files:
                ts_file = ts_files[0].split('.ts')[0] + '.ts'
                ts_url = channel_url_base + ts_file
                
                # 测试下载速度
                start_time = time.time()
                content = requests.get(ts_url, timeout=1).content
                end_time = time.time()
                
                if content:
                    file_size = len(content)
                    download_time = end_time - start_time
                    speed = file_size / download_time / 1024 / 1024  # MB/s
                    
                    # 清理临时文件（如果创建了的话）
                    if os.path.exists(ts_file):
                        os.remove(ts_file)
                    
                    return channel_name, channel_url, f"{speed:.3f} MB/s"
        except:
            pass
        return None

    # 并行测试所有频道
    working_channels = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(test_channel, name, url): (name, url) for name, url in channels}
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                working_channels.append(result)
                name, url, speed = result
                print(f"✅ 频道可用: {name} - 速度: {speed}")

    # 生成播放列表文件
    if working_channels:
        # 按频道名称排序
        def get_channel_number(name):
            match = re.search(r'\d+', name)
            return int(match.group()) if match else 9999
        
        working_channels.sort(key=lambda x: (get_channel_number(x[0]), x[0]))
        
        # 生成M3U文件
        with open("itvlist.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            
            # 央视频道
            for name, url, speed in working_channels:
                if "CCTV" in name:
                    f.write(f"#EXTINF:-1 group-title=\"央视频道\",{name}\n")
                    f.write(f"{url}\n")
            
            # 卫视频道
            for name, url, speed in working_channels:
                if "卫视" in name:
                    f.write(f"#EXTINF:-1 group-title=\"卫视频道\",{name}\n")
                    f.write(f"{url}\n")
            
            # 其他频道
            for name, url, speed in working_channels:
                if "CCTV" not in name and "卫视" not in name:
                    f.write(f"#EXTINF:-1 group-title=\"其他频道\",{name}\n")
                    f.write(f"{url}\n")
        
        # 生成TXT文件
        with open("itvlist.txt", "w", encoding="utf-8") as f:
            f.write("央视频道,#genre#\n")
            for name, url, speed in working_channels:
                if "CCTV" in name:
                    f.write(f"{name},{url}\n")
            
            f.write("\n卫视频道,#genre#\n")
            for name, url, speed in working_channels:
                if "卫视" in name:
                    f.write(f"{name},{url}\n")
            
            f.write("\n其他频道,#genre#\n")
            for name, url, speed in working_channels:
                if "CCTV" not in name and "卫视" not in name:
                    f.write(f"{name},{url}\n")
        
        print(f"🎉 完成! 生成 {len(working_channels)} 个可用频道")
    else:
        print("❌ 没有找到可用的频道")

if __name__ == "__main__":
    main()
