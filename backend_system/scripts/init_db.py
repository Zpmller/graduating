"""
数据库初始化脚本：创建默认管理员用户
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal, engine
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from sqlalchemy import select


async def init_db():
    """初始化数据库"""
    try:
        async with AsyncSessionLocal() as db:
            # 检查是否已存在管理员用户
            result = await db.execute(
                select(User).where(User.username == "admin")
            )
            admin_user = result.scalar_one_or_none()
            
            if admin_user:
                print("管理员用户已存在，跳过创建")
                return
            
            # 创建默认管理员用户
            admin_password = input("请输入管理员密码（默认: admin123）: ").strip() or "admin123"
            
            admin_user = User(
                username="admin",
                hashed_password=get_password_hash(admin_password),
                full_name="系统管理员",
                role=UserRole.ADMIN,
                is_active=True
            )
            
            db.add(admin_user)
            await db.commit()
            
            print(f"✓ 管理员用户创建成功")
            print(f"  用户名: admin")
            print(f"  密码: {admin_password}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
