"""
机器人客户端模块 - 处理QQ消息的接收和回复
"""

import botpy
from botpy import logging
from botpy.message import GroupMessage, C2CMessage
from botpy.types.message import Reference

from src.ai_client import process_message_with_ai, fetch_available_models, get_model_name
from src.image_handler import process_image_attachment, get_month_folder
from src.config import AI_MODEL_NAME

_log = logging.get_logger()


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

    async def on_group_at_message_create(self, message: GroupMessage):
        """
        监听群@消息（整个群组共享会话历史）

        Args:
            message: 群消息对象
        """
        # 使用群组ID作为会话ID，整个群组共享同一个对话历史
        session_id = f"group_{message.group_openid}"
        # 创建引用对象，引用用户的消息
        message_reference = Reference(message_id=message.id)

        # 在用户消息前添加用户名，让AI知道是谁在说话
        user_display_name = message.author.member_openid[-4:] if message.author.member_openid else "用户"
        text_content = f"[{user_display_name}] {message.content}" if message.content else ""

        image_paths = []

        # 检查是否有图片附件
        if message.attachments and len(message.attachments) > 0:
            for attachment in message.attachments:
                save_path, error = await process_image_attachment(attachment)
                if save_path:
                    _log.info(f"[群聊] [Session:{session_id}] [{user_display_name}] 图片下载成功: {save_path}")
                    image_paths.append(save_path)
                elif error:
                    _log.error(f"[群聊] [Session:{session_id}] [{user_display_name}] 图片处理失败: {error}")

        # 调用AI处理消息
        ai_response = await process_message_with_ai(text_content, image_paths, session_id)

        if ai_response:
            # 回复AI的结果（纯内容）
            await message.reply(
                content=ai_response,
                message_reference=message_reference
            )
        else:
            # AI调用失败
            await message.reply(
                content="抱歉，暂时无法处理您的消息。",
                message_reference=message_reference
            )