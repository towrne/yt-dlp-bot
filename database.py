import sqlite3
import json
import uuid

# --- Database Functions ---

def setup_database():
    """Initializes the database and creates the 'links' table."""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    # Using TEXT to store the JSON string of the links array
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS link_sets (
            id TEXT PRIMARY KEY,
            links TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def store_links_and_get_id(links_array):
    """Stores a list of links in the DB and returns a unique ID."""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    # Generate a short, unique ID
    unique_id = str(uuid.uuid4().hex)[:8]
    # Convert the Python list to a JSON string for storage
    links_json = json.dumps(links_array)
    cursor.execute("INSERT INTO link_sets (id, links) VALUES (?, ?)", (unique_id, links_json))
    conn.commit()
    conn.close()
    return unique_id

def get_links_by_id(unique_id):
    """Retrieves and decodes a list of links from the DB by its ID."""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT links FROM link_sets WHERE id = ?", (unique_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        # Convert the JSON string back to a Python list
        return json.loads(result[0])
    return None

# --- Run setup when your bot starts ---
setup_database()

