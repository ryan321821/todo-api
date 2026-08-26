"""
作用：  从同级目录下的 category.py 和 task.py 文件中，导入定义好的 Category 和 Task 数据模型类。
好处：  以后在其他文件（如 main.py 或 API 路由）中需要用到模型时，不需要写繁琐的 
        from app.models.category import Category，直接写 from app.models import Category, 
        Task 即可。
"""


from .task import Task
from .category import Category

"""
作用：  显式定义这个包允许对外部导出的内容。
好处：  当别人在其他文件使用通配符导入（例如 from app.models import *）时，
        Python 只会导入 __all__ 列表里声明的 Task 和 Category，防止内部的临时变量或无关模块被污染导入。
"""
__all__ = ["Task", "Category"]
