import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import numpy as np
from PIL import Image
from tensorflow.keras.models import load_model
from datetime import datetime

# --- Configuration ---
app = Flask(__name__)
app.secret_key = '8480ac24fe7cc47d8a63fc93c671d8c1'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load model
model = load_model("model/Skin_Cancer_CNN_Local.h5")

# Ensure upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Routes ---

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        action = request.form['action']
        conn = sqlite3.connect('database.db')
        curs = conn.cursor()

        if action == 'signup':
            username = request.form['username'].strip()
            email    = request.form['email'].strip()
            password = request.form['password']
            role     = request.form['role']

            try:
                curs.execute("""
                  INSERT INTO User (username,email,password,role)
                  VALUES (?,?,?,?)
                """, (username,email,password,role))
                conn.commit()
                flash("Signup successful! Please login.", "success")
            except sqlite3.IntegrityError:
                flash("Username or email already exists.", "danger")
            finally:
                conn.close()
            return redirect(url_for('login'))

        elif action == 'login':
            username_or_email = request.form['username_or_email'].strip()
            password          = request.form['password']

            curs.execute("""
              SELECT userID,username, role FROM User
              WHERE (username=? OR email=?) AND password=?
            """, (username_or_email,username_or_email,password))
            user = curs.fetchone()
            conn.close()

            if user:
                session.clear()
                session['user_id']  = user[0]
                session['username'] = user[1]
                session['role'] = user[2]
                return redirect(url_for('index'))
            else:
                flash("Invalid username/email or password.", "danger")
                return redirect(url_for('login'))

    return render_template('login.html')




@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    username = session['username']
    role = session.get('role', 'USER')

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if role == 'ADMIN':
        cursor.execute('''
            SELECT d.*, u.username, i.filePath
            FROM Diagnosis d
            JOIN Image i ON d.imageID = i.imageID
            JOIN User u ON i.userID = u.userID
            ORDER BY d.diagnosisDate ASC
        ''')
    else:
        cursor.execute('''
            SELECT d.*, u.username, i.filePath
            FROM Diagnosis d
            JOIN Image i ON d.imageID = i.imageID
            JOIN User u ON i.userID = u.userID
            WHERE u.userID = ?
            ORDER BY d.diagnosisDate ASC
        ''', (user_id,))

    reports = cursor.fetchall()
    conn.close()

    return render_template('index.html', username=username, reports=reports)






@app.route('/predict', methods=['POST'])
def predict():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    file = request.files['image']
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Step 1: Preprocess image according to model input shape
        image = Image.open(filepath).resize((224, 224))  # Match model input
        image = image.convert("RGB")
        image = np.array(image) / 255.0
        image = np.expand_dims(image, axis=0)

        # Step 2: Predict
        prediction = model.predict(image)[0][0]
        label = "MELANOMA" if prediction > 0.5 else "NON_MELANOMA"
        confidence = float(prediction) if label == "MELANOMA" else 1.0 - float(prediction)


        # Step 3: Database insertions
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Insert into Image table
        upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO Image (userID, filePath, uploadDate) VALUES (?, ?, ?)
        """, (session['user_id'], filepath, upload_date))
        image_id = cursor.lastrowid

        # Insert into Diagnosis table
        diagnosis_date = upload_date
        cursor.execute("""
            INSERT INTO Diagnosis (imageID, diagnosisResult, confidenceScore, diagnosisDate) 
            VALUES (?, ?, ?, ?)
        """, (image_id, label, confidence, diagnosis_date))

        # Insert into ActivityLog table
        cursor.execute("""
            INSERT INTO ActivityLog (userID, action, entityType, entityID, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session['user_id'],
            'Prediction Performed',
            'Diagnosis',
            image_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))


        conn.commit()
        conn.close()

        return render_template('result.html', image_path=filepath, label=label, confidence=round(confidence * 100, 2), model_name='ResNet50', model_version='1.0')

    flash("No image uploaded!", "warning")
    return redirect(url_for('index'))




@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# --- Run ---
if __name__ == '__main__':
    app.run(debug=True)
