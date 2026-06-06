import os
import io
import re
from datetime import datetime, timedelta
from collections import OrderedDict

from flask import Flask, render_template, request, jsonify, send_file
from db import get_db

app = Flask(__name__, static_folder='static', template_folder='templates')

# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route('/')
def dashboard():
    return render_template('index.html', today=datetime.now().strftime('%Y-%m-%d'))


@app.route('/machine_report')
def machine_report():
    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    return render_template('machine_report.html', today=today, week_ago=week_ago)


# ---------------------------------------------------------------------------
# API – Dashboard
# ---------------------------------------------------------------------------

@app.route('/api/dashboard/summary')
def api_dashboard_summary():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total_checkpoints,
                       SUM(checkpoint_ok) as total_ok,
                       SUM(checkpoint_not_ok) as total_nok,
                       AVG(time_taken) as avg_time
                FROM checkpoints
                WHERE DATE(start_time) = %s
            """, (date,))
            summary = cur.fetchone()

            cur.execute("""
                SELECT machine_id,
                       SUM(checkpoint_ok) as total_ok,
                       SUM(checkpoint_not_ok) as total_nok
                FROM checkpoints
                WHERE DATE(start_time) = %s
                GROUP BY machine_id
            """, (date,))
            machines = cur.fetchall()

            cur.execute("""
                SELECT machine_id, checkpoint_no, checkpoint_ok,
                       checkpoint_not_ok, time_taken, start_time
                FROM checkpoints
                ORDER BY created_at DESC
                LIMIT 10
            """)
            recent = cur.fetchall()

        conn.close()

        # Convert datetime objects and Decimal for JSON serialisation
        for r in recent:
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.strftime('%Y-%m-%d %H:%M:%S')
                elif hasattr(v, 'is_finite'):  # Decimal
                    r[k] = float(v)

        return jsonify({
            'status': 'success',
            'date': date,
            'data': {
                'summary': {
                    'total': int(summary['total_checkpoints'] or 0),
                    'ok': int(summary['total_ok'] or 0),
                    'nok': int(summary['total_nok'] or 0),
                    'avg_time': float(summary['avg_time'] or 0),
                },
                'machines': machines,
                'recent': recent,
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ---------------------------------------------------------------------------
# API – Machines list
# ---------------------------------------------------------------------------

@app.route('/api/reports/machines_list')
def api_machines_list():
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT machine_id FROM checkpoints ORDER BY machine_id")
            machines = [row['machine_id'] for row in cur.fetchall()]
        conn.close()
        return jsonify({'status': 'success', 'data': machines})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ---------------------------------------------------------------------------
# API – Machine history
# ---------------------------------------------------------------------------

@app.route('/api/reports/machine')
def api_machine_report():
    machine_id = request.args.get('machine_id')
    start_date = request.args.get('start_date', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))

    if not machine_id:
        return jsonify({'status': 'error', 'message': 'Machine ID is required'}), 400

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM checkpoints
                WHERE machine_id = %s
                  AND DATE(start_time) >= %s
                  AND DATE(start_time) <= %s
                ORDER BY start_time ASC
            """, (machine_id, start_date, end_date))
            data = cur.fetchall()
        conn.close()

        # Serialise datetime / Decimal
        for r in data:
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.strftime('%Y-%m-%d %H:%M:%S')
                elif hasattr(v, 'is_finite'):
                    r[k] = float(v)

        return jsonify({
            'status': 'success',
            'machine_id': machine_id,
            'start_date': start_date,
            'end_date': end_date,
            'data': data
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# API – Excel export  (dynamic generation via openpyxl)
# ---------------------------------------------------------------------------

from report_generator import generate_report
import calendar, zipfile as zf


# ---------------------------------------------------------------------------
# API – Export Route
# ---------------------------------------------------------------------------

@app.route('/api/export/excel')
def api_export_excel():
    machine_id = request.args.get('machine_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    report_type = request.args.get('report_type', 'monthly')

    if not machine_id or not start_date or not end_date:
        return jsonify({'status': 'error', 'message': 'Missing parameters'}), 400

    try:
        dt_start = datetime.strptime(start_date, '%Y-%m-%d')
        dt_end = datetime.strptime(end_date, '%Y-%m-%d')
        if report_type == 'custom' and (dt_end - dt_start).days > 31:
            return jsonify({'status': 'error', 'message': 'Custom range cannot exceed 31 days'}), 400

        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM checkpoints
                WHERE machine_id = %s
                  AND DATE(start_time) >= %s
                  AND DATE(start_time) <= %s
                ORDER BY start_time ASC
            """, (machine_id, start_date, end_date))
            rows = cur.fetchall()
        conn.close()

        if report_type == 'custom':
            month_str = f"Date: {start_date} to {end_date}"
        else:
            month_str = f"Month: {dt_start.strftime('%B %Y')}"

        buf = generate_report(machine_id, month_str, rows, start_date, end_date)

        safe = re.sub(r'[\\/*?:"<>|]', '_', machine_id.strip())
        return send_file(
            buf,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'TPM_{safe}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
