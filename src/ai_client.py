"""
AI客户端模块 - 处理与AI API的交互
基于 finish_reason 的智能体循环机制
"""

import asyncio
import os
import re
import json
from typing import List, Dict, Callable, Awaitable, Optional, Any

import aiohttp
from botpy import logging

from src.config import (
    AI_API_BASE_URL,
    AI_MODEL_NAME,
    MAX_CONCURRENT_REQUESTS,
    MAX_STEPS,
    SYSTEM_PROMPT
)
from src.session_manager import (
    get_history_messages,
    get_last_images,
    set_last_images,
    update_last_ai_messages
)
from src.image_handler import encode_image_to_base64
from src.tools import TOOLS, process_tool_calls

_log = logging.get_logger()

# 并发控制信号量
request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

# 全局模型名称
current_model_name = AI_MODEL_NAME

# 全局模型上下文长度
current_model_context_length = 0

# 全局模型详细信息
current_model_info = {}


def parse_text_tool_call(text: str) -> List[Dict]:
    """
    解析文本格式的工具调用（Qwen 格式）
    支持格式: <function=name>\n<parameter=key>\nvalue\n</parameter>\n</function>

    Args:
        text: 包含工具调用的文本

    Returns:
        List[Dict]: 解析后的工具调用列表
    """
    tool_calls = []

    # 匹配 <function=name>...</function> 格式
    pattern = r'<function=([^>]+)>(.*?)</function>'
    matches = re.findall(pattern, text, re.DOTALL)

    for func_name, params_text in matches:
        func_name = func_name.strip()
        args = {}

        # 匹配 <parameter=key>\nvalue\n</parameter> 格式
        param_pattern = r'<parameter=([^>]+)>\s*(.*?)\s*</parameter>'
        param_matches = re.findall(param_pattern, params_text, re.DOTALL)

        for param_name, param_value in param_matches:
            param_name = param_name.strip()
            param_value = param_value.strip()
            args[param_name] = param_value

        tool_calls.append({
            "id": f"call_{len(tool_calls)}",
            "function": {
                "name": func_name,
                "arguments": json.dumps(args)
            }
        })

    return tool_calls


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

                    print("\n" + "="*80)
                    print("📋 模型API返回数据:")
                    print("="*80)
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    print("="*80 + "\n")

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


class AIResponse:
    """AI响应封装类"""
    def __init__(
        self,
        content: Optional[str] = None,
        finish_reason: str = "stop",
        tool_calls: Optional[List[Dict]] = None,
        error: Optional[str] = None
    ):
        self.content = content
        self.finish_reason = finish_reason
        self.tool_calls = tool_calls or []
        self.error = error

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0

    @property
    def is_done(self) -> bool:
        """判断是否应该结束循环"""
        return self.finish_reason in ["stop", "end_turn", "length"]


async def call_ai_api_single(
    messages: List[Dict],
    tools: Optional[List[Dict]] = None
) -> AIResponse:
    """
    单次调用AI API，返回结构化响应

    Args:
        messages: 消息列表
        tools: 工具定义列表

    Returns:
        AIResponse: 结构化的AI响应
    """
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{AI_API_BASE_URL}/chat/completions"

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

            # 只在非图片消息时启用工具
            if not has_image and tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            headers = {"Content-Type": "application/json"}

            _log.info(f"[AI API] 发送请求，消息数: {len(processed_messages)}")

            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()

                    if result.get("choices") and len(result["choices"]) > 0:
                        choice = result["choices"][0]
                        message = choice.get("message", {})
                        finish_reason = choice.get("finish_reason", "stop")

                        # 检查原生工具调用
                        tool_calls = message.get("tool_calls", [])

                        # 检查文本格式的工具调用
                        content = message.get("content", "")
                        if not tool_calls and content:
                            text_tool_calls = parse_text_tool_call(content)
                            if text_tool_calls:
                                tool_calls = text_tool_calls

                        return AIResponse(
                            content=content,
                            finish_reason=finish_reason,
                            tool_calls=tool_calls
                        )
                    else:
                        return AIResponse(error="API返回格式异常")
                else:
                    response_text = await response.text()
                    _log.error(f"AI API调用失败，状态码: {response.status}, 响应: {response_text}")
                    return AIResponse(error=f"API调用失败: {response.status}")

    except Exception as e:
        _log.error(f"AI API调用异常: {e}", exc_info=True)
        return AIResponse(error=str(e))


