"""
机器人客户端模块 - 处理QQ消息的接收和回复
"""

import asyncio
import time
import botpy
from botpy import logging
from botpy.message import C2CMessage

from src.ai_client import process_message_with_ai, fetch_available_models, get_model_name, get_model_info
from src.image_handler import process_image_attachment
from src.session_manager import clear_history, get_stats

_log = logging.get_logger()

# 消息发送间隔（秒），根据消息长度动态调整
MESSAGE_INTERVAL_SHORT = 4.0   # 短消息（≤20字）
MESSAGE_INTERVAL_MEDIUM = 5.0  # 中等消息（21-100字）
MESSAGE_INTERVAL_LONG = 6.0    # 长消息（>100字）


def _calculate_interval(content: str) -> float:
    """根据消息长度计算发送间隔"""
    length = len(content)
    if length <= 20:
        return MESSAGE_INTERVAL_SHORT
    elif length <= 100:
        return MESSAGE_INTERVAL_MEDIUM
    else:
        return MESSAGE_INTERVAL_LONG
_last_send_time = 0


def handle_command(text_content: str) -> str | None:
    """
    处理 "/" 开头的指令

    Args:
        text_content: 消息内容

    Returns:
        str | None: 指令处理结果，如果不是指令则返回None
    """
    if not text_content.startswith("/"):
        return None

    command = text_content.strip().lower()

    if command == "/清理":
        clear_history()
        return "已被洗脑，我将不记得之前的事情！"

    if command == "/会话":
        stats = get_stats()
        model_name = get_model_name() or "未设置"
        model_info = get_model_info()
        msg_count = stats["message_count"]
        img_count = stats["image_count"]
        tokens = stats["estimated_tokens"]

        # 格式化上下文长度
        n_ctx = model_info.get("n_ctx_train", 0)
        context_str = f"{n_ctx:,}" if n_ctx > 0 else "未知"

        # 格式化参数数量
        n_params = model_info.get("n_params", 0)
        if n_params > 0:
            if n_params >= 1e9:
                params_str = f"{n_params/1e9:.1f}B"
            elif n_params >= 1e6:
                params_str = f"{n_params/1e6:.1f}M"
            else:
                params_str = f"{n_params:,}"
        else:
            params_str = "未知"

        # 格式化模型大小
        size = model_info.get("size", 0)
        if size > 0:
            if size >= 1e9:
                size_str = f"{size/1e9:.1f}GB"
            elif size >= 1e6:
                size_str = f"{size/1e6:.1f}MB"
            else:
                size_str = f"{size:,}B"
        else:
            size_str = "未知"

        # 模型能力
        capabilities = model_info.get("capabilities", [])
        cap_str = ", ".join(capabilities) if capabilities else "未知"

        return (
            f"📊 会话统计\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📝 消息记录: {msg_count}\n"
            f"🖼️ 图片数量: {img_count}\n"
            f"🎯 预估Token: ~{tokens}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🤖 模型: {model_name}\n"
            f"📏 上下文: {context_str}\n"
            f"🔢 参数量: {params_str}\n"
            f"💾 模型大小: {size_str}\n"
            f"⚡ 能力: {cap_str}"
        )

    return f"未知指令: {text_content}"


class MyClient(botpy.Client):
    """QQ机器人客户端"""

    async def on_ready(self):
        """机器人启动就绪"""
        _log.info(f"robot 「{self.robot.name}」 on_ready!")
        await fetch_available_models()
        _log.info(f"已设置AI模型: {get_model_name()}")

    async def on_c2c_message_create(self, message: C2CMessage):
        """
        监听C2C消息（个人对个人）

        Args:
            message: C2C消息对象
        """
        text_content = message.content or ""
        image_paths = []

        # 检查是否是指令
        command_response = handle_command(text_content)
        if command_response is not None:
            await message.reply(content=command_response)
            return

        # 检查是否有图片附件
        if message.attachments and len(message.attachments) > 0:
            for attachment in message.attachments:
                save_path, error = await process_image_attachment(attachment)
                if save_path:
                    _log.info(f"[C2C] 图片下载成功: {save_path}")
                    image_paths.append(save_path)
                elif error:
                    _log.error(f"[C2C] 图片处理失败: {error}")

        # 维护一个消息序号计数器，用于避免消息去重
        msg_seq_counter = 1

        # 定义发送中间结果的回调函数（添加延迟和不同的msg_seq，避免消息去重）
        async def send_intermediate_result(content: str):
            """发送中间结果给用户（根据消息长度动态调整延迟，并使用递增的msg_seq）"""
            nonlocal msg_seq_counter
            global _last_send_time
            try:
                # 根据消息长度计算间隔时间
                interval = _calculate_interval(content)

                # 计算需要等待的时间
                current_time = time.time()
                elapsed = current_time - _last_send_time
                wait_time = interval - elapsed

                if wait_time > 0:
                    _log.info(f"[回调] 消息长度 {len(content)}，等待 {wait_time:.1f} 秒后发送...")
                    await asyncio.sleep(wait_time)

                # 使用递增的msg_seq发送消息，避免被判定为重复消息
                msg_seq = msg_seq_counter
                msg_seq_counter += 1

                # 调用底层API，传入msg_seq参数
                await message._api.post_c2c_message(
                    openid=message.author.user_openid,
                    msg_type=0,
                    msg_id=message.id,
                    msg_seq=msg_seq,
                    content=content
                )

                _last_send_time = time.time()
                _log.info(f"[回调] 已发送中间结果 (msg_seq={msg_seq}): {content[:50]}...")
            except Exception as e:
                _log.error(f"[回调] 发送中间结果失败: {e}")

        # 调用AI处理消息（传入回调函数）
        ai_response = await process_message_with_ai(text_content, image_paths, send_intermediate_result)

        # 最终回复不再发送，因为中间过程已经发送了最后一次AI回复
        if not ai_response:
            await message.reply(content="抱歉，暂时无法处理您的消息。")