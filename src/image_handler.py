"""
图片处理模块 - 处理图片下载、存储和编码
"""

import os
import base64
import uuid
from datetime import datetime

import aiohttp
from botpy import logging

_log = logging.get_logger()


def get_month_folder() -> str:
    """
    获取当前月份的文件夹路径，格式：YYYY-MM

    Returns:
        str: 月份文件夹的完整路径
    """
    current_date = datetime.now()
    year_month = current_date.strftime("%Y-%m")
    data_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    month_folder = os.path.join(data_folder, year_month)

    # 确保文件夹存在
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
    if not os.path.exists(month_folder):
        os.makedirs(month_folder)

    return month_folder


async def download_image(url: str, save_path: str) -> bool:
    """
    异步下载图片

    Args:
        url: 图片URL
        save_path: 保存路径

    Returns:
        bool: 下载是否成功
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(save_path, 'wb') as f:
                        f.write(content)
                    return True
                else:
                    _log.error(f"下载图片失败，状态码: {response.status}")
                    return False
    except Exception as e:
        _log.error(f"下载图片异常: {e}")
        return False


async def encode_image_to_base64(image_path: str) -> str | None:
    """
    将图片编码为Base64

    Args:
        image_path: 图片路径

    Returns:
        str | None: Base64编码字符串，失败返回None
    """
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string
    except Exception as e:
        _log.error(f"图片编码失败: {e}")
        return None


def generate_image_filename(original_filename: str | None = None) -> str:
    """
    生成唯一的图片文件名

    Args:
        original_filename: 原始文件名（用于获取扩展名）

    Returns:
        str: 新的文件名
    """
    file_ext = ".jpg"
    if original_filename:
        _, ext = os.path.splitext(original_filename)
        if ext:
            file_ext = ext
    return f"{uuid.uuid4()}{file_ext}"


async def process_image_attachment(attachment) -> tuple[str | None, str | None]:
    """
    处理图片附件：下载并保存

    Args:
        attachment: 消息附件对象

    Returns:
        tuple: (保存路径, 错误信息)
    """
    if not attachment.content_type or not attachment.content_type.startswith('image/'):
        return None, "不是图片类型"

    # 获取保存路径
    month_folder = get_month_folder()
    file_name = generate_image_filename(attachment.filename)
    save_path = os.path.join(month_folder, file_name)

    # 下载图片
    if await download_image(attachment.url, save_path):
        return save_path, None
    else:
        return None, f"下载失败: {attachment.url}"