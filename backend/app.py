import os
import sys
import csv
import io
import re

# Ensure root workspace is in python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from datetime import datetime
from flask import Flask, render_template, jsonify, request
from backend.database.db import get_db_connection, init_db
from backend.agents.coordinator import CoordinatorAgent

app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, 'templates'),
    static_folder=os.path.join(ROOT_DIR, 'static')
)

coordinator = CoordinatorAgent()

def get_request_user_id(default=1):
    payload = request.get_json(silent=True) or {}
    raw_user_id = payload.get('user_id', request.args.get('user_id', default))
    try:
        return int(raw_user_id)
    except (TypeError, ValueError):
        return default

def _normalize_csv_header(value):
    return re.sub(r'[^a-z0-9]', '', str(value or '').lower())

def _find_csv_column(headers, aliases):
    normalized = {_normalize_csv_header(header): header for header in headers}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    return None

def _parse_csv_date(value):
    value = str(value or '').strip()
    if not value:
        raise ValueError('date is required')
    for date_format in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y'):
        try:
            return datetime.strptime(value, date_format).strftime('%Y-%m-%d')
        except ValueError:
            continue
    raise ValueError('invalid date; use YYYY-MM-DD or a common day/month format')

def _parse_csv_amount(value):
    text = str(value or '').strip().replace(',', '').replace('₹', '').replace('$', '')
    if not text:
        raise ValueError('amount is required')
    negative = text.startswith('(') and text.endswith(')')
    text = text.strip('()')
    amount = float(text)
    if amount == 0:
        raise ValueError('amount must not be zero')
    return -abs(amount) if negative else amount

def _infer_import_category(title):
    text = title.lower()
    category_keywords = {
        'Food & Dining': ('food', 'grocery', 'restaurant', 'dining', 'cafe', 'coffee', 'zomato', 'swiggy'),
        'Shopping & Electronics': ('shopping', 'amazon', 'flipkart', 'electronics', 'clothing'),
        'Transportation': ('transport', 'uber', 'ola', 'petrol', 'fuel', 'metro', 'taxi'),
        'Housing & Utilities': ('rent', 'electric', 'utility', 'water', 'internet', 'broadband'),
        'Entertainment & Leisure': ('movie', ' cinema', 'game', 'entertainment', 'netflix'),
        'Healthcare & Fitness': ('health', 'medical', 'doctor', 'gym', 'fitness', 'pharmacy'),
    }
    for category, keywords in category_keywords.items():
        if any(keyword in text for keyword in keywords):
            return category
    return 'Subscriptions & Misc'

def _normalize_import_type(value):
    normalized = str(value or '').strip().lower()
    if normalized in ('income', 'credit', 'credited', 'deposit', 'deposit credited'):
        return 'income'
    if normalized in ('expense', 'debit', 'debited', 'withdrawal', 'payment'):
        return 'expense'
    return None

def _existing_transaction_keys(cursor, user_id, rows=None):
    keys = set()
    cursor.execute(
        "SELECT date, title, amount FROM transactions WHERE user_id = ?",
        (user_id,)
    )
    keys.update((row['date'], row['title'].strip().lower(), round(float(row['amount']), 2))
                for row in cursor.fetchall())
    if rows:
        keys.update((row['date'], row['title'].strip().lower(), round(float(row['amount']), 2))
                    for row in rows)
    return keys

