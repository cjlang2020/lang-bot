"""
QQ机器人主入口
通过QQ发送信息到本项目，项目接收后转发给支持OPENAI协议的第三方大模型

使用方法：
    python start_listener.py

模块说明：
    - src/config.py: 配置和常量
    - src/session_manager.py: 会话管理
    - src/image_handler.py: 图片处理
    - src/ai_client.py: AI API调用
    - src/bot_client.py: 机器人客户端
    - src/windows_tools.py: 工具服务
    - src/image_server.py: 图片HTTP服务
"""

import sys
import os
import threading
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import botpy
from src.bot_client import MyClient
from src.session_manager import last_ai_messages
from src.image_server import run_server


if __name__ == "__main__":
    # 显示历史消息状态
    msg_count = len(last_ai_messages.get("messages", []))
    print(f"[启动] 已加载历史消息: {msg_count} 条")

    # 在后台线程启动图片服务
    image_server_thread = threading.Thread(
        target=run_server,
        kwargs={"host": "127.0.0.1", "port": 9901},
        daemon=True
    )
    image_server_thread.start()
    print("[启动] 图片服务已启动: http://127.0.0.1:9901/images/{filename}")

    # 从环境变量读取配置
    appid = os.getenv("QQ_BOT_APPID")
    secret = os.getenv("QQ_BOT_SECRET")

    if not appid or not secret:
        raise ValueError("请在.env文件中配置QQ_BOT_APPID和QQ_BOT_SECRET")

    # 监听所有事件（推荐用于测试）
    intents = botpy.Intents.all()

    # 启动QQ机器人（主线程）
    client = MyClient(intents=intents)
    client.run(appid=appid, secret=secret)