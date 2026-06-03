from flask import Flask, request, jsonify, render_template
import pickle
import pandas as pd
import sqlite3
import re
from datetime import datetime

app = Flask(__name__)

# Load model and feature columns
with open('fraud_model.pkl', 'rb') as f:
    model = pickle.load(f)

with open('feature_columns.pkl', 'rb') as f:
    feature_columns = pickle.load(f)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('fraud.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            transaction_hour INTEGER,
            foreign_transaction INTEGER,
            location_mismatch INTEGER,
            device_trust_score REAL,
            velocity_last_24h INTEGER,
            merchant_category TEXT,
            result TEXT,
            confidence REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()

    # Convert to dataframe
    df = pd.DataFrame([data])
    df = pd.get_dummies(df)

    # Fix column names
    df.columns = [re.sub(r'[^A-Za-z0-9_]', '_', col) for col in df.columns]
    df = df.reindex(columns=feature_columns, fill_value=0)

    # Predict
    prediction = model.predict(df)[0]
    probability = model.predict_proba(df)[0][1]
    result = 'FRAUD' if prediction == 1 else 'LEGITIMATE'
    confidence = round(float(probability) * 100, 2)

    # Save to SQLite
    try:
        conn = sqlite3.connect('fraud.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO predictions 
            (amount, transaction_hour, foreign_transaction, location_mismatch,
             device_trust_score, velocity_last_24h, merchant_category, result, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['amount'], data['transaction_hour'],
            data['foreign_transaction'], data['location_mismatch'],
            data['device_trust_score'], data['velocity_last_24h'],
            data['merchant_category'], result, confidence
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB Error:", e)

    return jsonify({'result': result, 'confidence': confidence})

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('fraud.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM predictions ORDER BY timestamp DESC LIMIT 50")
    records = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', records=records)

if __name__ == '__main__':
    app.run(debug=True)