def _parse_import_csv(file_storage, user_id):
    filename = (file_storage.filename or '').lower()
    if not filename.endswith('.csv'):
        return None, ['Please upload a CSV file.']

    try:
        content = file_storage.read().decode('utf-8-sig')
    except (UnicodeDecodeError, AttributeError):
        return None, ['CSV must be a UTF-8 text file.']
    if not content.strip():
        return None, ['The CSV file is empty.']

    reader = csv.DictReader(io.StringIO(content))
    headers = reader.fieldnames or []
    date_column = _find_csv_column(headers, ('date', 'transactiondate', 'txndate'))
    description_column = _find_csv_column(headers, ('description', 'title', 'narration', 'details', 'memo'))
    amount_column = _find_csv_column(headers, ('amount', 'transactionamount', 'value'))
    category_column = _find_csv_column(headers, ('category', 'transactioncategory'))
    type_column = _find_csv_column(headers, ('type', 'transactiontype', 'direction'))
    debit_column = _find_csv_column(headers, ('debit', 'withdrawal', 'withdrawals'))
    credit_column = _find_csv_column(headers, ('credit', 'deposit', 'deposits'))

    missing = []
    if not date_column:
        missing.append('Date')
    if not description_column:
        missing.append('Description')
    if not amount_column and not debit_column and not credit_column:
        missing.append('Amount')
    if missing:
        return None, [f"Missing required column(s): {', '.join(missing)}"]

    conn = get_db_connection()
    cursor = conn.cursor()
    existing_keys = _existing_transaction_keys(cursor, user_id)
    conn.close()

    valid_rows = []
    invalid_rows = []
    duplicate_count = 0
    for row_number, raw_row in enumerate(reader, start=2):
        try:
            date_value = _parse_csv_date(raw_row.get(date_column, ''))
            title = str(raw_row.get(description_column, '') or '').strip()
            if not title:
                raise ValueError('description is required')

            raw_amount = raw_row.get(amount_column, '') if amount_column else ''
            amount = _parse_csv_amount(raw_amount) if str(raw_amount or '').strip() else 0.0
            if debit_column and str(raw_row.get(debit_column, '') or '').strip():
                amount = -abs(_parse_csv_amount(raw_row.get(debit_column)))
            elif credit_column and str(raw_row.get(credit_column, '') or '').strip():
                amount = abs(_parse_csv_amount(raw_row.get(credit_column)))
            if amount == 0:
                raise ValueError('amount is required and must not be zero')

            raw_type = str(raw_row.get(type_column, '') or '').strip() if type_column else ''
            explicit_type = _normalize_import_type(raw_type) if raw_type else None
            if raw_type and not explicit_type:
                raise ValueError('type must be income or expense')
            transaction_type = explicit_type
            if not transaction_type:
                if amount < 0:
                    transaction_type = 'expense'
                elif debit_column and str(raw_row.get(debit_column, '') or '').strip():
                    transaction_type = 'expense'
                elif credit_column and str(raw_row.get(credit_column, '') or '').strip():
                    transaction_type = 'income'
                else:
                    raise ValueError('type is required for positive amounts; use income or expense')

            amount = abs(float(amount))
            title_key = (date_value, title.lower(), round(amount, 2))
            if title_key in existing_keys:
                duplicate_count += 1
                continue

            category = str(raw_row.get(category_column, '') or '').strip() if category_column else ''
            valid_rows.append({
                'date': date_value,
                'title': title,
                'amount': round(amount, 2),
                'category': category or _infer_import_category(title),
                'type': transaction_type
            })
            existing_keys.add(title_key)
        except (TypeError, ValueError) as error:
            invalid_rows.append({'row': row_number, 'error': str(error)})

    return {
        'valid_rows': valid_rows,
        'invalid_rows': invalid_rows,
        'duplicate_count': duplicate_count,
        'total_rows': len(valid_rows) + len(invalid_rows) + duplicate_count
    }, []

def format_goal_data(goal, monthly_surplus=0.0):
    """
    Format a savings goal record with computed metrics:
    - remaining_amount: target - current
    - months_remaining: calculated from target_date
    - required_monthly_saving: remaining / months
    - progress_pct: current / target * 100
    - status: COMPLETED, ON TRACK, or AT RISK
    """
    target = float(goal.get('target_amount', 0.0))
    current = float(goal.get('current_amount', 0.0))
    remaining = max(0.0, round(target - current, 2))
    progress = round(min(100.0, (current / target) * 100), 1) if target > 0 else (100.0 if current >= target else 0.0)

    target_date = goal.get('target_date') or ''
    months_remaining = 1
    if target_date:
        try:
            today = datetime.now()
            t_dt = datetime.strptime(str(target_date).split('T')[0], "%Y-%m-%d")
            diff_days = (t_dt - today).days
            months_remaining = max(0, round(diff_days / 30.4))
        except Exception:
            months_remaining = 1

    if remaining <= 0:
        req_monthly = 0.0
        status = "COMPLETED"
    else:
        req_monthly = round(remaining / max(1, months_remaining), 2)
        if monthly_surplus >= req_monthly:
            status = "ON TRACK"
        else:
            status = "AT RISK"

    return {
        "id": goal.get('id'),
        "user_id": goal.get('user_id'),
        "title": goal.get('title'),
        "target_amount": target,
        "current_amount": current,
        "target_date": target_date,
        "remaining_amount": remaining,
        "months_remaining": months_remaining,
        "required_monthly_saving": req_monthly,
        "progress_pct": progress,
        "status": status
    }

