"""
数据库层：SQLAlchemy ORM 声明基类定义 (db/base_class.py)

【为什么需要这个文件？】
在 SQLAlchemy 中，所有数据表模型（如 Task、User 等）都需要继承同一个 Base 基类。
将其独立放置在 base_class.py 中，可以避免 models 层与 db 层的循环导入问题。
"""

from sqlalchemy.orm import declarative_base

# 创建 ORM 模型的公共基类
# 所有的数据表类（如 models/task.py 中的 Task）都必须继承此 Base
Base = declarative_base()
"""
declarative_base：在 SQLAlchemy 中，declarative_base() 表示采用 “声明式映射” 方式。这意味着你不需要手动写复杂
    的 Table 定义来映射数据库，而是通过定义一个普通的 Python 类（class），并在类里面声明 __tablename__ 和字段（Column），
    SQLAlchemy 就会自动帮你生成对应的数据库表结构。这叫“声明”，意思是你“声明”我要什么，底层框架自动去实现。

Base.metadata是 declarative_base() 的一个属性（Attribute）
metadata：metadata 是 SQLAlchemy 中的一个对象，它包含了数据库的元数据，如数据库连接信息、表信息、列信息等。

"""

