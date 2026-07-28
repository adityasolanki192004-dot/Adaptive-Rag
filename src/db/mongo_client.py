"""
MongoDB client initialization.
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = "adaptive_rag"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
