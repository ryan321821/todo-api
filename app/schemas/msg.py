"""
数据传输层：通用消息响应 Schema (schemas/msg.py)

【为什么需要这个文件？】
定义通用的操作结果提示响应格式（例如：删除成功、操作提示）。
在企业级架构中，通用的 DTO 模型从具体业务中剥离出来，方便各模块共用。
"""

from typing import Optional
from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """
    通用操作消息响应模型
    常用于 DELETE 或无实体返回的接口响应
    """

    message: str = Field(
        ..., description="操作结果说明信息", examples=["任务 ID 1 已删除"]
    )
    id: Optional[int] = Field(None, description="被操作的相关资源 ID", examples=[1])
