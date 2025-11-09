import eventlet
eventlet.monkey_patch()

import time
import requests
import re
import concurrent.futures
import logging
from urllib.parse import unquote
import base64

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== 配置区域 ====================
# 在这里修改配置，不需要改动代码其他部分

# 1. 选择省份（可多选）
SELECTED_PROVINCES = [
    "hebei",        # 河北
    "beijing",      # 北京  
    "guangdong",    # 广东
    "shanghai",     # 上海
    "jiangsu",      # 江苏
    "zhejiang",     # 浙江
    "shandong",     # 山东
    "henan",        # 河南
    # 添加更多省份...
]

# 2. 选择源类型（可多选）
SOURCE_TYPES = [
    "hotel",        # 酒店源
    "multicast",    # 组播源
    "unicast",      # 单播源
]

# 3. 搜索关键词配置
SEARCH_CONFIG = {
    # 省份映射
    "provinces": {
        "hebei": "河北", "beijing": "北京", "guangdong": "广东", 
        "shanghai": "上海", "tianjin": "天津", "chongqing": "重庆",
        "shanxi": "山西", "shaanxi": "陕西", "liaoning": "辽宁", 
        "jiangsu": "江苏", "zhejiang": "浙江", "anhui": "安徽",
        "fujian": "福建", "jiangxi": "江西", "shandong": "山东",
        "henan": "河南", "hubei": "湖北", "hunan": "湖南",
        "guangxi": "广西", "hainan": "海南", "sichuan": "四川",
        "guizhou": "贵州", "yunnan": "云南", "heilongjiang": "黑龙江",
        "jilin": "吉林", "taiwan": "台湾", "gansu": "甘肃",
        "qinghai": "青海", "ningxia": "宁夏", "xinjiang": "新疆",
        "xizang": "西藏", "neimenggu": "内蒙古"
    },
    
    # 源类型搜索条件
    "sources": {
        "hotel": {  # 酒店源
            "title": "酒店",
            "keywords": ["酒店", "宾馆", "旅馆", "hotel"]
        },
        "multicast": {  # 组播源
            "protocol": "udp",
            "keywords": ["组播", "multicast", "udp", "rtp"]
        },
        "unicast": {  # 单播源
            "protocol": "http", 
            "keywords": ["单播", "unicast", "http", "https"]
        }
    }
}
# ==================== 配置结束 ====================

def generate_fofa_urls(provinces, source_types):
    """根据配置生成FOFA搜索URL"""
    base_url = "https://fofa.info/result?qbase64="
    urls = []
    
    for province in provinces:
        if province not in SEARCH_CONFIG["provinces"]:
            logger.warning(f"未知省份: {province}")
            continue
            
        province_name = SEARCH_CONFIG["provinces"][province]
        
        for source_type in source_types:
            if source_type not in SEARCH_CONFIG["sources"]:
                logger.warning(f"未知源类型: {source_type}")
                continue
                
            source_config = SEARCH_CONFIG["sources"][source_type]
            
            # 构建搜索查询
            query_parts = ['"iptv/live/zh_cn.js"', 'country="CN"']
            query_parts.append(f'region="{province_name}"')
            
            # 添加源类型条件
            if "title" in source_config:
                query_parts.append(f'title="{source_config["title"]}"')
            if "protocol" in source_config:
                query_parts.append(f'protocol="{source_config["protocol"]}"')
            
            query = " && ".join(query_parts)
            query_base64 = base64.b64encode(query.encode()).decode()
            
            url = f"{base_url}{query_base64}"
            urls.append({
                "url": url,
                "province": province_name,
                "source_type": source_type,
                "query": query
            })
    
    return urls

def decode_fofa_url(url):
    """解码FOFA URL"""
    try:
        if "qbase64=" in url:
            base64_str = url.split("qbase64=")[1].split("&")[0]
            decoded = base64.b64decode(base64_str).decode('utf-8')
            return decoded
    except:
        pass
    return url

