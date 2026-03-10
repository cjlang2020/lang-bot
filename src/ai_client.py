"""
AI客户端模块 - 处理与AI API的交互
"""

import asyncio
import os
import re
from typing import List, Dict

import aiohttp
from botpy import logging

from src.config import (
    AI_API_BASE_URL,
    AI_MODEL_NAME,
    MAX_CONCURRENT_REQUESTS,
    SYSTEM_PROMPT
)
from src.session_manager import (
    get_session,
    add_to_session,
    session_exists,
    maybe_cleanup,
    get_last_images,
    set_last_images
)
from src.image_handler import encode_image_to_base64
from src.windows_tools import TOOLS, process_tool_calls

_log = logging.get_logger()

# 并发控制信号量
request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

# 全局模型名称
current_model_name = AI_MODEL_NAME


async def fetch_available_models() -> str:
    """
    从API获取可用的模型列表，并返回第一个模型名称

    Returns:
        str: 模型名称
    """
    global current_model_name
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{AI_API_BASE_URL}/models"
            headers = {"Content-Type": "application/json"}

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    _log.info(f"[模型获取] API返回: {result}")

                    # 尝试不同的数据结构
                    models = []
                    if "data" in result:
                        models = result["data"]
                    elif "models" in result:
                        models = result["models"]
                    elif isinstance(result, list):
                        models = result
                    else:
                        _log.warning(f"[模型获取] 无法识别的数据结构: {result.keys() if isinstance(result, dict) else '非字典类型'}")

                    if models and len(models) > 0:
                        # 提取第一个模型的id或name
                        first_model = models[0]
                        if isinstance(first_model, dict):
                            model_id = first_model.get("id") or first_model.get("model") or first_model.get("name")
                        else:
                            model_id = str(first_model)

                        if model_id:
                            current_model_name = model_id
                            _log.info(f"[模型获取] 成功设置模型: {current_model_name}")
                            return current_model_name
                        else:
                            _log.error(f"[模型获取] 第一个模型缺少id/name: {first_model}")
                    else:
                        _log.error(f"[模型获取] API返回空模型列表: {result}")
                else:
                    _log.error(f"[模型获取] 获取模型列表失败，状态码: {response.status}")
    except Exception as e:
        _log.error(f"[模型获取] 获取模型列表异常: {e}", exc_info=True)

    # 失败时使用默认模型名
    current_model_name = "default-model"
    _log.warning(f"[模型获取] 使用默认模型: {current_model_name}")
    return current_model_name


def get_model_name() -> str:
    """
    获取当前模型名称

    Returns:
        str: 当前模型名称
    """
    return current_model_name


