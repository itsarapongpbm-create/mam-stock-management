# -*- coding: utf-8 -*-
from flask import Flask, render_template, jsonify, request
import csv
import os
import random
import json
from datetime import datetime

app = Flask(__name__)

CSV_PATH = "C:/Users/Itsarapong.po/MAM/list.csv"
TEMP_CSV_PATH = "C:/Users/Itsarapong.po/MAM/list_temp.csv"
LOGS_PATH = "C:/Users/Itsarapong.po/MAM/stock_logs.csv"
SETTINGS_PATH = "C:/Users/Itsarapong.po/MAM/settings.json"

# Load Settings
def load_settings():
    default_settings = {"low_stock_threshold": 10}
    if not os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(default_settings, f, indent=4)
        return default_settings
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default_settings

def save_settings(settings):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)

# Initialize Logs File
def init_logs_file():
    if not os.path.exists(LOGS_PATH):
        with open(LOGS_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "product_id", "product_name", "type", "change", "previous_qty", "new_qty"])

# Log a transaction
def log_transaction(prod_id, prod_name, action_type, change, prev_qty, new_qty):
    init_logs_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOGS_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, str(prod_id), prod_name, action_type, str(change), str(prev_qty), str(new_qty)])

# Initialize CSV Schema
def init_csv_schema():
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found.")
        return
        
    rows = []
    header_rows = []
    
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        empty_row = next(reader, None)
        header_row = next(reader, None)
        
        if empty_row is not None:
            header_rows.append(empty_row)
        if header_row is not None:
            header_rows.append(header_row)
            
        for row in reader:
            rows.append(row)
            
    # Check if 'จำนวนคงเหลือ' is already in headers
    if len(header_rows) > 1:
        headers = header_rows[1]
        if 'จำนวนคงเหลือ' not in headers:
            headers.append('จำนวนคงเหลือ')
            # Initialize random quantities for demonstration
            for r in rows:
                if len(r) < 6:
                    r.extend([""] * (6 - len(r)))
                r[5] = str(random.choice([0, 5, 8, 12, 15, 20, 35, 45]))
            save_csv(header_rows, rows)
            print("CSV Schema initialized: Added 'จำนวนคงเหลือ' column.")
        else:
            updated = False
            for r in rows:
                if len(r) < 6:
                    r.extend([""] * (6 - len(r)))
                if not r[5].strip():
                    r[5] = str(random.choice([0, 5, 12, 25, 40]))
                    updated = True
            if updated:
                save_csv(header_rows, rows)

