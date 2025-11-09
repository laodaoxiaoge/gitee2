import requests
import json
import re
import time
import logging
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
import sys

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IPTVExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        })
    
    def search_fofa(self, query):
        """搜索FOFA获取IP列表"""
        try:
            query_base64 = base64.b64encode(query.encode()).decode()
            url = f"https://fofa.info/result?qbase64={query_base64}"
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return self.extract_ips(response.text)
        except Exception as e:
            logger.error(f"搜索失败: {e}")
        
        return []
    
    def extract_ips(self, html_content):
        """从HTML中提取IP地址"""
        ips = set()
        patterns = [
            r'\b(?:\d{1,3}\.){3}\d{1,3}:\d+\b',
            r'http://(?:\d{1,3}\.){3}\d{1,3}:\d+',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                if '://' in match:
                    ip_port = match.split('://')[1].split('/')[0]
                else:
                    ip_port = match
                
                if self.validate_ip(ip_port):
                    ips.add(ip_port)
        
        return list(ips)
    
    def validate_ip(self, ip_port):
        """验证IP地址格式"""
        try:
            ip, port = ip_port.split(':')
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            return all(0 <= int(part) <= 255 for part in parts) and 1 <= int(port) <= 65535
        except:
            return False
    
    def test_channel_api(self, ip_port):
        """测试IP的频道API接口"""
        endpoints = [
            f"http://{ip_port}/iptv/live/1000.json?key=txiptv",
            f"http://{ip_port}/live/1000.json",
            f"http://{ip_port}/tv/1000.json",
            f"http://{ip_port}/iptv.json",
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(endpoint, timeout=5)
                if response.status_code == 200:
                    return self.parse_channels(response.json(), ip_port)
            except:
                continue
        
        return []
    
    def parse_channels(self, data, base_ip):
        """解析频道数据"""
        channels = []
        
        if isinstance(data, dict) and 'data' in data:
            for item in data['data']:
                if isinstance(item, dict):
                    name = item.get('name', '')
                    url_path = item.get('url', '')
                    
                    if name and url_path:
                        # 构建完整URL
                        if url_path.startswith(('http://', 'https://')):
                            full_url = url_path
                        else:
                            full_url = f"http://{base_ip}{url_path}"
                        
                        # 清理频道名称
                        clean_name = self.clean_channel_name(name)
                        category = self.classify_channel(clean_name)
                        
                        channels.append({
                            'name': clean_name,
                            'url': full_url,
                            'category': category,
                            'source': base_ip
                        })
        
        return channels
    
    def clean_channel_name(self, name):
        """清理频道名称"""
        if not name:
            return "未知频道"
        
        # 替换规则
        replacements = {
            "cctv": "CCTV",
            "中央": "CCTV", 
            "央视": "CCTV",
            "高清": "",
            "HD": "",
            "标清": "",
            "频道": "",
            "(": "",
            ")": "",
            "[": "",
            "]": ""
        }
        
        for old, new in replacements.items():
            name = name.replace(old, new)
        
        name = re.sub(r'\s+', ' ', name).strip()
        return name if name else "未知频道"
    
    def classify_channel(self, name):
        """频道分类"""
        name_lower = name.lower()
        
        if any(keyword in name_lower for keyword in ['cctv', '央视', '中央']):
            return '央视'
        elif '卫视' in name:
            return '卫视'
        elif any(keyword in name_lower for keyword in ['电影', '影院']):
            return '电影'
        elif any(keyword in name_lower for keyword in ['娱乐', '综艺', '音乐']):
            return '娱乐'
        else:
            return '其他'
    
    def test_channel_speed(self, channel):
        """测试频道速度"""
        try:
            if channel['url'].startswith(('http://', 'https://')):
                start_time = time.time()
                response = self.session.head(channel['url'], timeout=5)
                if response.status_code == 200:
                    return True
        except:
            pass
        return False

def main():
    """主函数"""
    extractor = IPTVExtractor()
    
    # 搜索配置
    search_queries = [
        'title="IPTV" && country="CN"',
        'body=".m3u8" && country="CN"',
        'title="直播" && country="CN"',
    ]
    
    all_channels = []
    
    for query in search_queries:
        logger.info(f"搜索: {query}")
        ips = extractor.search_fofa(query)
        logger.info(f"找到 {len(ips)} 个IP")
        
        for ip in ips:
            logger.info(f"测试IP: {ip}")
            channels = extractor.test_channel_api(ip)
            
            if channels:
                # 测试频道可用性
                valid_channels = []
                for channel in channels:
                    if extractor.test_channel_speed(channel):
                        valid_channels.append(channel)
                
                if valid_channels:
                    all_channels.extend(valid_channels)
                    logger.info(f"从 {ip} 获取到 {len(valid_channels)} 个有效频道")
    
    # 去重
    unique_channels = []
    seen = set()
    
    for channel in all_channels:
        key = (channel['name'], channel['url'])
        if key not in seen:
            unique_channels.append(channel)
            seen.add(key)
    
    logger.info(f"总共找到 {len(unique_channels)} 个唯一频道")
    
    # 生成播放列表
    if unique_channels:
        generate_playlist(unique_channels)
    else:
        create_empty_playlist()

def generate_playlist(channels):
    """生成播放列表"""
    # 按分类分组
    categorized = {}
    for channel in channels:
        category = channel['category']
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(channel)
    
    # 生成M3U文件
    with open("itvlist.m3u", 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        
        for category, channel_list in categorized.items():
            for channel in channel_list:
                f.write(f'#EXTINF:-1 group-title="{category}",{channel["name"]}\n')
                f.write(f'{channel["url"]}\n')
    
    # 生成TXT文件
    with open("itvlist.txt", 'w', encoding='utf-8') as f:
        for category, channel_list in categorized.items():
            f.write(f'{category},#genre#\n')
            for channel in channel_list:
                f.write(f'{channel["name"]},{channel["url"]}\n')
            f.write('\n')
    
    logger.info("播放列表生成完成")

def create_empty_playlist():
    """创建空播放列表"""
    with open("itvlist.m3u", 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        f.write('# 未找到可用频道\n')
    
    with open("itvlist.txt", 'w', encoding='utf-8') as f:
        f.write('未找到可用频道,#genre#\n')
    
    logger.info("创建了空的播放列表")

if __name__ == "__main__":
    main()
