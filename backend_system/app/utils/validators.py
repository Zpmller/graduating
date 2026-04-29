"""
自定义验证器
"""
import re
from typing import Optional


def validate_ip_address(ip: Optional[str]) -> bool:
    """验证IP地址格式"""
    if ip is None:
        return True
    
    # IPv4正则表达式
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    # IPv6简单验证（简化版）
    ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    
    if re.match(ipv4_pattern, ip):
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    elif re.match(ipv6_pattern, ip):
        return True
    
    return False
