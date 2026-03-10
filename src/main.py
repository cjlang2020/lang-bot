"""
QQ机器人主入口
通过QQ发送信息到本项目，项目接收后转发给支持OPENAI协议的第三方大模型
"""

import sys
import os

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import botpy
from src.bot_client import MyClient


if __name__ == "__main__":
    # 监听所有事件（推荐用于测试）
    intents = botpy.Intents.all()

    client = MyClient(intents=intents)
    client.run(appid="102870980", secret="dXRLFA50vqlgcYUQMIEB852zwtqomkig")