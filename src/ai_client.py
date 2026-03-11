"""
AI客户端模块 - 处理与AI API的交互
支持循环调用大模型直到获得有效结果
"""

import asyncio
import os
import re
import json
from typing import List, Dict, Callable, Awaitable

import aiohttp
from botpy import logging

from src.config import (
    AI_API_BASE_URL,
    AI_MODEL_NAME,
    MAX_CONCURRENT_REQUESTS,
    MAX_LOOP_COUNT,
    SYSTEM_PROMPT,
    EVALUATION_PROMPT
)
from src.session_manager import (
    get_history_messages,
    get_last_images,
    set_last_images,
    update_last_ai_messages
)
from src.image_handler import encode_image_to_base64
from src.tools import TOOLS, TOOL_FUNCTIONS, process_tool_calls

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
                    import json
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


async def evaluate_response(question: str, answer: str) -> bool:
    """
    评估大模型回复是否有效

    Args:
        question: 用户原始问题
        answer: 大模型回复

    Returns:
        bool: True=有结果，False=无结果
    """
    try:
        question_stripped = question.strip().lower()
        answer_stripped = answer.strip()

        # 简单问候列表
        simple_greetings = [
            "你好", "您好", "嗨", "hi", "hello", "在吗", "在不在",
            "早上好", "下午好", "晚上好", "早", "晚安",
            "怎么样", "最近好吗", "吃了吗", "干嘛呢"
        ]

        # 简单告别列表
        simple_goodbyes = [
            "拜拜", "再见", "晚安", "走了", "溜了"
        ]

        # 判断是否为简单问候
        is_greeting = any(
            question_stripped.startswith(g.lower()) and len(question_stripped) <= len(g) + 2
            for g in simple_greetings
        )

        # 判断是否为简单告别
        is_goodbye = any(
            question_stripped.startswith(g.lower()) and len(question_stripped) <= len(g) + 2
            for g in simple_goodbyes
        )

        if is_greeting or is_goodbye:
            _log.info(f"[评估] 简单问候/告别，直接返回有效")
            return True

        # 具体问题的判断指标
        specific_question_indicators = [
            "什么", "怎么", "如何", "为什么", "哪", "几", "多少", "为啥",
            "查找", "搜索", "找", "读取", "查看", "打开", "执行", "运行",
            "帮我", "能否", "可以", "有没有", "是不是", "告诉我",
            "文件", "目录", "系统", "进程", "网络", "命令", "代码",
            "路径", "位置", "在哪里", "列出", "显示", "看看"
        ]

        # 判断是否是具体问题
        is_specific_question = any(
            indicator in question_stripped
            for indicator in specific_question_indicators
        )

        # 如果不是具体问题，直接返回有效（例如感谢、确认等）
        if not is_specific_question:
            _log.info(f"[评估] 非具体问题，直接返回有效")
            return True

        # 对于具体问题，需要更严格的判断
        if is_specific_question:
            # 回答太短（小于15字符），认为无效
            if len(answer_stripped) < 15:
                _log.info(f"[评估] 具体问题回答太短({len(answer_stripped)}字符)，无结果")
                return False

            # 无效回答短语列表
            pure_failure_phrases = [
                "我不知道", "我无法回答", "我无法处理这个请求",
                "抱歉，我无法", "对不起，我不能", "我没有能力",
                "我不会", "我不能", "这个我做不到"
            ]

            for phrase in pure_failure_phrases:
                if phrase in answer:
                    _log.info(f"[评估] 包含无效短语'{phrase}'，无结果")
                    return False

            # 列出类问题的特殊判断
            list_questions = ["列出", "显示", "看看", "list", "dir", "ls"]
            if any(q in question_stripped for q in list_questions):
                # 列出目录操作返回空目录也算有效
                if "目录为空" in answer or "没有找到" in answer:
                    return True

            # 搜索类问题的特殊判断
            search_questions = ["搜索", "查找", "找", "search", "find"]
            if any(q in question_stripped for q in search_questions):
                # 没找到文件也是有效回答
                if "未找到" in answer or "不存在" in answer:
                    return True

        _log.info(f"[评估] 回答有效，长度: {len(answer)}字符")
        return True

    except Exception as e:
        _log.error(f"[评估] 异常: {e}")
        return True  # 异常时默认有结果，避免无限循环


