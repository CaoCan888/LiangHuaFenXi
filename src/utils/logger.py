# -*- coding: utf-8 -*-
"""
Stock Analysis System - Logger Configuration
日志配置模块
"""

import os
import sys
from loguru import logger

# 移除默认处理器
logger.remove()


def setup_logger(
    level: str = "INFO",
    log_dir: str = "logs",
    rotation: str = "10 MB",
    retention: str = "30 days"
):
    """
    配置日志系统
    
    Args:
        level: 日志级别
        log_dir: 日志目录
        rotation: 日志轮转大小
        retention: 日志保留时间
    """
    # 创建日志目录
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 控制台日志格式 - 简洁版
    console_format = "<level>{level: <5}</level> | {message}"
    
    # 文件日志格式 - 详细版
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} - "
        "{message}"
    )
    
    # 控制台输出 - 只显示WARNING及以上，或者可以通过环境变量控制
    console_level = os.environ.get('LOG_LEVEL', 'WARNING')
    logger.add(
        sys.stdout,
        format=console_format,
        level=console_level,
        colorize=True
    )
    
    # 文件输出 - 所有日志
    logger.add(
        os.path.join(log_dir, "app_{time:YYYY-MM-DD}.log"),
        format=file_format,
        level=level,
        rotation=rotation,
        retention=retention,
        encoding="utf-8"
    )
    
    # 文件输出 - 错误日志
    logger.add(
        os.path.join(log_dir, "error_{time:YYYY-MM-DD}.log"),
        format=file_format,
        level="ERROR",
        rotation=rotation,
        retention=retention,
        encoding="utf-8"
    )
    return logger


def get_logger(name: str = None):
    """
    获取日志实例
    
    Args:
        name: 日志名称
        
    Returns:
        logger实例
    """
    if name:
        return logger.bind(name=name)
    return logger


# 默认初始化
setup_logger()
