#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logger utilities for crawl4weibo
"""

import logging
import sys
from pathlib import Path


def setup_logger(name="crawl4weibo", level=logging.INFO, log_file=None):
    """
    Setup logger with console and optional file output
    
    Args:
        name (str): Logger name
        level (int): Logging level
        log_file (str, optional): Log file path
        
    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name="crawl4weibo"):
    """Get existing logger or create new one"""
    return logging.getLogger(name)