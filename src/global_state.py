"""
全局状态模块 - 存储QQ机器人的API实例和用户信息
用于在HTTP接口中发送消息给QQ用户
"""

import asyncio
from typing import Optional, Any
from botpy import logging

_log = logging.get_logger()

# 全局API实例（用于发送消息）
_bot_api: Optional[Any] = None

# 用户openid（消息接收者）
_user_openid: Optional[str] = None

# Bot的事件循环（用于跨线程调度异步任务）
_bot_loop: Optional[asyncio.AbstractEventLoop] = None


def set_bot_api(api: Any) -> None:
    """设置Bot API实例"""
    global _bot_api
    _bot_api = api
    _log.info("[全局状态] Bot API实例已设置")


def get_bot_api() -> Optional[Any]:
    """获取Bot API实例"""
    return _bot_api


def set_user_openid(openid: str) -> None:
    """设置用户OpenID"""
    global _user_openid
    _user_openid = openid
    _log.info(f"[全局状态] 用户OpenID已设置: {openid}")


def get_user_openid() -> Optional[str]:
    """获取用户OpenID"""
    return _user_openid


def set_bot_loop(loop: asyncio.AbstractEventLoop) -> None:
    """设置Bot的事件循环"""
    global _bot_loop
    _bot_loop = loop
    _log.info("[全局状态] Bot事件循环已设置")


def get_bot_loop() -> Optional[asyncio.AbstractEventLoop]:
    """获取Bot的事件循环"""
    return _bot_loop


def send_message_to_user_sync(content: str) -> tuple[bool, str]:
    """
    同步方式发送消息给QQ用户（用于HTTP接口调用）
    
    使用 run_coroutine_threadsafe 在 Bot 的事件循环中执行异步调用
    
    Args:
        content: 消息内容
    
    Returns:
        tuple[bool, str]: (是否成功, 错误信息或成功提示)
    """
    global _bot_api, _user_openid, _bot_loop
    
    if not _bot_api:
        return False, "Bot API未初始化"
    
    if not _user_openid:
        return False, "用户OpenID未设置（请先通过QQ发送一条消息给机器人）"
    
    if not _bot_loop:
        return False, "Bot事件循环未设置"
    
    try:
        # 创建协程
        async def _send():
            await _bot_api.post_c2c_message(
                openid=_user_openid,
                msg_type=0,
                msg_id=None,
                msg_seq=1,
                content=content
            )
        
        # 在Bot的事件循环中调度执行
        future = asyncio.run_coroutine_threadsafe(_send(), _bot_loop)
        # 等待完成（超时10秒）
        future.result(timeout=10)
        
        _log.info(f"[消息发送] 成功发送消息给用户: {content[:50]}...")
        return True, "消息发送成功"
    except Exception as e:
        error_msg = f"发送消息失败: {str(e)}"
        _log.error(f"[消息发送] {error_msg}")
        return False, error_msg