@app.route('/')
def index():
    return render_template('index.html', page_name='dashboard')

@app.route('/dashboard')
def dashboard():
    return render_template('index.html', page_name='dashboard')

@app.route('/transactions')
def transactions():
    return render_template('transactions.html', page_name='transactions')

@app.route('/transactions/import')
def transaction_import():
    return render_template('transaction_import.html', page_name='transactions')

@app.route('/goals')
def goals():
    return render_template('goals.html', page_name='goals')

@app.route('/simulator')
def simulator():
    return render_template('simulator.html', page_name='simulator')

@app.route('/transactions/add')
@app.route('/add-expense')
def transaction_add():
    return render_template('transaction_add.html', page_name='transactions')

@app.route('/edit-expense/<int:txn_id>')
def edit_expense(txn_id):
    return render_template('transaction_add.html', page_name='transactions', edit_id=txn_id)

@app.route('/purchase-check')
def purchase_check():
    return render_template('purchase_check.html', page_name='purchase')

@app.route('/ask-ai')
def ask_ai():
    return render_template('index.html', page_name='dashboard', auto_open_chat=True)

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    user_id = request.args.get('user_id', 1, type=int)
    
    # Process full analysis using coordinator
    res = coordinator.process_request("Dashboard View Summary", user_id=user_id)
    
    # Fetch recent transactions (both Income and Expense)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, date, title, amount, category, type
        FROM transactions
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT 5
    """, (user_id,))
    recent_txs = [dict(row) for row in cursor.fetchall()]
    
    # Fetch savings goals with computed progress and tracking metrics
    user_surplus = float(res["data"]["analysis"].get("monthly_surplus", 0.0))
    cursor.execute("SELECT * FROM savings_goals WHERE user_id = ? ORDER BY id ASC", (user_id,))
    raw_goals = [dict(row) for row in cursor.fetchall()]
    goals = [format_goal_data(g, user_surplus) for g in raw_goals]
    conn.close()

    validation = res["data"].get("validation", {})

    dashboard_payload = {
        "user_id": user_id,
        # --- Health (corrected by ValidationAgent if rules triggered) ---
        "health_score": res["data"]["health"]["health_score"],
        "health_tier": res["data"]["health"]["health_tier"],
        "risk_level": res["data"]["health"]["risk_level"],
        # --- Analysis ---
        "monthly_income": res["data"]["analysis"]["monthly_income"],
        "monthly_expenses": res["data"]["analysis"]["monthly_expenses"],
        "current_savings": res["data"]["analysis"]["current_savings"],
        "monthly_surplus": res["data"]["analysis"]["monthly_surplus"],
        "expense_ratio": res["data"]["analysis"]["expense_ratio"],
        "top_category": res["data"]["analysis"]["top_category"],
        "category_distribution": res["data"]["analysis"]["category_distribution"],
        "health_breakdown": res["data"]["health"]["breakdown"],
        "budget_optimization": res["data"]["budget"],
        # --- Forecast (corrected by ValidationAgent if rules triggered) ---
        "forecast": res["data"]["forecast"],
        # --- Transactions & Goals ---
        "recent_transactions": recent_txs,
        "savings_goals": goals,
        # --- Validation metadata (new) ---
        "is_prediction_corrected": validation.get("is_self_corrected", False),
        "correction_reasons": [
            c["reason"] for c in validation.get("corrections_applied", [])
        ],
        "corrections_applied": [
            c["rule"] for c in validation.get("corrections_applied", [])
        ],
        "emergency_recommendations": validation.get("emergency_recommendations", []),
        # --- AI Insight: from ValidationAgent if corrected, else static fallback ---
        "ai_insight_of_the_day": (
            validation.get("ai_insight")
            or (
                f"Based on your {res['data']['health']['health_tier']} health rating, lowering "
                f"*{res['data']['analysis']['top_category']}* by 15% will add "
                f"₹{res['data']['analysis']['category_distribution'].get(res['data']['analysis']['top_category'], 0)*0.15:,.2f} "
                f"to monthly savings."
            )
        )
    }

    return jsonify(dashboard_payload)

@app.route('/api/summary', methods=['GET'])
def get_summary():
    """Lightweight endpoint for header nav pills — no ML, just DB query."""
    user_id = request.args.get('user_id', 1, type=int)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT current_savings FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        current_savings = float(user_row['current_savings']) if user_row else 0.0

        cursor.execute("""
            SELECT SUM(CASE WHEN type='income' THEN amount ELSE 0 END)  AS total_income,
                   SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS total_expense
            FROM transactions WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        total_income  = float(row['total_income']  or 0)
        total_expense = float(row['total_expense'] or 0)
        conn.close()

        expense_ratio = (total_expense / total_income) if total_income > 0 else 0
        health_score  = max(0, min(100, round(100 - (expense_ratio * 100))))

        return jsonify({
            "current_savings": current_savings,
            "health_score": health_score
        })
    except Exception as e:
        print(f"[Summary API Error] {e}")
        return jsonify({"current_savings": 0, "health_score": 0})


