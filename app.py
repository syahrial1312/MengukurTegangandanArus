from datetime import date
from flask import Flask, request, jsonify, render_template, redirect
from flask_mysqldb import MySQL

app = Flask(__name__)

# Konfigurasi koneksi ke MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Fou90ryan10**'  # Ganti dengan password MySQL kamu
app.config['MYSQL_DB'] = 'daya_listrik'

mysql = MySQL(app)

@app.route('/')
def home():
    return redirect('/dashboard')

# Endpoint untuk menerima data dari ESP8266
@app.route('/insert', methods=['POST'])
def insert():
    try:
        arus = float(request.form['arus'])
        tegangan = float(request.form['tegangan'])
        daya = float(request.form['daya'])
        tarif_per_kwh = 1352 # dalam Rupiah

        # Hitung kWh: daya dalam Watt, interval 10 detik
        energy_kwh = daya / 360000.0
        tambahan_harga = energy_kwh * tarif_per_kwh

        cur = mysql.connection.cursor()

        # Simpan ke sensor_data
        cur.execute("""
            INSERT INTO sensor_data (arus, tegangan, daya, energy_kwh)
            VALUES (%s, %s, %s, %s)
        """, (arus, tegangan, daya, energy_kwh))

        # Update atau insert ke kwh_harian
        today = date.today()
        cur.execute("""
            INSERT INTO kwh_harian (tanggal, total_kwh, total_harga)
            VALUES (CURDATE(), %s, %s)
            ON DUPLICATE KEY UPDATE 
                total_kwh = total_kwh + VALUES(total_kwh),
                total_harga = total_harga + VALUES(total_harga)
        """, (energy_kwh, tambahan_harga))

        mysql.connection.commit()
        cur.close()

        return "Data berhasil disimpan dan energi tercatat!", 200
    except Exception as e:
        return f"Gagal menyimpan data: {str(e)}", 400

# Endpoint untuk melihat data (untuk chart nanti)
@app.route('/data', methods=['GET'])
def get_data():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT waktu, arus, tegangan, daya 
        FROM sensor_data 
        WHERE DATE(waktu) = CURDATE() 
        ORDER BY waktu DESC 
        LIMIT 100
    """)
    rows = cur.fetchall()
    cur.close()

    data = []
    for row in rows:
        data.append({
            'waktu': row[0].strftime('%Y-%m-%d %H:%M:%S'),
            'arus': row[1],
            'tegangan': row[2],
            'daya': row[3]
        })

    return jsonify(data)

@app.route('/data-kwh-harian')
def data_kwh_harian():
    cur = mysql.connection.cursor()
    cur.execute("SELECT tanggal, total_kwh, total_harga FROM kwh_harian ORDER BY tanggal ")
    results = cur.fetchall()
    cur.close()

    # Konversi ke format JSON
    data = []
    for row in results:
        data.append({
            'tanggal': row[0].strftime('%Y-%m-%d'),  # Format tanggal
            'total_kwh': round(row[1], 3),
            'total_harga': int(row[2])
        })
    return jsonify(data)

@app.route('/total-kwh')
def total_kwh_today():
    cur = mysql.connection.cursor()
    cur.execute("SELECT total_kwh, total_harga FROM kwh_harian WHERE tanggal = CURDATE()")
    row = cur.fetchone()
    cur.close()

    if row:
        return jsonify({
            "total_kwh": round(row[0], 3),
            "total_harga": round(row[1], 0)
        })
    else:
        return jsonify({
            "total_kwh": 0.0,
            "total_harga": 0
        })


@app.route('/dashboard')
def dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT waktu, arus, tegangan, daya FROM sensor_data ORDER BY waktu DESC LIMIT 100")
    rowsData = cur.fetchall()
    cur.close()
    return render_template('index.html',rows=rowsData)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
