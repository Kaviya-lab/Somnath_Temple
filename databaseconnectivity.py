import sqlite3
conn = sqlite3.connect("somnath_temple.db") 
cursor = conn.cursor() 
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    mobile TEXT,
    password_hash TEXT NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    qr_code TEXT UNIQUE,
    status TEXT DEFAULT 'Confirmed',
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)
""")
conn.commit()  # save changes to database
conn.close()   # close connection