async def call_ai_api(messages: List[Dict], save_history: bool = True, status_callback: Callable[[str], Awaitable[None]] | None = None) -> str | None:
    """
    调用第三方AI应用API（支持多模态和工具调用）

    Args:
        messages: 消息列表
        save_history: 是否保存到历史记录
        status_callback: 状态通知回调函数（发送给用户）

    Returns:
        str | None: AI回复内容，失败返回None
    """
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{AI_API_BASE_URL}/chat/completions"

            # 注意：不再发送"正在思考..."，避免消息去重
            # 直接等待AI响应后发送结果

            print("\n" + "="*60)
            print("📦 发送给AI的消息:")
            print("="*60)
            for idx, msg in enumerate(messages, 1):
                role = msg.get("role", "")
                content = msg.get("content", "")
                print(f"[{idx}] {role.upper()}: ", end="")
                if isinstance(content, list):
                    for item in content:
                        if item.get("type") == "text":
                            print(item.get('text', '')[:100])
                            break
                    else:
                        print("[多模态内容]")
                else:
                    print(str(content)[:100])
            print("="*60 + "\n")

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
                                tool_names = [tc['function']['name'] for tc in message["tool_calls"]]
                                _log.info(f"[工具调用] {tool_names}")

                                # 工具调用过程不发送给用户，直接执行
                                tool_results = await process_tool_calls(message["tool_calls"])
                                _log.info(f"[工具调用] 返回结果数: {len(tool_results)}")

                                tool_call_msg = {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": message["tool_calls"]
                                }
                                final_messages = processed_messages + [tool_call_msg] + tool_results

                                _log.info("🔄 再次调用AI，传入工具结果...")

                                # 再次调用大模型，传入工具结果，这次的回复会发送给用户
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
                                                    _log.info(f"🤖 AI最终回复: {ai_reply[:100]}{'...' if len(ai_reply) > 100 else ''}")
                                                    if save_history:
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

                                # 检查是否包含文本格式的工具调用
                                text_tool_calls = parse_text_tool_call(ai_reply)

                                if text_tool_calls:
                                    tool_names = [tc['function']['name'] for tc in text_tool_calls]
                                    _log.info(f"[工具调用（文本格式）] {tool_names}")

                                    # 工具调用过程不发送给用户，直接执行
                                    tool_results = await process_tool_calls(text_tool_calls)
                                    _log.info(f"[工具调用] 返回结果数: {len(tool_results)}")

                                    # 构建工具调用消息
                                    tool_call_msg = {
                                        "role": "assistant",
                                        "content": ai_reply,
                                        "tool_calls": text_tool_calls
                                    }
                                    final_messages = processed_messages + [tool_call_msg] + tool_results

                                    _log.info("🔄 再次调用AI，传入工具结果...")

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
                                                    final_reply = final_choice["message"].get("content", "")
                                                    if final_reply:
                                                        _log.info(f"🤖 AI最终回复: {final_reply[:100]}{'...' if len(final_reply) > 100 else ''}")
                                                        if save_history:
                                                            saved_messages = final_messages + [{"role": "assistant", "content": final_reply}]
                                                            update_last_ai_messages(saved_messages, current_model_name)
                                                        return final_reply
                                                    else:
                                                        return "抱歉，我无法处理这个请求。"
                                            else:
                                                return "抱歉，处理请求时出现问题。"
                                        else:
                                            return "抱歉，服务暂时不可用。"
                                else:
                                    # 普通文本回复
                                    _log.info(f"🤖 AI回复: {ai_reply[:100]}{'...' if len(ai_reply) > 100 else ''}")
                                    if save_history:
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


async def call_ai_api_with_semaphore(messages: List[Dict], save_history: bool = True, status_callback: Callable[[str], Awaitable[None]] | None = None) -> str | None:
    async with request_semaphore:
        return await call_ai_api(messages, save_history, status_callback)


async def process_message_with_ai(
    text_content: str,
    image_paths: List[str] | None = None,
    send_callback: Callable[[str], Awaitable[None]] | None = None
) -> str | None:
    """
    处理消息并调用AI（支持多模态、工具调用和循环评估）

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

    # 保存原始用户问题（用于评估）
    original_question = text_content

    # 循环调用大模型
    loop_count = 0
    last_reply = None

    while loop_count < MAX_LOOP_COUNT:
        loop_count += 1
        _log.info(f"[循环] 第 {loop_count}/{MAX_LOOP_COUNT} 次调用")

        ai_reply = await call_ai_api_with_semaphore(messages, True, send_callback)

        if ai_reply is None:
            _log.warning(f"[循环] 第 {loop_count} 次调用返回空结果，继续循环")
            # 构建重试消息
            messages.append({"role": "assistant", "content": "（调用失败，正在重试...）"})
            messages.append({"role": "user", "content": "请重新尝试回答我的问题。"})
            continue

        last_reply = ai_reply

        # 发送大模型回复给用户
        if send_callback:
            try:
                # 直接发送回复，不添加额外前缀
                await send_callback(ai_reply)
            except Exception as e:
                _log.warning(f"[状态通知] 发送失败: {e}")

        # 评估回复是否有效
        has_result = await evaluate_response(original_question, ai_reply)

        if has_result:
            _log.info(f"[循环] 第 {loop_count} 次评估：有结果，结束循环")
            return ai_reply
        else:
            _log.info(f"[循环] 第 {loop_count} 次评估：无结果，继续循环")

            simulated_question = "请提供更详细的回答。"

            messages.append({"role": "assistant", "content": ai_reply})
            messages.append({"role": "user", "content": simulated_question})

    # 达到最大循环次数，返回最后一次结果
    _log.info(f"[循环] 达到最大次数 {MAX_LOOP_COUNT}，返回最后结果")
    return last_reply or "抱歉，我无法回答你的问题。"