import pymysql
from flask import Flask, request, jsonify, render_template, redirect
from datetime import datetime
import pytz

app = Flask(__name__)

def get_db_connection():
    db = pymysql.connect(
        host='gateway01.ap-southeast-1.prod.aws.tidbcloud.com',
        user='v1XWKekDGZz3Fj2.root',
        password='qbRONysqh95LT90K',
        database='daya_listrik',
        ssl={'ca': 'isrgrootx1.pem'},
        cursorclass=pymysql.cursors.DictCursor
    )
    cur = db.cursor()
    cur.execute("SET time_zone = '+07:00';")
    cur.close()
    return db

@app.route('/')
def home():
    return redirect('/dashboard')

@app.route('/insert', methods=['POST'])
def insert():
    try:
        arus = float(request.form['arus'])
        tegangan = float(request.form['tegangan'])
        daya = float(request.form['daya'])
        tarif_per_kwh = 1352

        energy_kwh = daya / 360000.0
        tambahan_harga = energy_kwh * tarif_per_kwh

        db = get_db_connection()
        cur = db.cursor()

        # waktu sekarang pakai timezone Jakarta
        now_jakarta = datetime.now(pytz.timezone('Asia/Jakarta'))
        waktu_str = now_jakarta.strftime('%Y-%m-%d %H:%M:%S')

        cur.execute("""
            INSERT INTO sensor_data (waktu, arus, tegangan, daya, energy_kwh)
            VALUES (%s, %s, %s, %s, %s)
        """, (waktu_str, arus, tegangan, daya, energy_kwh))

        cur.execute("""
            INSERT INTO kwh_harian (tanggal, total_kwh, total_harga)
            VALUES (CURDATE(), %s, %s)
            ON DUPLICATE KEY UPDATE 
                total_kwh = total_kwh + VALUES(total_kwh),
                total_harga = total_harga + VALUES(total_harga)
        """, (energy_kwh, tambahan_harga))

        db.commit()
        cur.close()
        db.close()

        return "Data berhasil disimpan dan energi tercatat!", 200
    except Exception as e:
        return f"Gagal menyimpan data: {str(e)}", 400

@app.route('/data', methods=['GET'])
def get_data():
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("""
        SELECT waktu, arus, tegangan, daya 
        FROM sensor_data 
        WHERE DATE(waktu) = CURDATE() 
        ORDER BY waktu DESC 
        LIMIT 100
    """)
    rows = cur.fetchall()
    cur.close()
    db.close()

    data = []
    for row in rows:
        # row adalah dict, akses pakai key
        waktu = row['waktu']
        if isinstance(waktu, str):
            # kalau ternyata string langsung pakai
            waktu_str = waktu
        else:
            waktu_str = waktu.strftime('%Y-%m-%d %H:%M:%S')
        data.append({
            'waktu': waktu_str,
            'arus': row['arus'],
            'tegangan': row['tegangan'],
            'daya': row['daya']
        })
    return jsonify(data)


@app.route('/data-kwh-harian')
def data_kwh_harian():
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("SELECT tanggal, total_kwh, total_harga FROM kwh_harian ORDER BY tanggal")
    results = cur.fetchall()
    cur.close()
    db.close()

    data = []
    for row in results:
        tanggal = row['tanggal']
        if isinstance(tanggal, str):
            tanggal_str = tanggal
        else:
            tanggal_str = tanggal.strftime('%Y-%m-%d')
        data.append({
            'tanggal': tanggal_str,
            'total_kwh': round(row['total_kwh'], 3),
            'total_harga': int(row['total_harga'])
        })
    return jsonify(data)


@app.route('/total-kwh')
def total_kwh_today():
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("SELECT total_kwh, total_harga FROM kwh_harian WHERE tanggal = CURDATE()")
    row = cur.fetchone()
    cur.close()
    db.close()

    if row:
        return jsonify({
            "total_kwh": round(row['total_kwh'], 3),
            "total_harga": round(row['total_harga'], 0)
        })
    else:
        return jsonify({
            "total_kwh": 0.0,
            "total_harga": 0
        })


@app.route('/dashboard')
def dashboard():
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("SELECT waktu, arus, tegangan, daya FROM sensor_data ORDER BY waktu DESC LIMIT 100")
    rowsData = cur.fetchall()
    cur.close()
    db.close()
    return render_template('index.html', rows=rowsData)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