async def agent_loop(
    messages: List[Dict],
    send_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    save_history: bool = True
) -> Optional[str]:
    """
    基于finish_reason的智能体循环

    核心逻辑：
    - finish_reason == "tool_calls" → 执行工具 → 继续循环
    - finish_reason in ["stop", "end_turn"] → 退出循环

    Args:
        messages: 消息列表
        send_callback: 发送中间结果给用户的回调函数
        save_history: 是否保存历史记录

    Returns:
        str | None: 最终AI回复
    """
    step = 0
    final_messages = list(messages)  # 复制消息列表

    while step < MAX_STEPS:
        step += 1
        _log.info(f"[Agent Loop] 第 {step}/{MAX_STEPS} 步")

        # 调用AI
        response = await call_ai_api_single(final_messages, TOOLS)

        # 错误处理
        if response.error:
            _log.error(f"[Agent Loop] 错误: {response.error}")
            if send_callback:
                await send_callback(f"❌ 发生错误: {response.error}")
            return None

        # 情况1：工具调用 → 执行工具，继续循环
        if response.has_tool_calls:
            tool_names = [tc['function']['name'] for tc in response.tool_calls]
            _log.info(f"[Agent Loop] 工具调用: {tool_names}")

            # 推送工具调用信息给用户
            if send_callback:
                await send_callback(f"🔧 调用工具: {', '.join(tool_names)}")

            # 执行工具
            tool_results = await process_tool_calls(response.tool_calls)

            # 推送工具结果给用户（截取前200字符）
            if send_callback and tool_results:
                for i, result in enumerate(tool_results):
                    result_text = result.get("content", "")
                    preview = result_text[:200] + "..." if len(result_text) > 200 else result_text
                    tool_name = response.tool_calls[i]['function']['name'] if i < len(response.tool_calls) else "unknown"
                    await send_callback(f"📋 [{tool_name}] {preview}")

            # 添加助手消息（包含工具调用）
            assistant_msg = {
                "role": "assistant",
                "content": response.content
            }
            if response.tool_calls and response.tool_calls == response.tool_calls:
                # 原生工具调用格式
                assistant_msg["tool_calls"] = response.tool_calls
                assistant_msg["content"] = None

            final_messages.append(assistant_msg)

            # 添加工具结果
            final_messages.extend(tool_results)

            # 继续循环，让AI看到工具结果后决策
            continue

        # 情况2：任务完成 → 推送回复，退出循环
        if response.is_done:
            _log.info(f"[Agent Loop] finish_reason={response.finish_reason}，退出循环")

            if response.content:
                if send_callback:
                    await send_callback(response.content)

                if save_history:
                    # 保存最终消息（包含助手的最终回复）
                    saved_messages = final_messages + [{"role": "assistant", "content": response.content}]
                    update_last_ai_messages(saved_messages, current_model_name)

                return response.content
            else:
                return "抱歉，我无法处理这个请求。"

        # 情况3：其他finish_reason → 推送回复，退出循环
        _log.info(f"[Agent Loop] 未知finish_reason={response.finish_reason}，退出循环")

        if response.content:
            if send_callback:
                await send_callback(response.content)
            return response.content

        # 无内容，返回默认消息
        return "抱歉，我无法回答你的问题。"

    # 达到最大步数
    _log.warning(f"[Agent Loop] 达到最大步数 {MAX_STEPS}")
    if send_callback:
        await send_callback(f"⚠️ 已达到最大处理步数({MAX_STEPS})，任务可能未完全完成。")
    return "抱歉，处理过程超过了最大步数限制。"


async def process_message_with_ai(
    text_content: str,
    image_paths: Optional[List[str]] = None,
    send_callback: Optional[Callable[[str], Awaitable[None]]] = None
) -> Optional[str]:
    """
    处理消息并调用AI（基于finish_reason的智能体循环）

    Args:
        text_content: 文本内容
        image_paths: 图片路径列表
        send_callback: 发送中间结果给用户的回调函数

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

    # 执行智能体循环
    return await agent_loop(messages, send_callback, save_history=True)