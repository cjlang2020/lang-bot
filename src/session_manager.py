"""
会话管理模块 - 管理对话历史和最后一次发送给大模型的消息
单用户模式：程序启动自动加载，AI返回后更新
"""

import os
import json
from typing import List, Dict
from datetime import datetime

from botpy import logging

_log = logging.get_logger()

# 持久化文件路径
MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "memory.json")

# 历史消息最大条数（避免消息太长）
MAX_HISTORY_LENGTH = 20

# 最后一次发送给大模型的消息（包含系统提示词和完整对话历史）
last_ai_messages: Dict = {}

# 最后发送的图片路径（用于引用历史图片）
last_images: List[str] = []


def _ensure_data_dir():
    """确保 data 目录存在"""
    data_dir = os.path.dirname(MEMORY_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        _log.info(f"创建数据目录: {data_dir}")


def save_to_file():
    """
    保存最后一次AI消息到文件
    """
    _ensure_data_dir()
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(last_ai_messages, f, ensure_ascii=False, indent=2)
        _log.info(f"[持久化] 消息已保存，共 {len(last_ai_messages.get('messages', []))} 条")
    except Exception as e:
        _log.error(f"[持久化] 保存失败: {e}")


def load_from_file():
    """
    从文件加载最后一次AI消息
    """
    global last_ai_messages
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                last_ai_messages = json.load(f)
            msg_count = len(last_ai_messages.get("messages", []))
            model = last_ai_messages.get("model", "未知")
            _log.info(f"[持久化] 加载历史消息，模型: {model}，消息数: {msg_count}")
        except Exception as e:
            _log.error(f"[持久化] 加载失败: {e}")
            last_ai_messages = {}
    else:
        _log.info("[持久化] 没有历史消息文件")


def get_history_messages() -> List[Dict]:
    """
    获取历史对话消息（不含系统提示词），限制数量避免上下文过长

    Returns:
        List[Dict]: 历史消息列表
    """
    messages = last_ai_messages.get("messages", [])
    # 过滤掉系统提示词，只返回对话历史
    history = [msg for msg in messages if msg.get("role") != "system"]

    # 限制历史消息数量（保留最近的N条）
    if len(history) > MAX_HISTORY_LENGTH:
        history = history[-MAX_HISTORY_LENGTH:]
        _log.info(f"[历史] 截取最近 {MAX_HISTORY_LENGTH} 条消息")

    return history


def get_last_images() -> List[str]:
    """
    获取最后发送的图片路径

    Returns:
        List[str]: 图片路径列表
    """
    return last_images


def set_last_images(image_paths: List[str]):
    """
    保存最后发送的图片路径

    Args:
        image_paths: 图片路径列表
    """
    global last_images
    last_images = image_paths
    _log.info(f"[图片] 保存图片路径: {image_paths}")


def update_last_ai_messages(messages: List[Dict], model: str):
    """
    更新最后一次发送给大模型的消息（大模型返回后调用）

    Args:
        messages: 消息列表（包含系统提示词）
        model: 模型名称
    """
    global last_ai_messages

    # 处理消息，移除图片的Base64数据（文本中已包含图片路径）
    simplified_messages = []
    for msg in messages:
        msg_copy = msg.copy()
        content = msg_copy.get("content")

        if isinstance(content, list):
            # 多模态消息，移除 image_url 部分，只保留文本
            text_content = ""
            for item in content:
                if item.get("type") == "text":
                    text_content = item.get("text", "")
                    break
            # 保存为纯文本（文本中已包含图片路径）
            msg_copy["content"] = text_content

        # 注意：如果content是None（工具调用情况），保留原样
        # 同时保留tool_calls字段

        simplified_messages.append(msg_copy)

    # 限制保存的消息数量（保留系统提示词 + 最近的历史消息）
    system_msg = None
    other_msgs = []
    for msg in simplified_messages:
        if msg.get("role") == "system":
            system_msg = msg
        else:
            other_msgs.append(msg)

    # 保留最近的对话历史
    if len(other_msgs) > MAX_HISTORY_LENGTH:
        other_msgs = other_msgs[-MAX_HISTORY_LENGTH:]
        _log.info(f"[持久化] 保存最近 {MAX_HISTORY_LENGTH} 条消息")

    # 重新组合
    final_messages = [system_msg] + other_msgs if system_msg else other_msgs

    last_ai_messages = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": model,
        "messages": final_messages
    }

    # 保存到文件
    save_to_file()


def clear_history():
    """
    清空对话历史
    """
    global last_ai_messages, last_images
    last_ai_messages = {}
    last_images = []
    save_to_file()
    _log.info("[持久化] 对话历史已清空")


def get_stats() -> Dict:
    """
    获取统计信息

    Returns:
        Dict: 统计信息字典
    """
    messages = last_ai_messages.get("messages", [])
    message_count = len(messages)

    # 统计图片数量和文本长度
    image_count = 0
    text_length = 0

    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            text_length += len(content)
        elif isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    text_length += len(item.get("text", ""))
                elif item.get("type") == "image_url":
                    image_count += 1

    # 估算token数量
    estimated_tokens = text_length // 2

    return {
        "message_count": message_count,
        "image_count": image_count,
        "text_length": text_length,
        "estimated_tokens": estimated_tokens,
        "model": last_ai_messages.get("model", "未知"),
        "timestamp": last_ai_messages.get("timestamp", "")
    }


# 模块加载时自动从文件恢复
load_from_file()