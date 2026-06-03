from flask import Flask, request, jsonify, render_template
import pickle
import pandas as pd
import mysql.connector
from datetime import datetime

app = Flask(__name__)

# Load model and feature columns
with open('fraud_model.pkl', 'rb') as f:
    model = pickle.load(f)

with open('feature_columns.pkl', 'rb') as f:
    feature_columns = pickle.load(f)

# MySQL connection
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Shannu@2669",  # change this
        database="fraud_detection"
    )

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()

    # Convert to dataframe
    df = pd.DataFrame([data])
    df = pd.get_dummies(df)
    df = df.reindex(columns=feature_columns, fill_value=0)

    # Predict
    prediction = model.predict(df)[0]
    probability = model.predict_proba(df)[0][1]
    result = 'FRAUD' if prediction == 1 else 'LEGITIMATE'
    confidence = round(float(probability) * 100, 2)

    # Save to MySQL
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO predictions 
            (amount, transaction_hour, foreign_transaction, location_mismatch, 
             device_trust_score, velocity_last_24h, merchant_category, result, confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['amount'], data['transaction_hour'],
            data['foreign_transaction'], data['location_mismatch'],
            data['device_trust_score'], data['velocity_last_24h'],
            data['merchant_category'], result, confidence
        ))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("DB Error:", e)

    return jsonify({'result': result, 'confidence': confidence})

@app.route('/dashboard')
def dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM predictions ORDER BY timestamp DESC LIMIT 50")
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('dashboard.html', records=records)

if __name__ == '__main__':
    app.run(debug=True)