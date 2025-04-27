import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.db.session import get_db
from backend.db.models import User
from backend.security.utils import get_password_hash

async def seed_test_user():
    async with get_db() as db:  # Ensure this matches your DB session setup
        query = select(User).where(User.username == "test_e2e_user")
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            test_user = User(
                username="test_e2e_user",
                hashed_password=get_password_hash("test_password"),
                is_active=True,
                is_superuser=False
            )
            db.add(test_user)
            await db.commit()
            print("✅ Test user created.")
        else:
            print("ℹ️ Test user already exists.")

if __name__ == "__main__":
    asyncio.run(seed_test_user())
