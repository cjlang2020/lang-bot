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
    get_history_messages,
    get_last_images,
    set_last_images,
    update_last_ai_messages
)
from src.image_handler import encode_image_to_base64
from src.windows_tools import TOOLS, process_tool_calls

_log = logging.get_logger()

# 并发控制信号量
request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

# 全局模型名称
current_model_name = AI_MODEL_NAME

# 全局模型上下文长度
current_model_context_length = 0

# 全局模型详细信息
current_model_info = {}


async def fetch_available_models() -> str:
    """
    从API获取可用的模型列表，并返回第一个模型名称

    Returns:
        str: 模型名称
    """
    global current_model_name, current_model_context_length
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{AI_API_BASE_URL}/models"
            headers = {"Content-Type": "application/json"}

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()

                    # 打印API返回的原始数据
                    print("\n" + "="*80)
                    print("📋 模型API返回数据:")
                    print("="*80)
                    import json
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    print("="*80 + "\n")

                    # 尝试不同的数据结构
                    models = []
                    if "data" in result:
                        models = result["data"]
                    elif "models" in result:
                        models = result["models"]
                    elif isinstance(result, list):
                        models = result
                    else:
                        _log.warning(f"[模型获取] 无法识别的数据结构")

                    if models and len(models) > 0:
                        first_model = models[0]
                        if isinstance(first_model, dict):
                            model_id = first_model.get("id") or first_model.get("model") or first_model.get("name")

                            # 保存模型详细信息
                            meta = first_model.get("meta", {})
                            current_model_info["name"] = model_id
                            current_model_info["owned_by"] = first_model.get("owned_by", "未知")
                            current_model_info["n_ctx_train"] = meta.get("n_ctx_train", 0)
                            current_model_info["n_vocab"] = meta.get("n_vocab", 0)
                            current_model_info["n_embd"] = meta.get("n_embd", 0)
                            current_model_info["n_params"] = meta.get("n_params", 0)
                            current_model_info["size"] = meta.get("size", 0)
                            current_model_info["capabilities"] = first_model.get("capabilities", [])

                            current_model_context_length = current_model_info["n_ctx_train"] or 0
                        else:
                            model_id = str(first_model)

                        if model_id:
                            current_model_name = model_id
                            _log.info(f"[模型获取] 成功设置模型: {current_model_name}")
                            return current_model_name
                    else:
                        _log.error(f"[模型获取] API返回空模型列表")
                else:
                    _log.error(f"[模型获取] 获取模型列表失败，状态码: {response.status}")
    except Exception as e:
        _log.error(f"[模型获取] 获取模型列表异常: {e}", exc_info=True)

    current_model_name = "default-model"
    _log.warning(f"[模型获取] 使用默认模型: {current_model_name}")
    return current_model_name


def get_model_name() -> str:
    return current_model_name


def get_model_context_length() -> int:
    return current_model_context_length


