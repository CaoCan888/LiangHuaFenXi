# -*- coding: utf-8 -*-
"""
预警系统模块
"""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AlertRule:
    """预警规则"""
    
    def __init__(self, name: str, condition: Callable, message_template: str):
        self.name = name
        self.condition = condition
        self.message_template = message_template
        self.enabled = True


class AlertSystem:
    """预警系统"""
    
    def __init__(self):
        self.rules: List[AlertRule] = []
        self.triggered_alerts: List[Dict] = []
    
    def add_price_alert(self, stock_code: str, target_price: float, direction: str = 'above'):
        """添加价格预警"""
        def condition(data):
            current_price = data.get('price', 0)
            if direction == 'above':
                return current_price >= target_price
            else:
                return current_price <= target_price
        
        msg = f"{{stock_code}} 价格触发预警: 当前价格 {{price}} {'突破' if direction == 'above' else '跌破'} {target_price}"
        
        rule = AlertRule(f"price_alert_{stock_code}_{target_price}", condition, msg)
        self.rules.append(rule)
        logger.info(f"添加价格预警: {stock_code} {direction} {target_price}")
    
    def add_indicator_alert(self, stock_code: str, indicator: str, threshold: float, direction: str = 'above'):
        """添加指标预警"""
        def condition(data):
            value = data.get(indicator, 0)
            if direction == 'above':
                return value >= threshold
            else:
                return value <= threshold
        
        msg = f"{{stock_code}} {indicator} 触发预警: {direction} {threshold}"
        
        rule = AlertRule(f"indicator_{stock_code}_{indicator}", condition, msg)
        self.rules.append(rule)
    
    def check_alerts(self, data: Dict[str, Any]) -> List[Dict]:
        """检查预警"""
        triggered = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                if rule.condition(data):
                    alert = {
                        'rule_name': rule.name,
                        'message': rule.message_template.format(**data),
                        'triggered_at': datetime.now(),
                        'data': data
                    }
                    triggered.append(alert)
                    self.triggered_alerts.append(alert)
                    logger.warning(f"预警触发: {alert['message']}")
            except Exception as e:
                logger.error(f"检查预警规则失败: {rule.name}, {e}")
        
        return triggered
    
    def send_email_notification(self, alerts: List[Dict]):
        """发送邮件通知"""
        if not settings.alert.email_enabled:
            return
        
        if not alerts:
            return
        
        try:
            content = "预警通知:\n\n"
            for alert in alerts:
                content += f"- {alert['message']}\n  时间: {alert['triggered_at']}\n\n"
            
            msg = MIMEText(content, 'plain', 'utf-8')
            msg['Subject'] = f"股票预警通知 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            msg['From'] = settings.alert.email_username
            msg['To'] = ','.join(settings.alert.email_receivers)
            
            with smtplib.SMTP_SSL(settings.alert.email_host, settings.alert.email_port) as server:
                server.login(settings.alert.email_username, settings.alert.email_password)
                server.send_message(msg)
            
            logger.info(f"邮件通知发送成功: {len(alerts)}条预警")
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
    
    def clear_rules(self):
        """清除所有规则"""
        self.rules.clear()
    
    def get_triggered_alerts(self) -> List[Dict]:
        """获取已触发的预警"""
        return self.triggered_alerts


alert_system = AlertSystem()
