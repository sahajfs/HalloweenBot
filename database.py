import aiosqlite

class Database:
    def __init__(self, db_path: str = 'points.db'):
        self.db_path = db_path
    
    async def setup(self):
        async with aiosqlite.connect(self.db_path) as db:
            # Points table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS points (
                    user_id INTEGER PRIMARY KEY,
                    points INTEGER DEFAULT 0
                )
            """)
            
            # Freeplay tracking table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS freeplay_claimed (
                    user_id INTEGER PRIMARY KEY,
                    claimed INTEGER DEFAULT 0
                )
            """)
            
            # MESSAGE COUNTER TABLE (NEW)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS message_counter (
                    user_id INTEGER PRIMARY KEY,
                    message_count INTEGER DEFAULT 0
                )
            """)
            
            await db.commit()
        print(f"Database ready: {self.db_path}")
    
    async def get_points(self, user_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT points FROM points WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
    
    async def set_points(self, user_id: int, points: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO points (user_id, points) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET points = ?
            """, (user_id, points, points))
            await db.commit()
    
    async def add_points(self, user_id: int, amount: int):
        current = await self.get_points(user_id)
        await self.set_points(user_id, current + amount)
    
    async def remove_points(self, user_id: int, amount: int):
        current = await self.get_points(user_id)
        new_amount = max(0, current - amount)
        await self.set_points(user_id, new_amount)
    
    async def reset_points(self, user_id: int):
        await self.set_points(user_id, 0)
    
    async def get_all_points(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id, points FROM points ORDER BY points DESC") as cursor:
                return await cursor.fetchall()
    
    # FREEPLAY TRACKING
    async def has_claimed_freeplay(self, user_id: int) -> bool:
        """Check if user has already claimed freeplay"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT claimed FROM freeplay_claimed WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result[0] == 1 if result else False
    
    async def mark_freeplay_claimed(self, user_id: int):
        """Mark that user has claimed their freeplay"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO freeplay_claimed (user_id, claimed) VALUES (?, 1)
                ON CONFLICT(user_id) DO UPDATE SET claimed = 1
            """, (user_id,))
            await db.commit()
    
    async def reset_freeplay(self, user_id: int):
        """Reset freeplay claim for a user (admin only)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM freeplay_claimed WHERE user_id = ?", (user_id,))
            await db.commit()
    
    async def reset_all_freeplays(self):
        """Reset ALL freeplay claims (admin only)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM freeplay_claimed")
            await db.commit()
    
    # MESSAGE COUNTER FOR AUTO POINTS
    async def get_message_count(self, user_id: int) -> int:
        """Get user's message count"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT message_count FROM message_counter WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
    
    async def increment_message_count(self, user_id: int) -> int:
        """Increment message count and return new count"""
        async with aiosqlite.connect(self.db_path) as db:
            current_count = await self.get_message_count(user_id)
            new_count = current_count + 1
            
            await db.execute("""
                INSERT INTO message_counter (user_id, message_count) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET message_count = ?
            """, (user_id, new_count, new_count))
            await db.commit()
            return new_count
    
    async def reset_message_count(self, user_id: int):
        """Reset message count to 0"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO message_counter (user_id, message_count) VALUES (?, 0)
                ON CONFLICT(user_id) DO UPDATE SET message_count = 0
            """, (user_id,))
            await db.commit()
    
    async def get_all_message_counts(self):
        """Get all user message counts"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id, message_count FROM message_counter ORDER BY message_count DESC") as cursor:
                return await cursor.fetchall()