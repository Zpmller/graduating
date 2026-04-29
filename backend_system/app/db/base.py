"""
数据库基础模块：SQLAlchemy Base和元数据
"""
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData

# 创建Base类
Base = declarative_base()

# 元数据
metadata = MetaData()
