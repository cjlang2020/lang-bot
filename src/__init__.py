"""
src模块初始化文件
"""

from src.config import (
    AI_API_BASE_URL,
    AI_MODEL_NAME,
    MAX_CONCURRENT_REQUESTS,
    MAX_STEPS,
    SYSTEM_PROMPT
)
from src.session_manager import (
    last_ai_messages,
    get_history_messages,
    get_last_images,
    set_last_images,
    update_last_ai_messages,
    clear_history,
    get_stats
)
from src.image_handler import (
    get_month_folder,
    download_image,
    encode_image_to_base64,
    generate_image_filename,
    process_image_attachment
)
from src.ai_client import (
    fetch_available_models,
    get_model_name,
    get_model_info,
    get_model_context_length,
    AIResponse,
    call_ai_api_single,
    agent_loop,
    process_message_with_ai
)
from src.bot_client import MyClient
from src.windows_tools import TOOLS, TOOL_FUNCTIONS, process_tool_calls

__all__ = [
    # config
    "AI_API_BASE_URL",
    "AI_MODEL_NAME",
    "MAX_CONCURRENT_REQUESTS",
    "MAX_STEPS",
    "SYSTEM_PROMPT",
    # session_manager
    "last_ai_messages",
    "get_history_messages",
    "get_last_images",
    "set_last_images",
    "update_last_ai_messages",
    "clear_history",
    "get_stats",
    # image_handler
    "get_month_folder",
    "download_image",
    "encode_image_to_base64",
    "generate_image_filename",
    "process_image_attachment",
    # ai_client
    "fetch_available_models",
    "get_model_name",
    "get_model_info",
    "get_model_context_length",
    "AIResponse",
    "call_ai_api_single",
    "agent_loop",
    "process_message_with_ai",
    # bot_client
    "MyClient",
    # windows_tools
    "TOOLS",
    "TOOL_FUNCTIONS",
    "process_tool_calls",
]