def save_csv(headers, rows):
    with open(TEMP_CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for h in headers:
            writer.writerow(h)
        writer.writerows(rows)
        
    if os.path.exists(CSV_PATH):
        os.remove(CSV_PATH)
    os.rename(TEMP_CSV_PATH, CSV_PATH)

def read_inventory():
    rows = []
    headers = []
    
    if not os.path.exists(CSV_PATH):
        return headers, rows
        
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        empty_row = next(reader, None)
        header_row = next(reader, None)
        
        headers.append(empty_row if empty_row else [])
        headers.append(header_row if header_row else [])
        
        for row in reader:
            if len(row) < 6:
                row.extend([""] * (6 - len(row)))
            rows.append(row)
            
    return headers, rows

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    _, rows = read_inventory()
    inventory = []
    for r in rows:
        if not r or len(r) < 2:
            continue
        try:
            qty = int(r[5]) if r[5].strip() else 0
        except ValueError:
            qty = 0
            
        inventory.append({
            'id': r[0],
            'name': r[1],
            'price': r[2],
            'image': r[3],
            'link': r[4],
            'quantity': qty
        })
    return jsonify(inventory)

@app.route('/api/adjust-stock', methods=['POST'])
def adjust_stock():
    data = request.json
    prod_id = str(data.get('id'))
    change = int(data.get('change', 0))
    
    headers, rows = read_inventory()
    updated_prod = None
    
    for r in rows:
        if r[0] == prod_id:
            try:
                curr_qty = int(r[5]) if r[5].strip() else 0
            except ValueError:
                curr_qty = 0
                
            new_qty = max(0, curr_qty + change)
            r[5] = str(new_qty)
            
            updated_prod = {
                'id': r[0],
                'name': r[1],
                'price': r[2],
                'image': r[3],
                'link': r[4],
                'quantity': new_qty
            }
            # Log transaction
            log_transaction(r[0], r[1], "adjust", change, curr_qty, new_qty)
            break
            
    if updated_prod:
        save_csv(headers, rows)
        return jsonify({'success': True, 'product': updated_prod})
    else:
        return jsonify({'success': False, 'error': 'Product not found'}), 404

@app.route('/api/add-product', methods=['POST'])
def add_product():
    data = request.json
    name = data.get('name', '').strip()
    price = data.get('price', '').strip()
    link = data.get('link', '').strip()
    image = data.get('image', '').strip()
    qty_val = data.get('quantity', '0')
    
    try:
        quantity = int(qty_val) if str(qty_val).strip() else 0
    except ValueError:
        quantity = 0
        
    if not name:
        return jsonify({'success': False, 'error': 'Product name is required'}), 400
        
    headers, rows = read_inventory()
    
    next_id = 1
    if rows:
        try:
            next_id = max(int(r[0]) for r in rows if r[0].isdigit()) + 1
        except ValueError:
            next_id = len(rows) + 1
            
    new_row = [str(next_id), name, price, image, link, str(quantity)]
    rows.append(new_row)
    save_csv(headers, rows)
    
    # Log addition
    log_transaction(new_row[0], name, "add", quantity, 0, quantity)
    
    return jsonify({
        'success': True,
        'product': {
            'id': new_row[0],
            'name': new_row[1],
            'price': new_row[2],
            'image': new_row[3],
            'link': new_row[4],
            'quantity': quantity
        }
    })

@app.route('/api/edit-product', methods=['POST'])
def edit_product():
    data = request.json
    prod_id = str(data.get('id'))
    name = data.get('name', '').strip()
    price = data.get('price', '').strip()
    link = data.get('link', '').strip()
    image = data.get('image', '').strip()
    qty_val = data.get('quantity', '0')
    
    try:
        new_qty = int(qty_val) if str(qty_val).strip() else 0
    except ValueError:
        new_qty = 0
        
    if not name:
        return jsonify({'success': False, 'error': 'Product name is required'}), 400
        
    headers, rows = read_inventory()
    updated_prod = None
    
    for r in rows:
        if r[0] == prod_id:
            try:
                prev_qty = int(r[5]) if r[5].strip() else 0
            except ValueError:
                prev_qty = 0
                
            r[1] = name
            r[2] = price
            r[3] = image
            r[4] = link
            r[5] = str(new_qty)
            
            updated_prod = {
                'id': r[0],
                'name': r[1],
                'price': r[2],
                'image': r[3],
                'link': r[4],
                'quantity': new_qty
            }
            
            # Log if quantity was changed during edit
            if prev_qty != new_qty:
                log_transaction(r[0], name, "adjust", new_qty - prev_qty, prev_qty, new_qty)
            else:
                log_transaction(r[0], name, "edit", 0, prev_qty, prev_qty)
            break
            
    if updated_prod:
        save_csv(headers, rows)
        return jsonify({'success': True, 'product': updated_prod})
    else:
        return jsonify({'success': False, 'error': 'Product not found'}), 404

@app.route('/api/delete-product', methods=['POST'])
def delete_product():
    data = request.json
    prod_id = str(data.get('id'))
    
    headers, rows = read_inventory()
    initial_len = len(rows)
    
    deleted_prod = None
    for r in rows:
        if r[0] == prod_id:
            deleted_prod = r
            break
            
    if deleted_prod:
        rows = [r for r in rows if r[0] != prod_id]
        save_csv(headers, rows)
        
        # Log deletion
        try:
            curr_qty = int(deleted_prod[5]) if deleted_prod[5].strip() else 0
        except ValueError:
            curr_qty = 0
        log_transaction(deleted_prod[0], deleted_prod[1], "delete", -curr_qty, curr_qty, 0)
        
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Product not found'}), 404

@app.route('/api/logs', methods=['GET'])
def get_logs():
    init_logs_file()
    logs = []
    with open(LOGS_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            logs.append(row)
    # Return reversed to show latest logs first
    return jsonify(logs[::-1])

@app.route('/api/settings', methods=['GET', 'POST'])
def manage_app_settings():
    if request.method == 'POST':
        data = request.json
        settings = load_settings()
        try:
            settings['low_stock_threshold'] = int(data.get('low_stock_threshold', 10))
            save_settings(settings)
            return jsonify({'success': True, 'settings': settings})
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid threshold value'}), 400
    else:
        return jsonify(load_settings())

if __name__ == '__main__':
    init_csv_schema()
    init_logs_file()
    app.run(host='0.0.0.0', debug=True, port=5000)