def get_fofa_results(url):
    """获取FOFA页面内容"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        logger.error(f"获取FOFA结果失败: {e}")
    return ""

def extract_ips_from_html(html_content):
    """从HTML提取IP地址"""
    ips = set()
    patterns = [
        r'http://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+',
        r'https://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+',
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+',
        r'udp://@\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+',
        r'rtp://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html_content)
        ips.update(matches)
    
    return list(ips)

def test_stream_url(stream_url):
    """测试流媒体URL有效性"""
    try:
        if stream_url.startswith(('http://', 'https://')):
            response = requests.get(stream_url, timeout=5, stream=True)
            return response.status_code == 200
        elif stream_url.startswith(('udp://', 'rtp://')):
            return True  # UDP/RTP流只验证格式
    except:
        pass
    return False

def get_stream_data(ip_port):
    """获取IP的流媒体数据"""
    test_urls = [
        f"http://{ip_port}/iptv/live/1000.json?key=txiptv",
        f"http://{ip_port}/live/1000.json",
        f"http://{ip_port}/tv/1000.json",
        f"http://{ip_port}/iptv.json",
        f"http://{ip_port}/zb/1000.json"
    ]
    
    for test_url in test_urls:
        try:
            response = requests.get(test_url, timeout=3)
            if response.status_code == 200:
                return response.json()
        except:
            continue
    return None

def classify_channel(channel_name):
    """频道分类"""
    name_lower = channel_name.lower()
    
    if any(keyword in name_lower for keyword in ['cctv', '央视', '中央']):
        return '央视'
    elif '卫视' in channel_name:
        return '卫视'
    elif any(keyword in name_lower for keyword in ['高清', 'hd', '1080', '720', '4k']):
        return '高清'
    elif any(keyword in name_lower for keyword in ['电影', '影院', 'movie', 'cinema']):
        return '电影'
    elif any(keyword in name_lower for keyword in ['娱乐', '综艺', '音乐', '戏曲', '文艺']):
        return '娱乐'
    elif any(keyword in name_lower for keyword in ['地方', '都市', '民生', '公共', '新闻']):
        return '地方'
    else:
        return '其他'

def clean_channel_name(name):
    """清理频道名称"""
    if not name:
        return ""
    
    replacements = {
        "cctv": "CCTV", "中央": "CCTV", "央视": "CCTV",
        "高清": "", "超高": "", "HD": "", "标清": "", "频道": "",
        "-": "", " ": "", "PLUS": "+", "＋": "+", "(": "", ")": ""
    }
    
    for old, new in replacements.items():
        name = name.replace(old, new)
    
    # 特殊处理
    special_cases = {
        "CCTV1综合": "CCTV1", "CCTV2财经": "CCTV2", "CCTV3综艺": "CCTV3",
        "CCTV4国际": "CCTV4", "CCTV5体育": "CCTV5", "CCTV6电影": "CCTV6",
        "CCTV7军事": "CCTV7", "CCTV8电视剧": "CCTV8", "CCTV9纪录": "CCTV9",
        "CCTV10科教": "CCTV10", "CCTV11戏曲": "CCTV11", "CCTV12社会与法": "CCTV12",
        "CCTV13新闻": "CCTV13", "CCTV14少儿": "CCTV14", "CCTV15音乐": "CCTV15",
        "CCTV16奥林匹克": "CCTV16", "CCTV17农业农村": "CCTV17"
    }
    
    for old, new in special_cases.items():
        name = name.replace(old, new)
    
    name = re.sub(r'CCTV(\d+)台', r'CCTV\1', name)
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name

def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("FOFA视频流提取器启动")
    logger.info(f"选择的省份: {', '.join(SELECTED_PROVINCES)}")
    logger.info(f"选择的源类型: {', '.join(SOURCE_TYPES)}")
    logger.info("=" * 50)
    
    # 生成搜索URL
    search_urls = generate_fofa_urls(SELECTED_PROVINCES, SOURCE_TYPES)
    logger.info(f"生成 {len(search_urls)} 个搜索URL")
    
    all_channels = []
    
    for i, search_info in enumerate(search_urls):
        url = search_info["url"]
        province = search_info["province"]
        source_type = search_info["source_type"]
        
        logger.info(f"[{i+1}/{len(search_urls)}] 搜索: {province} - {source_type}源")
        logger.info(f"查询: {search_info['query']}")
        
        try:
            html_content = get_fofa_results(url)
            if not html_content:
                continue
            
            ips = extract_ips_from_html(html_content)
            logger.info(f"找到 {len(ips)} 个IP地址")
            
            # 处理每个IP
            for ip_info in ips:
                try:
                    if '://' in ip_info:
                        ip_port = ip_info.split('://')[1]
                    else:
                        ip_port = ip_info
                    
                    stream_data = get_stream_data(ip_port)
                    if not stream_data or 'data' not in stream_data:
                        continue
                    
                    # 处理频道数据
                    for item in stream_data['data']:
                        if isinstance(item, dict):
                            name = item.get('name', '')
                            url_path = item.get('url', '')
                            
                            if not name or not url_path:
                                continue
                            
                            # 构建完整URL
                            if url_path.startswith(('http://', 'https://', 'udp://', 'rtp://')):
                                full_url = url_path
                            else:
                                full_url = f"http://{ip_port}{url_path}"
                            
                            clean_name = clean_channel_name(name)
                            category = classify_channel(clean_name)
                            
                            if test_stream_url(full_url):
                                channel_info = {
                                    'name': clean_name,
                                    'url': full_url,
                                    'category': category,
                                    'province': province,
                                    'source_type': source_type,
                                    'ip': ip_port
                                }
                                all_channels.append(channel_info)
                                logger.info(f"✓ {clean_name} [{category}] - {province}({source_type})")
                
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.error(f"处理URL时出错: {e}")
            continue
    
    # 统计结果
    logger.info("=" * 50)
    logger.info("提取完成!")
    logger.info(f"总共找到 {len(all_channels)} 个有效频道")
    
    # 按省份统计
    province_stats = {}
    for channel in all_channels:
        province = channel['province']
        if province not in province_stats:
            province_stats[province] = 0
        province_stats[province] += 1
    
    for province, count in province_stats.items():
        logger.info(f"{province}: {count} 个频道")
    
    # 按源类型统计
    source_stats = {}
    for channel in all_channels:
        source_type = channel['source_type']
        if source_type not in source_stats:
            source_stats[source_type] = 0
        source_stats[source_type] += 1
    
    for source_type, count in source_stats.items():
        logger.info(f"{source_type}源: {count} 个频道")
    
    # 生成播放列表
    if all_channels:
        generate_playlist_files(all_channels)
    else:
        logger.warning("未找到任何有效频道")
    
    logger.info("程序执行完成")

def generate_playlist_files(channels):
    """生成播放列表文件"""
    
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
        
        category_order = ['央视', '卫视', '高清', '地方', '电影', '娱乐', '其他']
        
        for category in category_order:
            if category in categorized and categorized[category]:
                for channel in categorized[category]:
                    # 添加省份和源类型信息到频道名称
                    display_name = f"{channel['name']} [{channel['province']}-{channel['source_type']}]"
                    f.write(f'#EXTINF:-1 group-title="{category}",{display_name}\n')
                    f.write(f'{channel["url"]}\n')
    
    # 生成TXT文件
    with open("itvlist.txt", 'w', encoding='utf-8') as f:
        for category in category_order:
            if category in categorized and categorized[category]:
                f.write(f'{category},#genre#\n')
                for channel in categorized[category]:
                    display_name = f"{channel['name']} [{channel['province']}-{channel['source_type']}]"
                    f.write(f'{display_name},{channel["url"]}\n')
                f.write('\n')
    
    logger.info("播放列表文件生成完成")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
