# 基础镜像：带 Python 3.12 的轻量 Linux
FROM python:3.12-slim

# 容器内工作目录
WORKDIR /app

# 关闭字节码缓存、输出不缓冲（日志实时可见）
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# 先复制依赖清单并安装 —— 利用 Docker 层缓存，改代码不用重新装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app ./app
COPY static ./static

# 声明容器监听端口（仅是文档性声明）
EXPOSE 8000

# 容器启动命令：Uvicorn 监听 0.0.0.0，供容器外访问
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]