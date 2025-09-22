from flask import Flask, request, jsonify
import sqlite3
import hashlib
import re
import jwt
import datetime
import qrcode
import io
import base64
from functools import wraps
import joblib
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Add this after creating app

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # change in production


# ------------------ DATABASE ------------------
def get_db_connection():
    conn = sqlite3.connect('somnath_temple_data.db')
    conn.row_factory = sqlite3.Row
    return conn

# ------------------ HELPERS ------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def is_valid_phone(phone):
    return bool(re.match(r'^\d{10}$', phone))

def generate_qr(data):
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# ------------------ JWT DECORATOR ------------------
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(" ")[1]
            except IndexError:
                return jsonify({"success": False, "message": "Token format invalid"}), 401
        if not token:
            return jsonify({"success": False, "message": "Token is missing"}), 401
        try:
            decoded = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = decoded.get('user_id')
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token expired"}), 401
        except:
            return jsonify({"success": False, "message": "Token invalid"}), 401
        return f(user_id, *args, **kwargs)
    return decorated

# ------------------ SIGNUP ------------------
@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        password = data.get('password')

        if not all([name, email, phone, password]):
            return jsonify({"success": False, "message": "All fields required"}), 400
        if not is_valid_phone(phone):
            return jsonify({"success": False, "message": "Phone must be 10 digits"}), 400

        password_hash = hash_password(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO users (name, email, mobile, password_hash) VALUES (?, ?, ?, ?)',
                (name, email, phone, password_hash)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return jsonify({"success": False, "message": "Email or phone already exists"}), 409
        finally:
            conn.close()
        return jsonify({"success": True, "message": "Signup successful"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ------------------ LOGIN ------------------
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        phone = data.get('phone')
        password = data.get('password')
        if not phone or not password:
            return jsonify({"success": False, "message": "Phone and password required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE mobile = ?", (phone,))
        user = cursor.fetchone()
        conn.close()
        if not user or hash_password(password) != user['password_hash']:
            return jsonify({"success": False, "message": "Invalid phone or password"}), 401

        token = jwt.encode({
            'user_id': user['user_id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }, app.config['SECRET_KEY'], algorithm='HS256')

        return jsonify({"success": True, "message": "Login successful", "token": token}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ------------------ LOAD ML MODEL ------------------
try:
    ml_model = joblib.load("somnath_crowd_model.pkl")
except Exception as e:
    print(f"Error loading ML model: {e}")
    ml_model = None

# ------------------ PREDICT CROWD ------------------
@app.route('/predict', methods=['POST'])
@token_required
def predict(user_id):
    if not ml_model:
        return jsonify({"success": False, "message": "ML model not loaded"}), 500

    data = request.get_json()
    date_str = data.get("date")  # expecting YYYY-MM-DD

    if not date_str:
        return jsonify({"success": False, "message": "Date is required"}), 400
    date_obj = None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            date_obj = datetime.datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue

    if not date_obj:
        return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Now convert to features for your model
    day_of_week = date_obj.weekday()
    month = date_obj.month
    features = [[day_of_week, month]]
    predicted_crowd = ml_model.predict(features)[0]
    return jsonify({"success": True, "date": date_obj.strftime("%Y-%m-%d"), "prediction": predicted_crowd})
#   try:
#        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
#        day_of_week = date_obj.weekday()
#        month = date_obj.month
#        features = [[day_of_week, month]]       predicted_crowd = ml_model.predict(features)[0]
#   except ValueError:
#      return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD"}), 400
# except Exception as e:#    return jsonify({"success": False, "message": f"Prediction error: {str(e)}"}), 500



# ------------------ BOOKING ------------------
@app.route('/booking', methods=['POST'])
@token_required
def booking(user_id):
    try:
        data = request.get_json()
        date = data.get('date')
        time = data.get('time')
        num_people = data.get('num_people')
        people = data.get('people')  # list of {name, age, gender}

        if not all([date, time, num_people, people]):
            return jsonify({"success": False, "message": "Date, time, number of people, and people details are required"}), 400
        if not isinstance(num_people, int) or num_people <= 0:
            return jsonify({"success": False, "message": "Number of people must be a positive integer"}), 400
        if len(people) != num_people:
            return jsonify({"success": False, "message": "Number of people does not match details provided"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Insert main booking
        cursor.execute(
            'INSERT INTO bookings (user_id, date, time, no_of_pl, status) VALUES (?, ?, ?, ?, ?)',
            (user_id, date, time, num_people, 'Confirmed')
        )
        booking_id = cursor.lastrowid

        # 2. Insert each person in persons table
        for p in people:
            cursor.execute(
                'INSERT INTO persons (booking_id, name, age, gender) VALUES (?, ?, ?, ?)',
                (booking_id, p['name'], p['age'], p.get('gender'))
            )

        conn.commit()
        conn.close()

        # Prepare QR code with booking and person details
        people_str = "; ".join([f"{p['name']} ({p['age']}, {p.get('gender','')})" for p in people])
        qr_data = f"Booking ID: {booking_id}\nDate: {date}\nTime: {time}\nPeople ({num_people}): {people_str}"
        qr_base64 = generate_qr(qr_data)

        return jsonify({
            "success": True,
            "message": "Booking confirmed",
            "booking_id": booking_id,
            "qr_code": qr_base64
        }), 201

    except Exception as e:
        return jsonify({"success": False, "message": f"Internal server error: {str(e)}"}), 500

# ------------------ VIEW BOOKINGS ------------------
@app.route('/view_bookings', methods=['GET'])
@token_required
def view_bookings(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT booking_id, date, time, no_of_pl FROM bookings WHERE user_id=? ORDER BY booking_id DESC", (user_id,))
        rows = cursor.fetchall()
        conn.close()

        bookings = [{"booking_id": r["booking_id"], "date": r["date"], "time": r["time"], "no_of_pl": r["no_of_pl"]} for r in rows]
        return jsonify({"success": True, "bookings": bookings}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Internal server error: {str(e)}"}), 500

# ------------------ BOOKING DETAILS ------------------
@app.route('/booking/<int:booking_id>', methods=['GET'])
@token_required
def booking_details(user_id, booking_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT booking_id, date, time, no_of_pl FROM bookings WHERE booking_id=? AND user_id=?", (booking_id, user_id))
        booking_row = cursor.fetchone()

        if not booking_row:
            conn.close()
            return jsonify({"success": False, "message": "Booking not found"}), 404

        cursor.execute("SELECT name, age, gender FROM persons WHERE booking_id = ?", (booking_id,))
        persons = cursor.fetchall()
        conn.close()

        people_str = "; ".join([f"{p['name']} ({p['age']}, {p['gender']})" for p in persons])
        qr_data = f"Booking ID: {booking_row['booking_id']}\nDate: {booking_row['date']}\nTime: {booking_row['time']}\nPeople ({len(persons)}): {people_str}"
        qr_base64 = generate_qr(qr_data)

        return jsonify({
            "success": True,
            "booking_id": booking_row['booking_id'],
            "qr_code": qr_base64
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Internal server error: {str(e)}"}), 500

# ------------------ HEALTH CHECK ------------------
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Server is running"})

from flask import render_template

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/booking_page')
def booking_page():
    return render_template('booking.html')

@app.route('/mybookings_page')
def mybookings_page():
    return render_template('mybookings.html')


# ------------------ RUN APP ------------------
if __name__ == '__main__':
    app.run(debug=True, port=5000)