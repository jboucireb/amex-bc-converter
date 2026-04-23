from flask import Flask, request, send_file, render_template, jsonify
import csv
import io
import os
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

BEFORE_COLS = [
    'Transaction Index', 'Allocation Index', 'RCA Number', 'BCA Number',
    'Cardmember Number', 'Cycle End Date', 'Cardmember Name', 'Salesperson Code',
    'Transaction Date', 'Transaction Reference Number', 'Status', 'Merchant Name',
    'Merchant Street', 'Merchant City', 'Merchant State', 'Merchant Zip',
    'Merchant Country', 'Merchant Reference Number', 'Cardmember Reference Number',
    'Source Currency Code', 'Source Amount', 'Billed Currency Code', 'Billed Amount',
    'Description 1', 'BCA Manager Approval User', 'BCA Manager Approval Timestamp',
    'Cardmember Comment', 'Manager Comment', 'Allocation Amount', 'Allocation Percent',
    'Allocation Description', 'Accounting Manager Allocation Approval User',
    'Accounting Manager Allocation Approval Timestamp', 'GL Account', 'Employee ID',
    'Cost Center', 'Description 2', 'Description 3', 'Description 4'
]

# Salesperson Code moves from index 7 to the last position
AFTER_COL_ORDER = list(range(0, 7)) + list(range(8, 39)) + [7]
AFTER_COLS = [BEFORE_COLS[i] for i in AFTER_COL_ORDER]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Please upload a CSV file'}), 400

    try:
        content = file.read().decode('utf-8-sig')  # utf-8-sig handles BOM if present
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        headers = reader.fieldnames or []
    except Exception as e:
        return jsonify({'error': f'Could not read file: {str(e)}'}), 400

    # Validate columns
    missing = [c for c in BEFORE_COLS if c not in headers]
    if missing:
        return jsonify({
            'error': f"This doesn't look like an Amex export. Missing columns: {', '.join(missing[:3])}"
                     + (f' and {len(missing) - 3} more.' if len(missing) > 3 else '.')
        }), 400

    # Transform: reorder columns
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=AFTER_COLS, extrasaction='ignore', lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({col: row.get(col, '') for col in AFTER_COLS})

    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    original = os.path.splitext(file.filename)[0]
    out_filename = f"{original}_BC_Ready_{timestamp}.csv"

    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=out_filename
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
