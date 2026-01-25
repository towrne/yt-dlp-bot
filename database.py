import json
import uuid
import aiosqlite


async def setup_database():
    """Initializes the database and creates the 'links' table."""
    db = await aiosqlite.connect("bot_data.db")
    # Using TEXT to store the JSON string of the links array
    await db.execute("""
        CREATE TABLE IF NOT EXISTS link_sets (
            id TEXT PRIMARY KEY,
            links TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.commit()
    await db.close()


async def store_links_and_get_id(links_array):
    """Stores a list of links in the DB and returns a unique ID."""
    db = await aiosqlite.connect("bot_data.db")
    # Generate a short, unique ID
    unique_id = str(uuid.uuid4().hex)[:8]
    # Convert the Python list to a JSON string for storage
    links_json = json.dumps(links_array)
    await db.execute(
        "INSERT INTO link_sets (id, links) VALUES (?, ?)", (unique_id, links_json)
    )
    await db.commit()
    await db.close()
    return unique_id


async def get_links_by_id(unique_id):
    """Retrieves and decodes a list of links from the DB by its ID."""
    db = await aiosqlite.connect("bot_data.db")
    async with db.execute(
        "SELECT links FROM link_sets WHERE id = ?", (unique_id,)
    ) as cursor:
        result = await cursor.fetchone()
    await db.close()
    if result:
        # Convert the JSON string back to a Python list
        return json.loads(result[0])
    return None
