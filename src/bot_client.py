"""
机器人客户端模块 - 处理QQ消息的接收和回复
"""

import botpy
from botpy import logging
from botpy.message import C2CMessage

from src.ai_client import process_message_with_ai, fetch_available_models, get_model_name
from src.image_handler import process_image_attachment, get_month_folder
from src.config import AI_MODEL_NAME, MAX_HISTORY_LENGTH
from src.session_manager import clear_session, get_session_stats

_log = logging.get_logger()


def handle_command(text_content: str, session_id: str) -> str | None:
    """
    处理 "/" 开头的指令

    Args:
        text_content: 消息内容
        session_id: 会话ID

    Returns:
        str | None: 指令处理结果，如果不是指令则返回None
    """
    if not text_content.startswith("/"):
        return None

    # 提取指令（去掉开头的 "/"）
    command = text_content.strip().lower()

    if command == "/清理":
        clear_session(session_id)
        return "已被洗脑，我将不记得之前的事情！"

    if command == "/会话":
        stats = get_session_stats(session_id)
        model_name = get_model_name() or "未设置"
        msg_count = stats["message_count"]
        img_count = stats["image_count"]
        tokens = stats["estimated_tokens"]

        return (
            f"📊 会话统计\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📝 消息记录: {msg_count}/{MAX_HISTORY_LENGTH}\n"
            f"🖼️ 图片数量: {img_count}\n"
            f"🎯 预估Token: ~{tokens}\n"
            f"🤖 当前模型: {model_name}"
        )

    # 未知指令
    return f"未知指令: {text_content}"


class MyClient(botpy.Client):
    """QQ机器人客户端"""

    async def on_ready(self):
        """机器人启动就绪"""
        _log.info(f"robot 「{self.robot.name}」 on_ready!")
        # 启动时自动获取模型名称
        await fetch_available_models()
        _log.info(f"已设置AI模型: {get_model_name()}")

    async def on_c2c_message_create(self, message: C2CMessage):
        """
        监听C2C消息（个人对个人）

        Args:
            message: C2C消息对象
        """
        # 使用用户openid作为会话ID，保持同一用户的对话历史
        session_id = f"c2c_{message.author.user_openid}"
        text_content = message.content or ""
        image_paths = []

        # 检查是否是指令（"/" 开头），指令不传递给大模型
        command_response = handle_command(text_content, session_id)
        if command_response is not None:
            await message.reply(content=command_response)
            return

        # 检查是否有图片附件
        if message.attachments and len(message.attachments) > 0:
            for attachment in message.attachments:
                save_path, error = await process_image_attachment(attachment)
                if save_path:
                    _log.info(f"[C2C] [Session:{session_id}] 图片下载成功: {save_path}")
                    image_paths.append(save_path)
                elif error:
                    _log.error(f"[C2C] [Session:{session_id}] 图片处理失败: {error}")

        # 调用AI处理消息
        ai_response = await process_message_with_ai(text_content, image_paths, session_id)

        if ai_response:
            # 回复AI的结果（纯内容）
            await message.reply(content=ai_response)
        else:
            # AI调用失败，返回默认消息
            await message.reply(content="抱歉，暂时无法处理您的消息。")