@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.json or {}
    query = data.get('query', '').strip()
    user_id = data.get('user_id', 1)

    if not query:
        return jsonify({"error": "Query string is required"}), 400

    res = coordinator.process_request(query, user_id=user_id)

    return jsonify(res)

@app.route('/api/predict_purchase', methods=['POST'])
def predict_purchase_api():
    data = request.json or {}
    item_name = data.get('item_name', 'Requested Item')
    item_price = float(data.get('item_price', 50000.0))
    user_id = data.get('user_id', 1)

    query = f"Can I buy a {item_name} for ₹{item_price}?"
    res = coordinator.process_request(query, user_id=user_id)

    validation = res["data"].get("validation", {})
    return jsonify({
        "query": query,
        "purchase_analysis": res["data"]["purchase"],
        "purchase_precheck": validation.get("purchase_precheck"),
        "is_prediction_corrected": validation.get("is_self_corrected", False),
        "ai_insight": validation.get("ai_insight", ""),
        "agent_telemetry": res["pipeline_steps"]
    })

@app.route('/api/transactions', methods=['GET', 'POST'])
def transactions_api():
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = get_request_user_id()

    if request.method == 'POST':
        data = request.json or {}
        title = data.get('title', 'Transaction').strip()
        amount = float(data.get('amount', 0.0))
        category = data.get('category', 'Subscriptions & Misc')
        txn_type = data.get('type', 'expense') # 'income' or 'expense'
        date_str = data.get('date') or datetime.now().strftime('%Y-%m-%d')

        cursor.execute("""
            INSERT INTO transactions (user_id, date, title, amount, category, type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, date_str, title, amount, category, txn_type))

        # If incoming income transaction, update user's liquid savings balance as well!
        if txn_type == 'income':
            cursor.execute("""
                UPDATE users SET current_savings = current_savings + ? WHERE id = ?
            """, (amount, user_id))
        else:
            cursor.execute("""
                UPDATE users SET current_savings = max(0, current_savings - ?) WHERE id = ?
            """, (amount, user_id))

        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": f"{txn_type.capitalize()} transaction added successfully"})

    cursor.execute("""
        SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT 50
    """, (user_id,))
    txs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(txs)

@app.route('/api/transactions/import/preview', methods=['POST'])
def transaction_import_preview_api():
    file_storage = request.files.get('file')
    if not file_storage or not file_storage.filename:
        return jsonify({'status': 'error', 'message': 'Please select a CSV file.'}), 400

    parsed, errors = _parse_import_csv(file_storage, get_request_user_id())
    if errors:
        return jsonify({'status': 'error', 'message': errors[0]}), 400
    return jsonify({
        'status': 'success',
        'user_id': get_request_user_id(),
        'valid_count': len(parsed['valid_rows']),
        'invalid_count': len(parsed['invalid_rows']),
        'duplicate_count': parsed['duplicate_count'],
        'rows': parsed['valid_rows'],
        'invalid_rows': parsed['invalid_rows'],
        'total_rows': parsed['total_rows']
    })

@app.route('/api/transactions/import', methods=['POST'])
def transaction_import_api():
    data = request.get_json(silent=True) or {}
    rows = data.get('rows')
    user_id = get_request_user_id()
    if not isinstance(rows, list) or not rows:
        return jsonify({'status': 'error', 'message': 'No validated transaction rows were provided.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        if not cursor.fetchone():
            return jsonify({'status': 'error', 'message': 'User account was not found.'}), 400

        existing_keys = _existing_transaction_keys(cursor, user_id)
        imported_count = 0
        invalid_count = 0
        duplicate_count = 0
        invalid_rows = []

        for row_number, row in enumerate(rows, start=1):
            try:
                date_value = _parse_csv_date(row.get('date'))
                title = str(row.get('title', '') or '').strip()
                amount = abs(float(row.get('amount')))
                transaction_type = _normalize_import_type(row.get('type'))
                category = str(row.get('category', '') or '').strip()
                if not title:
                    raise ValueError('description is required')
                if amount <= 0:
                    raise ValueError('amount must be greater than zero')
                if transaction_type not in ('income', 'expense'):
                    raise ValueError('type must be income or expense')
                if not category:
                    category = _infer_import_category(title)

                key = (date_value, title.lower(), round(amount, 2))
                if key in existing_keys:
                    duplicate_count += 1
                    continue

                cursor.execute('''
                    INSERT INTO transactions (user_id, date, title, amount, category, type)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, date_value, title, amount, category, transaction_type))
                balance_delta = amount if transaction_type == 'income' else -amount
                cursor.execute(
                    'UPDATE users SET current_savings = max(0, current_savings + ?) WHERE id = ?',
                    (balance_delta, user_id)
                )
                existing_keys.add(key)
                imported_count += 1
            except (TypeError, ValueError, AttributeError) as error:
                invalid_count += 1
                invalid_rows.append({'row': row_number, 'error': str(error)})

        conn.commit()
        return jsonify({
            'status': 'success',
            'message': f'{imported_count} transactions imported successfully',
            'imported_count': imported_count,
            'invalid_count': invalid_count,
            'duplicate_count': duplicate_count,
            'invalid_rows': invalid_rows
        })
    except Exception:
        conn.rollback()
        return jsonify({'status': 'error', 'message': 'Transactions could not be imported.'}), 500
    finally:
        conn.close()

@app.route('/api/transactions/<int:txn_id>', methods=['PUT', 'DELETE'])
def transaction_detail_api(txn_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = get_request_user_id()

    cursor.execute("SELECT * FROM transactions WHERE id = ? AND user_id = ?", (txn_id, user_id))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return jsonify({"status": "error", "message": "Transaction not found"}), 404

    existing_dict = dict(existing)
    old_amount = float(existing_dict['amount'])
    old_type = existing_dict['type']

    if request.method == 'DELETE':
        if old_type == 'income':
            cursor.execute("UPDATE users SET current_savings = max(0, current_savings - ?) WHERE id = ?", (old_amount, user_id))
        else:
            cursor.execute("UPDATE users SET current_savings = current_savings + ? WHERE id = ?", (old_amount, user_id))

        cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (txn_id, user_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Transaction deleted successfully"})

    elif request.method == 'PUT':
        data = request.json or {}
        title = data.get('title', existing_dict['title']).strip()
        amount = float(data.get('amount', old_amount))
        category = data.get('category', existing_dict['category'])
        txn_type = data.get('type', old_type)
        date_str = data.get('date', existing_dict['date'])

        # 1. Revert old savings impact
        if old_type == 'income':
            cursor.execute("UPDATE users SET current_savings = max(0, current_savings - ?) WHERE id = ?", (old_amount, user_id))
        else:
            cursor.execute("UPDATE users SET current_savings = current_savings + ? WHERE id = ?", (old_amount, user_id))

        # 2. Apply new savings impact
        if txn_type == 'income':
            cursor.execute("UPDATE users SET current_savings = current_savings + ? WHERE id = ?", (amount, user_id))
        else:
            cursor.execute("UPDATE users SET current_savings = max(0, current_savings - ?) WHERE id = ?", (amount, user_id))

        # 3. Update transaction record
        cursor.execute("""
            UPDATE transactions 
            SET title = ?, amount = ?, category = ?, type = ?, date = ?
            WHERE id = ? AND user_id = ?
        """, (title, amount, category, txn_type, date_str, txn_id, user_id))

        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Transaction updated successfully"})

# ==============================================================================
# FEATURE 4: FINANCIAL GOAL PLANNER API
# ==============================================================================

@app.route('/api/goals', methods=['GET', 'POST'])
def goals_api():
    user_id = get_request_user_id()
    analysis_res = coordinator.analysis_agent.run_analysis(user_id=user_id)
    monthly_surplus = float(analysis_res.get('monthly_surplus', 0.0))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json or {}
        title = data.get('title', '').strip()
        target_amount = float(data.get('target_amount', 0.0))
        current_amount = float(data.get('current_amount', 0.0))
        target_date = data.get('target_date', '').strip()

        if not title:
            conn.close()
            return jsonify({"status": "error", "message": "Goal title is required"}), 400
        if target_amount <= 0:
            conn.close()
            return jsonify({"status": "error", "message": "Target amount must be greater than zero"}), 400
        if current_amount < 0:
            conn.close()
            return jsonify({"status": "error", "message": "Current amount cannot be negative"}), 400
        if current_amount > target_amount:
            conn.close()
            return jsonify({"status": "error", "message": "Current amount cannot exceed the target amount"}), 400

        cursor.execute("""
            INSERT INTO savings_goals (user_id, title, target_amount, current_amount, target_date)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, title, target_amount, current_amount, target_date))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()

        goal_data = format_goal_data({
            "id": new_id,
            "user_id": user_id,
            "title": title,
            "target_amount": target_amount,
            "current_amount": current_amount,
            "target_date": target_date
        }, monthly_surplus)

        return jsonify({"status": "success", "message": "Goal created successfully", "goal": goal_data})

    # GET: return all formatted goals
    cursor.execute("SELECT * FROM savings_goals WHERE user_id = ? ORDER BY id ASC", (user_id,))
    raw_goals = [dict(row) for row in cursor.fetchall()]
    conn.close()

    formatted_goals = [format_goal_data(g, monthly_surplus) for g in raw_goals]
    return jsonify(formatted_goals)