def get_model_info() -> dict:
    return current_model_info


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
                if isinstance(content, list):
                    for item in content:
                        item_type = item.get("type", "")
                        if item_type == "text":
                            print(f"📝 [文本]: {item.get('text', '')}")
                        elif item_type == "image_url":
                            print(f"🖼️  [图片]: 已添加Base64编码的图片")
                else:
                    print(f"📝 [文本]: {content}")
            print("="*80 + "\n")

            # 处理多模态消息
            processed_messages = []
            for msg in messages:
                if msg["role"] == "user" and "图片路径：" in msg.get("content", ""):
                    content_text = msg["content"]
                    image_paths = re.findall(r'- (.*\.png|.*\.jpg|.*\.jpeg)', content_text)

                    multimodal_content = [{"type": "text", "text": content_text}]

                    for img_path in image_paths:
                        if os.path.exists(img_path):
                            encoded_image = await encode_image_to_base64(img_path)
                            if encoded_image:
                                multimodal_content.append({
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}
                                })
                                _log.info(f"图片已添加到消息: {os.path.basename(img_path)}")

                    processed_messages.append({"role": "user", "content": multimodal_content})
                else:
                    processed_messages.append(msg)

            has_image = any(
                msg.get("role") == "user" and "图片路径：" in msg.get("content", "")
                for msg in messages
            )

            payload = {
                "model": current_model_name,
                "messages": processed_messages,
                "temperature": 0.7,
                "max_tokens": 128000
            }

            if not has_image:
                payload["tools"] = TOOLS
                payload["tool_choice"] = "auto"

            headers = {"Content-Type": "application/json"}
            _log.info(f"[AI API] 准备发送请求，消息数: {len(processed_messages)}")

            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("choices") and len(result["choices"]) > 0:
                        choice = result["choices"][0]

                        if "message" in choice:
                            message = choice["message"]

                            # 处理工具调用
                            if "tool_calls" in message and message["tool_calls"]:
                                print("\n" + "="*80)
                                print("🔧 AI 请求调用工具:")
                                print("="*80)
                                for tc in message["tool_calls"]:
                                    print(f"  - {tc['function']['name']}")

                                tool_results = await process_tool_calls(message["tool_calls"])
                                _log.info(f"[工具调用] 返回结果数: {len(tool_results)}")

                                tool_call_msg = {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": message["tool_calls"]
                                }
                                final_messages = processed_messages + [tool_call_msg] + tool_results

                                print("\n" + "="*80)
                                print("🔄 再次调用AI，传入工具结果...")
                                print("="*80 + "\n")

                                final_payload = {
                                    "model": current_model_name,
                                    "messages": final_messages,
                                    "temperature": 0.7,
                                    "max_tokens": 2048
                                }

                                async with session.post(url, json=final_payload, headers=headers) as final_response:
                                    if final_response.status == 200:
                                        final_result = await final_response.json()
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
                                                    # 保存时包含 AI 的回复
                                                    saved_messages = final_messages + [{"role": "assistant", "content": ai_reply}]
                                                    update_last_ai_messages(saved_messages, current_model_name)
                                                    return ai_reply
                                                else:
                                                    return "抱歉，我无法处理这个请求。"
                                        else:
                                            return "抱歉，处理请求时出现问题。"
                                    else:
                                        return "抱歉，服务暂时不可用。"

                            # 普通回复
                            elif "content" in message and message["content"]:
                                ai_reply = message["content"]
                                print("\n" + "="*80)
                                print("🤖 AI 回复:")
                                print("="*80)
                                print(ai_reply)
                                print("="*80 + "\n")
                                # 保存时包含 AI 的回复
                                saved_messages = processed_messages + [{"role": "assistant", "content": ai_reply}]
                                update_last_ai_messages(saved_messages, current_model_name)
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
    async with request_semaphore:
        return await call_ai_api(messages)


async def process_message_with_ai(
    text_content: str,
    image_paths: List[str] | None = None
) -> str | None:
    """
    处理消息并调用AI（支持多模态和工具调用）

    Args:
        text_content: 文本内容
        image_paths: 图片路径列表

    Returns:
        str | None: AI回复内容
    """
    # 构建消息：系统提示词 + 历史对话 + 当前消息
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 加载历史对话
    history = get_history_messages()
    messages.extend(history)

    # 检查用户是否提到了图片相关的内容
    image_keywords = ["图片", "刚才的图", "刚才发的图", "之前的图", "上面的图", "那张图", "这张图",
                      "图片内容", "图片里", "图片上", "提取图片", "识别图片", "看图片", "图片的文字"]

    # 判断是否需要附带历史图片
    need_history_image = False
    if not image_paths:
        if any(keyword in text_content for keyword in image_keywords):
            last_images = get_last_images()
            if last_images:
                image_paths = last_images
                need_history_image = True
                _log.info(f"用户提到图片，附带历史图片: {last_images}")

    # 保存新的图片路径
    if image_paths and not need_history_image:
        set_last_images(image_paths)

    # 构建用户消息
    if image_paths:
        user_message = f"{text_content}\n\n图片路径：\n"
        for path in image_paths:
            user_message += f"- {path}\n"
    else:
        user_message = text_content

    messages.append({"role": "user", "content": user_message})
    _log.info(f"[给AI的消息] {user_message[:200]}...")

    # 调用AI API
    return await call_ai_api_with_semaphore(messages)