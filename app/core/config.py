"""
配置层：全局设置与环境变量管理模块 (core/config.py)

【为什么需要这个文件？】
在企业级开发中，配置项（如数据库连接、端口、密钥等）不能硬编码在业务代码里。
使用 pydantic-settings 可以：
1. 集中管理所有配置项，提供类型提示与默认值。
2. 自动优先读取系统环境变量（或 Docker Compose 传入的环境变量）或 .env 文件中的值。
3. 如果环境变量不存在，则使用这里的默认值兜底。
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用全局配置类
    继承 BaseSettings，Pydantic 会自动读取同名环境变量并进行类型转换
    """

    # ==================== 项目基础信息 ====================
    PROJECT_NAME: str = "迷你任务备忘录 API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "一个基于 FastAPI + Docker + MySQL 的实战示例项目"

    # API 版本路由前缀（例如：/api/v1/tasks）
    API_V1_STR: str = "/api/v1"

    # ==================== 数据库配置 ====================
    # 优先从环境变量 DATABASE_URL 读取（docker-compose.yml 里已注入）
    # 格式：mysql+pymysql://用户名:密码@主机:端口/数据库名?参数
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://todo:todo@db:3306/todo?charset=utf8mb4",
    )

    # ==================== 安全与认证配置 ====================
    # 用于 JWT 令牌签名的密钥（生产环境中必须设置为高强度随机字符串）
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me-in-production")
    # JWT 访问令牌过期时间（分钟），这里默认 8 天
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    # ==================== 静态文件目录 ====================
    # 前端 HTML/CSS/JS 静态文件存放路径
    STATIC_DIR: str = "static"

    # Pydantic Settings 配置项
    model_config = SettingsConfigDict(
        env_file=".env",            # 支持从本地 .env 文件读取
        case_sensitive=True,        # 区分环境变量大小写
        extra="ignore",             # 忽略多余的未知环境变量
    )


# 实例化配置单例对象，其他模块直接导入 `settings` 使用即可
settings = Settings()
