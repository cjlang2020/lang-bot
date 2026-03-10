"""
会话管理模块 - 管理用户会话历史和过期清理
支持将对话历史持久化到文件，程序重启后自动恢复
"""

import os
import json
import random
from typing import Dict, List
from datetime import datetime

from botpy import logging
from src.config import SESSION_EXPIRE_TIME, MAX_HISTORY_LENGTH

_log = logging.get_logger()

# 会话持久化文件路径
MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "memory.json")

# 会话缓存：存储每个会话的历史对话和最后图片路径
# 结构：{ session_id: {"messages": [...], "last_images": [...], "last_active": timestamp} }
session_histories: Dict[str, Dict] = {}


def _ensure_data_dir():
    """确保 data 目录存在"""
    data_dir = os.path.dirname(MEMORY_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        _log.info(f"创建数据目录: {data_dir}")


def save_to_file():
    """
    将会话历史保存到文件
    """
    _ensure_data_dir()
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(session_histories, f, ensure_ascii=False, indent=2)
        _log.info(f"[持久化] 会话已保存到文件，共 {len(session_histories)} 个会话")
    except Exception as e:
        _log.error(f"[持久化] 保存会话失败: {e}")


def load_from_file():
    """
    从文件加载会话历史
    """
    global session_histories
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                session_histories = json.load(f)
            _log.info(f"[持久化] 从文件加载会话，共 {len(session_histories)} 个会话")
            # 统计消息总数
            total_messages = sum(
                len(s.get("messages", []))
                for s in session_histories.values()
            )
            _log.info(f"[持久化] 总消息数: {total_messages}")
        except Exception as e:
            _log.error(f"[持久化] 加载会话失败: {e}")
            session_histories = {}
    else:
        _log.info("[持久化] 没有找到历史会话文件，创建新的会话缓存")


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
    向会话添加消息并保存到文件

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

    # 保存到文件
    save_to_file()


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
    # 如果过期时间为0，表示永不过期，跳过清理
    if SESSION_EXPIRE_TIME <= 0:
        return

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
        # 清理后保存到文件
        save_to_file()


def maybe_cleanup():
    """
    随机触发会话清理（10%概率）
    """
    if len(session_histories) > 0 and random.random() < 0.1:
        _log.info(f"开始清理过期会话，当前会话数: {len(session_histories)}")
        cleanup_expired_sessions()


def clear_session(session_id: str) -> bool:
    """
    清理指定会话的所有历史记录

    Args:
        session_id: 会话ID

    Returns:
        bool: 是否成功清理（True=存在并已清理，False=不存在）
    """
    if session_id in session_histories:
        del session_histories[session_id]
        _log.info(f"[Session:{session_id}] 会话已清理")
        # 清理后保存到文件
        save_to_file()
        return True
    return False


def get_session_stats(session_id: str) -> Dict:
    """
    获取指定会话的统计信息

    Args:
        session_id: 会话ID

    Returns:
        Dict: 包含统计信息的字典
    """
    if session_id not in session_histories:
        return {
            "message_count": 0,
            "image_count": 0,
            "text_length": 0,
            "estimated_tokens": 0
        }

    messages = session_histories[session_id].get("messages", [])
    message_count = len(messages)

    # 统计图片数量和文本长度
    image_count = 0
    text_length = 0

    for msg in messages:
        content = msg.get("content", "")
        text_length += len(content)
        # 统计图片数量（通过图片路径标记）
        image_count += content.count("- D:\\")
        image_count += content.count("- /")  # Linux路径

    # 估算token数量（中文约1.5字符/token，英文约4字符/token，取平均2字符/token）
    estimated_tokens = text_length // 2

    return {
        "message_count": message_count,
        "image_count": image_count,
        "text_length": text_length,
        "estimated_tokens": estimated_tokens
    }


# 模块加载时自动从文件恢复会话
load_from_file()