async def call_ai_api(messages: List[Dict]) -> str | None:
    """
    调用第三方AI应用API（支持多模态和工具调用）

    Args:
        messages: 消息列表

    Returns:
        str | None: AI回复内容，失败返回None
    """
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{AI_API_BASE_URL}/chat/completions"

            # 打印发送给AI的所有消息
            print("\n" + "="*80)
            print("📦 准备发送给AI的完整消息:")
            print("="*80)
            for idx, msg in enumerate(messages, 1):
                role = msg.get("role", "")
                content = msg.get("content", "")
                print(f"\n[{idx}] 角色: {role.upper()}")
                print("-" * 80)
                if isinstance(content, list):  # 多模态消息
                    for item in content:
                        item_type = item.get("type", "")
                        if item_type == "text":
                            print(f"📝 [文本]: {item.get('text', '')}")
                        elif item_type == "image_url":
                            print(f"🖼️  [图片]: 已添加Base64编码的图片")
                else:  # 普通文本消息
                    print(f"📝 [文本]: {content}")
            print("="*80 + "\n")

            # 处理多模态消息：将包含图片路径的消息转换为多模态格式
            processed_messages = []
            for msg in messages:
                if msg["role"] == "user" and "图片路径：" in msg.get("content", ""):
                    # 提取图片路径
                    content_text = msg["content"]
                    image_paths = re.findall(r'- (.*\.png|.*\.jpg|.*\.jpeg)', content_text)

                    # 构建多模态消息
                    multimodal_content = [
                        {"type": "text", "text": content_text}
                    ]

                    # 添加图片的Base64编码
                    for img_path in image_paths:
                        if os.path.exists(img_path):
                            encoded_image = await encode_image_to_base64(img_path)
                            if encoded_image:
                                multimodal_content.append({
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{encoded_image}"
                                    }
                                })
                                _log.info(f"图片已添加到消息: {os.path.basename(img_path)}")

                    processed_messages.append({
                        "role": "user",
                        "content": multimodal_content
                    })
                else:
                    processed_messages.append(msg)

            payload = {
                "model": current_model_name,
                "messages": processed_messages,
                "temperature": 0.7,
                "max_tokens": 128000,
                "tools": TOOLS,  # 添加工具定义
                "tool_choice": "auto"  # 自动选择是否使用工具
            }
            headers = {
                "Content-Type": "application/json"
            }

            _log.info(f"[AI API] 准备发送请求，消息数: {len(processed_messages)}")

            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    # 打印AI回复
                    if result.get("choices") and len(result["choices"]) > 0:
                        choice = result["choices"][0]

                        # 检查是否有工具调用
                        if "message" in choice:
                            message = choice["message"]

                            # 处理工具调用
                            if "tool_calls" in message and message["tool_calls"]:
                                print("\n" + "="*80)
                                print("🔧 AI 请求调用工具:")
                                print("="*80)
                                for tc in message["tool_calls"]:
                                    print(f"  - {tc['function']['name']}")

                                # 处理工具调用
                                tool_results = await process_tool_calls(message["tool_calls"])
                                _log.info(f"[工具调用] 返回结果数: {len(tool_results)}")

                                # 添加AI的工具调用消息
                                tool_call_msg = {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": message["tool_calls"]
                                }
                                # 构建最终消息：使用已处理的消息（包含图片）+ 工具调用消息 + 工具结果
                                final_messages = processed_messages + [tool_call_msg] + tool_results

                                print("\n" + "="*80)
                                print("🔄 再次调用AI，传入工具结果...")
                                print("="*80 + "\n")

                                # 再次调用API（不传tools，让AI直接回答）
                                final_payload = {
                                    "model": current_model_name,
                                    "messages": final_messages,
                                    "temperature": 0.7,
                                    "max_tokens": 2048
                                }

                                async with session.post(url, json=final_payload, headers=headers) as final_response:
                                    if final_response.status == 200:
                                        final_result = await final_response.json()
                                        _log.info(f"[AI API] 第二次响应: {final_result}")
                                        if final_result.get("choices") and len(final_result["choices"]) > 0:
                                            final_choice = final_result["choices"][0]
                                            if "message" in final_choice:
                                                ai_reply = final_choice["message"].get("content", "")
                                                if ai_reply:
                                                    print("\n" + "="*80)
                                                    print("🤖 AI 最终回复:")
                                                    print("="*80)
                                                    print(ai_reply)
                                                    print("="*80 + "\n")
                                                    return ai_reply
                                                else:
                                                    _log.error(f"[AI API] 第二次返回空内容")
                                                    return "抱歉，我无法处理这个请求。"
                                        else:
                                            _log.error(f"[AI API] 第二次返回格式异常: {final_result}")
                                            return "抱歉，处理请求时出现问题。"
                                    else:
                                        response_text = await final_response.text()
                                        _log.error(f"AI API第二次调用失败，状态码: {final_response.status}, 响应: {response_text}")
                                        return "抱歉，服务暂时不可用。"

                            # 普通回复
                            elif "content" in message and message["content"]:
                                ai_reply = message["content"]
                                print("\n" + "="*80)
                                print("🤖 AI 回复:")
                                print("="*80)
                                print(ai_reply)
                                print("="*80 + "\n")
                                return ai_reply

                        _log.error(f"AI API返回格式异常: {result}")
                        return None
                    else:
                        _log.error(f"AI API返回格式异常: {result}")
                        return None
                else:
                    response_text = await response.text()
                    _log.error(f"AI API调用失败，状态码: {response.status}, 响应: {response_text}")
                    return None
    except Exception as e:
        _log.error(f"AI API调用异常: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return None


async def call_ai_api_with_semaphore(messages: List[Dict]) -> str | None:
    """
    带并发控制的AI API调用

    Args:
        messages: 消息列表

    Returns:
        str | None: AI回复内容
    """
    async with request_semaphore:
        return await call_ai_api(messages)


async def process_message_with_ai(
    text_content: str,
    image_paths: List[str] | None = None,
    session_id: str | None = None
) -> str | None:
    """
    处理消息并调用AI（支持多模态和工具调用）

    Args:
        text_content: 文本内容
        image_paths: 图片路径列表
        session_id: 会话ID

    Returns:
        str | None: AI回复内容
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 可能清理过期会话
    maybe_cleanup()

    # 添加历史对话
    if session_id and session_exists(session_id):
        messages.extend(get_session(session_id))
    else:
        _log.info(f"[Session:{session_id}] 创建新的会话")

    # 检查用户是否提到了图片相关的内容
    image_keywords = ["图片", "刚才的图", "刚才发的图", "之前的图", "上面的图", "那张图", "这张图",
                      "图片内容", "图片里", "图片上", "提取图片", "识别图片", "看图片", "图片的文字"]

    # 判断是否需要附带历史图片
    need_history_image = False
    if not image_paths and session_id:
        # 当前消息没有图片，但用户提到了图片相关内容
        if any(keyword in text_content for keyword in image_keywords):
            last_images = get_last_images(session_id)
            if last_images:
                image_paths = last_images
                need_history_image = True
                _log.info(f"[Session:{session_id}] 用户提到图片，附带历史图片: {last_images}")

    # 保存新的图片路径
    if image_paths and not need_history_image and session_id:
        set_last_images(session_id, image_paths)

    # 构建用户消息
    if image_paths:
        # 构建包含图片路径的用户消息
        user_message = f"{text_content}\n\n图片路径：\n"
        for path in image_paths:
            user_message += f"- {path}\n"
    else:
        user_message = text_content

    messages.append({"role": "user", "content": user_message})
    _log.info(f"[给AI的消息:{user_message[:200]}...]")

    # 调用AI API
    ai_response = await call_ai_api_with_semaphore(messages)

    # 保存历史对话
    if session_id and ai_response:
        add_to_session(session_id, "user", text_content, image_paths)
        add_to_session(session_id, "assistant", ai_response)

    return ai_response