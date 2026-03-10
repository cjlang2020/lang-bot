"""
会话管理模块 - 管理用户会话历史和过期清理
"""

import random
from typing import Dict, List
from datetime import datetime

from botpy import logging
from src.config import SESSION_EXPIRE_TIME, MAX_HISTORY_LENGTH

_log = logging.get_logger()

# 会话缓存：存储每个会话的历史对话和最后图片路径
# 结构：{ session_id: {"messages": [...], "last_images": [...], "last_active": timestamp} }
session_histories: Dict[str, Dict] = {}


def get_session(session_id: str) -> List[Dict[str, str]]:
    """
    获取指定会话的历史消息

    Args:
        session_id: 会话ID

    Returns:
        List[Dict]: 历史消息列表
    """
    if session_id in session_histories:
        return session_histories[session_id].get("messages", [])
    return []


def get_last_images(session_id: str) -> List[str]:
    """
    获取会话中最后发送的图片路径列表

    Args:
        session_id: 会话ID

    Returns:
        List[str]: 图片路径列表
    """
    if session_id in session_histories:
        return session_histories[session_id].get("last_images", [])
    return []


def set_last_images(session_id: str, image_paths: List[str]):
    """
    保存会话中最后发送的图片路径

    Args:
        session_id: 会话ID
        image_paths: 图片路径列表
    """
    if session_id not in session_histories:
        session_histories[session_id] = {
            "messages": [],
            "last_images": [],
            "last_active": datetime.now().timestamp()
        }

    session_histories[session_id]["last_images"] = image_paths
    session_histories[session_id]["last_active"] = datetime.now().timestamp()
    _log.info(f"[Session:{session_id}] 保存图片路径: {image_paths}")


def add_to_session(session_id: str, role: str, content: str, image_paths: List[str] = None):
    """
    向会话添加消息

    Args:
        session_id: 会话ID
        role: 消息角色（user/assistant）
        content: 消息内容
        image_paths: 图片路径列表（可选）
    """
    if session_id not in session_histories:
        session_histories[session_id] = {
            "messages": [],
            "last_images": [],
            "last_active": datetime.now().timestamp()
        }

    # 构建消息内容，如果有图片则保存完整路径信息
    if image_paths:
        msg_content = f"{content}\n\n图片路径：\n"
        for path in image_paths:
            msg_content += f"- {path}\n"
    else:
        msg_content = content

    session_histories[session_id]["messages"].append({
        "role": role,
        "content": msg_content
    })
    session_histories[session_id]["last_active"] = datetime.now().timestamp()

    # 限制历史记录长度
    if len(session_histories[session_id]["messages"]) > MAX_HISTORY_LENGTH:
        session_histories[session_id]["messages"] = session_histories[session_id]["messages"][-MAX_HISTORY_LENGTH:]

    _log.info(f"[Session:{session_id}] 对话历史已更新，当前长度: {len(session_histories[session_id]['messages'])}")


def session_exists(session_id: str) -> bool:
    """
    检查会话是否存在

    Args:
        session_id: 会话ID

    Returns:
        bool: 会话是否存在
    """
    return session_id in session_histories


def cleanup_expired_sessions():
    """
    清理过期的会话
    """
    current_time = datetime.now().timestamp()
    expired_sessions = []

    for session_id, session_data in session_histories.items():
        last_active = session_data.get("last_active", 0)
        if current_time - last_active > SESSION_EXPIRE_TIME:
            expired_sessions.append(session_id)

    for session_id in expired_sessions:
        del session_histories[session_id]
        _log.info(f"[Session:{session_id}] 会话已过期，已清理")

    if expired_sessions:
        _log.info(f"清理完成，清理了 {len(expired_sessions)} 个过期会话")


def maybe_cleanup():
    """
    随机触发会话清理（10%概率）
    """
    if len(session_histories) > 0 and random.random() < 0.1:
        _log.info(f"开始清理过期会话，当前会话数: {len(session_histories)}")
        cleanup_expired_sessions()