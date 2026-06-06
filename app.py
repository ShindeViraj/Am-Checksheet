import os
import io
import re
from datetime import datetime, timedelta
from collections import OrderedDict
from report_generator import find_template_data

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
    period = request.args.get('period', 'day')
    machine_id = request.args.get('machine_id', '')

    try:
        end_date = datetime.strptime(date, '%Y-%m-%d')
        if period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date
            
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Calculate prior period for trend
        if period == 'week':
            prev_start = start_date - timedelta(days=7)
            prev_end = start_date - timedelta(days=1)
        elif period == 'month':
            prev_start = start_date - timedelta(days=30)
            prev_end = start_date - timedelta(days=1)
        else: # day
            prev_start = start_date - timedelta(days=1)
            prev_end = start_date - timedelta(days=1)
            
        prev_start_str = prev_start.strftime('%Y-%m-%d')
        prev_end_str = prev_end.strftime('%Y-%m-%d')

        conn = get_db()
        with conn.cursor() as cur:
            params = [start_date_str, end_date_str]
            prev_params = [prev_start_str, prev_end_str]
            machine_sql = ""
            if machine_id:
                machine_sql = " AND machine_id = %s"
                params.append(machine_id)
                prev_params.append(machine_id)

            cur.execute(f"""
                SELECT COUNT(*) as total_checkpoints,
                       SUM(checkpoint_ok) as total_ok,
                       SUM(checkpoint_not_ok) as total_nok,
                       AVG(time_taken) as avg_time
                FROM checkpoints
                WHERE DATE(start_time) >= %s AND DATE(start_time) <= %s
                {machine_sql}
            """, tuple(params))
            summary = cur.fetchone()
            
            cur.execute(f"""
                SELECT COUNT(*) as prev_total
                FROM checkpoints
                WHERE DATE(start_time) >= %s AND DATE(start_time) <= %s
                {machine_sql}
            """, tuple(prev_params))
            prev_summary = cur.fetchone()
            
            trend_percent = 0
            if prev_summary and prev_summary['prev_total'] > 0:
                trend_percent = round(((summary['total_checkpoints'] - prev_summary['prev_total']) / prev_summary['prev_total']) * 100)
            elif summary['total_checkpoints'] > 0:
                trend_percent = 100
                
            if machine_id and period != 'day':
                # Show trend over time for a specific machine
                cur.execute(f"""
                    SELECT DATE(start_time) as group_key,
                           SUM(checkpoint_ok) as total_ok,
                           SUM(checkpoint_not_ok) as total_nok
                    FROM checkpoints
                    WHERE DATE(start_time) >= %s AND DATE(start_time) <= %s
                      AND machine_id = %s
                    GROUP BY DATE(start_time)
                    ORDER BY DATE(start_time)
                """, (start_date_str, end_date_str, machine_id))
            else:
                cur.execute(f"""
                    SELECT machine_id as group_key,
                           SUM(checkpoint_ok) as total_ok,
                           SUM(checkpoint_not_ok) as total_nok
                    FROM checkpoints
                    WHERE DATE(start_time) >= %s AND DATE(start_time) <= %s
                    {machine_sql}
                    GROUP BY machine_id
                """, tuple(params))
            chart_data = cur.fetchall()

            recent_params = []
            recent_sql = ""
            if machine_id:
                recent_sql = "WHERE machine_id = %s"
                recent_params.append(machine_id)

            cur.execute(f"""
                SELECT machine_id, checkpoint_no, checkpoint_ok,
                       checkpoint_not_ok, time_taken, start_time
                FROM checkpoints
                {recent_sql}
                ORDER BY start_time DESC
                LIMIT 10
            """, tuple(recent_params))
            recent = cur.fetchall()

        conn.close()

        # Convert datetime objects and Decimal for JSON serialisation
        for r in recent:
            # Map description from JSON
            template_data = find_template_data(r['machine_id'])
            cp_desc = "Description not found"
            if template_data and 'checkpoints' in template_data:
                for cp in template_data['checkpoints']:
                    if str(cp.get('s_no')) == str(r['checkpoint_no']):
                        cp_desc = cp.get('check_point', 'Description not found')
                        break
            r['description'] = cp_desc
            
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.strftime('%Y-%m-%d %H:%M:%S')
                elif hasattr(v, 'is_finite'):  # Decimal
                    r[k] = float(v)

        for r in chart_data:
            if hasattr(r['group_key'], 'strftime'):
                r['group_key'] = r['group_key'].strftime('%Y-%m-%d')
            elif hasattr(r['group_key'], 'is_finite'): # fallback
                pass

        return jsonify({
            'status': 'success',
            'date': date,
            'period': period,
            'machine_id': machine_id,
            'data': {
                'summary': {
                    'total': summary['total_checkpoints'] or 0,
                    'ok': int(summary['total_ok'] or 0),
                    'nok': int(summary['total_nok'] or 0),
                    'trend': trend_percent,
                    'avg_time': float(summary['avg_time'] or 0),
                },
                'chart_data': chart_data,
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
