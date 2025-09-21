from flask import Flask, request, jsonify
import joblib
import datetime

app = Flask(__name__)

# Load your ML model
with open("somnath_crowd_model.pkl", "rb") as f:
    model = joblib.load(f)
@app.route("/")
@app.route("/predict_crowd", methods=["POST"])
def predict_crowd():
    data = request.get_json()
    date_str = data.get("date") # Expecting 'YYYY-MM-DD' format

    if not date_str:
        return jsonify({"error": "Date is required"}), 400

    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        # Example: extracting features from date for your ML model
        day_of_week = date_obj.weekday()  # 0=Monday, 6=Sunday
        month = date_obj.month
        # You can add other features like holiday, festival, etc.
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Prepare features for ML model (example: [day_of_week, month])
    features = [[day_of_week, month]]
    predicted_crowd = model.predict(features)[0]

    return jsonify({"predicted_crowd": int(predicted_crowd)})


if __name__ == "__main__":
    app.run(debug=True)