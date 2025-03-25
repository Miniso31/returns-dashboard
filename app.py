from flask import Flask, render_template, request, send_file, redirect
import sqlite3, os, json
from datetime import datetime
from werkzeug.utils import secure_filename
import xlsxwriter

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# DB Setup
def init_db():
    conn = sqlite3.connect('returns.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            item_barcode TEXT,
            sku TEXT,
            condition TEXT,
            damage_description TEXT,
            return_reason TEXT,
            order_date TEXT,
            price REAL,
            lpn TEXT,
            box_label TEXT,
            warehouse_location TEXT,
            staff_name TEXT,
            platform TEXT,
            images TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = 'SELECT * FROM returns'
    params = []

    if start_date and end_date:
        query += ' WHERE DATE(timestamp) BETWEEN ? AND ?'
        params = [start_date, end_date]

    conn = sqlite3.connect('returns.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    data = cursor.fetchall()
    conn.close()
    return render_template('index.html', returns=data)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        form = request.form
        files = request.files.getlist('images')

        image_filenames = []
        for file in files:
            if file and file.filename:
                filename = datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filenames.append(filename)

        if len(image_filenames) == 0:
            return "At least one image is required!", 400

        conn = sqlite3.connect('returns.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO returns (
                order_id, item_barcode, sku, condition, damage_description,
                return_reason, order_date, price, lpn, box_label,
                warehouse_location, staff_name, platform, images, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            form['order_id'],
            form['item_barcode'],
            form['sku'],
            form['condition'],
            form.get('damage_description', ''),
            form.get('return_reason', ''),
            form.get('order_date', ''),
            form.get('price', 0),
            form.get('lpn', ''),
            form.get('box_label', ''),
            form['warehouse_location'],
            form['staff_name'],
            form['platform'],
            json.dumps(image_filenames),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
        conn.close()
        return "<h2>✅ Return submitted successfully!</h2><a href='/'>Back to Dashboard</a>"

    return render_template('add_return.html')

@app.route('/download_excel')
def download_excel():
    conn = sqlite3.connect('returns.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM returns')
    data = cursor.fetchall()
    conn.close()

    file_path = "returns_export.xlsx"
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet()

    headers = ['Order ID', 'Barcode', 'SKU', 'Condition', 'Damage Desc', 'Return Reason', 'Order Date',
               'Price', 'LPN', 'Box Label', 'Warehouse', 'Staff', 'Platform', 'Images', 'Timestamp']

    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header)

    for row_num, row in enumerate(data, start=1):
        for col_num, value in enumerate(row[1:]):
            if col_num == 13:  # Images column
                try:
                    imgs = json.loads(value)
                    for img in imgs:
                        link = f'file:///{os.path.abspath("static/uploads/" + img)}'
                        worksheet.write_url(row_num, col_num, link, string=img)
                except:
                    worksheet.write(row_num, col_num, str(value))
            else:
                worksheet.write(row_num, col_num, str(value))

    workbook.close()
    return send_file(file_path, as_attachment=True)

@app.route('/delete/<int:return_id>', methods=['POST'])
def delete_return(return_id):
    conn = sqlite3.connect('returns.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM returns WHERE id = ?', (return_id,))
    conn.commit()
    conn.close()
    return redirect('/')

app.jinja_env.filters['loads'] = json.loads

if __name__ == '__main__':
    app.run(debug=True)
