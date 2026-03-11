"""
图片服务模块 - FastAPI静态文件服务
提供本地图片的HTTP访问接口
"""

import os
from pathlib import Path
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.global_state import send_message_to_user_sync, get_user_openid, get_bot_api

# 图片存储目录
IMAGES_DIR = Path(__file__).parent.parent / "data" / "images"

# 创建FastAPI应用
app = FastAPI(
    title="图片服务",
    description="提供本地图片的HTTP访问接口",
    version="1.0.0"
)

# 添加CORS中间件，允许跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求体模型
class MessageRequest(BaseModel):
    """消息请求体"""
    content: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "这是一条测试消息"
            }
        }

@app.get("/images/{filename}")
async def get_image(filename: str):
    """
    获取图片文件
    
    Args:
        filename: 图片文件名（如 123.jpg）
    
    Returns:
        FileResponse: 图片文件响应
    
    Raises:
        HTTPException: 文件不存在时返回404
    """
    # 构建图片路径
    image_path = IMAGES_DIR / filename
    
    # 检查文件是否存在
    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"图片不存在: {filename}")
    
    # 检查是否为文件（防止目录遍历攻击）
    if not image_path.is_file():
        raise HTTPException(status_code=400, detail=f"无效的文件路径: {filename}")
    
    # 返回图片文件
    return FileResponse(
        path=str(image_path),
        media_type="image/jpeg",
        filename=filename
    )


@app.get("/")
async def root():
    """根路径 - 显示服务信息"""
    return {
        "service": "图片服务",
        "status": "running",
        "images_dir": str(IMAGES_DIR),
        "usage": "访问 /images/{filename} 获取图片"
    }


@app.get("/health")
async def health():
    """健康检查端点"""
    return {"status": "ok"}


@app.post("/msg")
async def send_message(request: MessageRequest):
    """
    发送消息给QQ用户
    
    需要用户先通过QQ发送一条消息给机器人，才能获取到openid
    
    Args:
        request: 消息请求体，包含content字段
    
    Returns:
        dict: 发送结果
    """
    # 检查Bot API是否已初始化
    if not get_bot_api():
        raise HTTPException(status_code=503, detail="Bot API未初始化，请等待机器人启动完成")
    
    # 检查用户OpenID是否已设置
    if not get_user_openid():
        raise HTTPException(
            status_code=503, 
            detail="用户OpenID未设置，请先通过QQ发送一条消息给机器人"
        )
    
    # 发送消息
    success, message = send_message_to_user_sync(request.content)
    
    if success:
        return {
            "success": True,
            "message": message,
            "content": request.content
        }
    else:
        raise HTTPException(status_code=500, detail=message)

def run_server(host: str = "127.0.0.1", port: int = 9901):
    """
    启动图片服务
    
    Args:
        host: 监听地址，默认127.0.0.1
        port: 监听端口，默认9901
    """
    # 确保图片目录存在
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"[图片服务] 启动中...")
    print(f"[图片服务] 图片目录: {IMAGES_DIR}")
    print(f"[图片服务] 访问地址: http://{host}:{port}/images/{{filename}}")
    
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    run_server()