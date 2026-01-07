import sqlite3

# Connect to SQLite and create the 'talks.db' database
try:
    # Connect to SQLite database
    conn = sqlite3.connect("talks.db")
    cursor = conn.cursor()

    # SQL commands to create tables in the correct order
    # TABLES = [
    #     """
    #     CREATE TABLE IF NOT EXISTS users (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         username TEXT NOT NULL UNIQUE,
    #         email TEXT NOT NULL UNIQUE,
    #         password TEXT NOT NULL,
    #         bio TEXT,
    #         contact TEXT,
    #         google_id TEXT
    #     );
    #     """,
    #     """
    #     CREATE TABLE IF NOT EXISTS posts (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         user_id INTEGER NOT NULL,
    #         content TEXT NOT NULL,
    #         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    #         FOREIGN KEY (user_id) REFERENCES users (id)
    #     );
    #     """,
    #     """
    #     CREATE TABLE IF NOT EXISTS comments (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         post_id INTEGER NOT NULL,
    #         user_id INTEGER NOT NULL,
    #         content TEXT NOT NULL,
    #         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    #         FOREIGN KEY (post_id) REFERENCES posts (id),
    #         FOREIGN KEY (user_id) REFERENCES users (id)
    #     );
    #     """,
    #     """
    #     CREATE TABLE IF NOT EXISTS post_likes (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         post_id INTEGER NOT NULL,
    #         user_id INTEGER NOT NULL,
    #         FOREIGN KEY (post_id) REFERENCES posts (id),
    #         FOREIGN KEY (user_id) REFERENCES users (id)
    #     );
    #     """,
    #     """
    #     CREATE TABLE IF NOT EXISTS comment_likes (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         comment_id INTEGER NOT NULL,
    #         user_id INTEGER NOT NULL,
    #         FOREIGN KEY (comment_id) REFERENCES comments (id),
    #         FOREIGN KEY (user_id) REFERENCES users (id)
    #     );
    #     """,
    #     """
    #     CREATE TABLE IF NOT EXISTS reports (
    #         report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         post_id INTEGER,
    #         status TEXT DEFAULT 'Pending',
    #         reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    #         FOREIGN KEY (post_id) REFERENCES posts (id)
    #     );
    #     """,
    #     """
    #     CREATE TABLE IF NOT EXISTS user_queries (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         name TEXT NOT NULL,
    #         email TEXT NOT NULL,
    #         message TEXT NOT NULL
    #     );
    #     """,
    #     """
    #     CREATE TABLE IF NOT EXISTS hashtags (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         tag TEXT UNIQUE,
    #         count INTEGER DEFAULT 1,
    #         post_ids TEXT
    #     );
    #     """,
    #     """
    #     CREATE TABLE IF NOT EXISTS email_verifications (
    #         email TEXT PRIMARY KEY,
    #         code TEXT NOT NULL,
    #         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    #     );
    #     """
    # ]

    # Execute each table creation query in order
    # for table_sql in TABLES:
    #     cursor.execute(table_sql)

    cursor.execute(
        """select """
    )
    print(cursor.fetchall())
    print("All tables created successfully.")

    # Commit the changes and close the connection
    conn.commit()
    cursor.close()
    conn.close()

except sqlite3.Error as e:
    print(f"An error occurred: {e}")
