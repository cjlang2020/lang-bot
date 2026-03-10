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
    - tools_service.py: 工具服务
"""

import sys
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import botpy
from src.bot_client import MyClient
from src.session_manager import load_from_file, session_histories


if __name__ == "__main__":
    # 加载历史会话记录
    load_from_file()
    print(f"[启动] 已加载 {len(session_histories)} 个历史会话")

    # 从环境变量读取配置
    appid = os.getenv("QQ_BOT_APPID")
    secret = os.getenv("QQ_BOT_SECRET")

    if not appid or not secret:
        raise ValueError("请在.env文件中配置QQ_BOT_APPID和QQ_BOT_SECRET")

    # 监听所有事件（推荐用于测试）
    intents = botpy.Intents.all()

    client = MyClient(intents=intents)
    client.run(appid=appid, secret=secret)