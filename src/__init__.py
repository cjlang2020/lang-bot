"""
src模块初始化文件
"""

from src.config import (
    AI_API_BASE_URL,
    AI_MODEL_NAME,
    MAX_CONCURRENT_REQUESTS,
    SESSION_EXPIRE_TIME,
    MAX_HISTORY_LENGTH,
    SYSTEM_PROMPT
)
from src.session_manager import (
    session_histories,
    get_session,
    add_to_session,
    session_exists,
    cleanup_expired_sessions,
    maybe_cleanup
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
    call_ai_api,
    call_ai_api_with_semaphore,
    process_message_with_ai
)
from src.bot_client import MyClient
from src.windows_tools import TOOLS, TOOL_FUNCTIONS, process_tool_calls

__all__ = [
    # config
    "AI_API_BASE_URL",
    "AI_MODEL_NAME",
    "MAX_CONCURRENT_REQUESTS",
    "SESSION_EXPIRE_TIME",
    "MAX_HISTORY_LENGTH",
    "SYSTEM_PROMPT",
    # session_manager
    "session_histories",
    "get_session",
    "add_to_session",
    "session_exists",
    "cleanup_expired_sessions",
    "maybe_cleanup",
    # image_handler
    "get_month_folder",
    "download_image",
    "encode_image_to_base64",
    "generate_image_filename",
    "process_image_attachment",
    # ai_client
    "fetch_available_models",
    "get_model_name",
    "call_ai_api",
    "call_ai_api_with_semaphore",
    "process_message_with_ai",
    # bot_client
    "MyClient",
    # windows_tools
    "TOOLS",
    "TOOL_FUNCTIONS",
    "process_tool_calls",
]