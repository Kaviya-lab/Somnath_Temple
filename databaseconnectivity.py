import sqlite3
conn = sqlite3.connect("somnath_temple_data.db") 
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
    no_of_pl INTEGER,
    qr_code TEXT UNIQUE,
    status TEXT DEFAULT 'Confirmed',
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS persons (
    person_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    age INTEGER,
    gender TEXT,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
);
""")
conn.commit()  # save changes to database
conn.close()   # close connection