import sqlite3
conn = sqlite3.connect("somnath_temple.db") 
cursor = conn.cursor() 
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