@app.route('/api/goals/<int:goal_id>', methods=['PUT', 'DELETE'])
def goal_detail_api(goal_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = get_request_user_id()

    cursor.execute("SELECT * FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return jsonify({"status": "error", "message": "Goal not found"}), 404

    existing_dict = dict(existing)

    if request.method == 'DELETE':
        cursor.execute("DELETE FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Goal deleted successfully"})

    elif request.method == 'PUT':
        data = request.json or {}
        title = data.get('title', existing_dict['title']).strip()
        target_amount = float(data.get('target_amount', existing_dict['target_amount']))
        current_amount = float(data.get('current_amount', existing_dict['current_amount']))
        target_date = data.get('target_date', existing_dict['target_date']).strip()

        if not title:
            conn.close()
            return jsonify({"status": "error", "message": "Goal title is required"}), 400
        if target_amount <= 0:
            conn.close()
            return jsonify({"status": "error", "message": "Target amount must be greater than zero"}), 400
        if current_amount < 0:
            conn.close()
            return jsonify({"status": "error", "message": "Current amount cannot be negative"}), 400
        if current_amount > target_amount:
            conn.close()
            return jsonify({"status": "error", "message": "Current amount cannot exceed the target amount"}), 400

        cursor.execute("""
            UPDATE savings_goals
            SET title = ?, target_amount = ?, current_amount = ?, target_date = ?
            WHERE id = ? AND user_id = ?
        """, (title, target_amount, current_amount, target_date, goal_id, user_id))
        conn.commit()
        conn.close()

        return jsonify({"status": "success", "message": "Goal updated successfully"})

# ==============================================================================
# FEATURE 5: WHAT-IF FINANCIAL SIMULATOR API
# ==============================================================================

@app.route('/api/simulate', methods=['POST'])
def simulate_api():
    """
    Deterministic What-If Financial Simulation API.
    Calculates the exact effect of financial decisions using actual user data:
    1. Category spending reduction (e.g. cut Food & Dining by 20%)
    2. Monthly income change (e.g. salary increment by ₹10,000)
    3. General expense cut (e.g. trim discretionary expenses by 15%)
    Computes effect on: expenses, monthly surplus, savings rate, yearly wealth gain,
    and acceleration towards completing active financial goals.
    """
    data = request.json or {}
    scenario_type = data.get('scenario_type', 'category_reduction') # 'category_reduction', 'income_change', 'expense_cut'
    user_id = data.get('user_id', 1)

    # Fetch live financial analysis
    analysis_res = coordinator.analysis_agent.run_analysis(user_id=user_id)
    monthly_income = float(analysis_res['monthly_income'])
    monthly_expenses = float(analysis_res['monthly_expenses'])
    current_savings = float(analysis_res['current_savings'])
    current_surplus = float(analysis_res['monthly_surplus'])
    category_distribution = analysis_res['category_distribution']

    current_savings_rate = round((current_surplus / monthly_income * 100), 1) if monthly_income > 0 else 0.0

    simulated_income = monthly_income
    simulated_expenses = monthly_expenses
    category_name = None
    category_original = 0.0
    category_simulated = 0.0
    monthly_savings_increase = 0.0
    explanation = ""

    if scenario_type == 'category_reduction':
        category_name = data.get('category', 'Food & Dining')
        reduction_pct = float(data.get('percentage', 20.0))
        category_original = float(category_distribution.get(category_name, 0.0))

        monthly_savings_increase = round(category_original * (reduction_pct / 100.0), 2)
        category_simulated = round(max(0.0, category_original - monthly_savings_increase), 2)
        simulated_expenses = round(max(0.0, monthly_expenses - monthly_savings_increase), 2)
        explanation = (
            f"Reducing '{category_name}' spending by {reduction_pct:.0f}% drops category costs from "
            f"₹{category_original:,.2f} to ₹{category_simulated:,.2f}, freeing up ₹{monthly_savings_increase:,.2f} every month."
        )

    elif scenario_type == 'income_change':
        delta_income = float(data.get('amount', 10000.0))
        simulated_income = round(max(0.0, monthly_income + delta_income), 2)
        monthly_savings_increase = round(delta_income, 2)
        explanation = (
            f"Increasing monthly income by ₹{delta_income:,.2f} elevates total income from "
            f"₹{monthly_income:,.2f} to ₹{simulated_income:,.2f}, adding ₹{delta_income:,.2f} directly to monthly surplus."
        )

    elif scenario_type == 'expense_cut':
        reduction_pct = float(data.get('percentage', 10.0))
        monthly_savings_increase = round(monthly_expenses * (reduction_pct / 100.0), 2)
        simulated_expenses = round(max(0.0, monthly_expenses - monthly_savings_increase), 2)
        explanation = (
            f"Trimming total monthly spending by {reduction_pct:.0f}% saves ₹{monthly_savings_increase:,.2f} each month, "
            f"reducing overall outflow to ₹{simulated_expenses:,.2f}."
        )

    simulated_surplus = round(simulated_income - simulated_expenses, 2)
    annual_additional_savings = round(monthly_savings_increase * 12, 2)
    simulated_savings_rate = round((simulated_surplus / simulated_income * 100), 1) if simulated_income > 0 else 0.0
    savings_rate_diff = round(simulated_savings_rate - current_savings_rate, 1)

    # Calculate impact on savings goals
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title, target_amount, current_amount FROM savings_goals WHERE user_id = ?", (user_id,))
    goals = cursor.fetchall()
    conn.close()

    goal_impacts = []
    for g in goals:
        remaining = max(0.0, float(g['target_amount']) - float(g['current_amount']))
        if remaining > 0 and current_surplus > 0:
            current_months = round(remaining / current_surplus, 1)
            new_months = round(remaining / simulated_surplus, 1) if simulated_surplus > 0 else 99.0
            months_saved = max(0.0, round(current_months - new_months, 1))
            goal_impacts.append({
                "title": g['title'],
                "remaining": remaining,
                "current_months_to_goal": current_months,
                "simulated_months_to_goal": new_months,
                "months_faster": months_saved
            })

    return jsonify({
        "scenario_type": scenario_type,
        "category": category_name,
        "category_original": category_original,
        "category_simulated": category_simulated,
        "current": {
            "monthly_income": monthly_income,
            "monthly_expenses": monthly_expenses,
            "monthly_surplus": current_surplus,
            "savings_rate_pct": current_savings_rate
        },
        "simulated": {
            "monthly_income": simulated_income,
            "monthly_expenses": simulated_expenses,
            "monthly_surplus": simulated_surplus,
            "savings_rate_pct": simulated_savings_rate
        },
        "impact": {
            "monthly_savings_increase": monthly_savings_increase,
            "annual_additional_savings": annual_additional_savings,
            "savings_rate_gain_pct": savings_rate_diff,
            "goals_acceleration": goal_impacts
        },
        "explanation": explanation
    })

if __name__ == '__main__':
    db_path = os.path.join(ROOT_DIR, 'backend', 'finpilot.db')
    if not os.path.exists(db_path):
        init_db()
    
    app.run(host='127.0.0.1', port=5000, debug=True)
