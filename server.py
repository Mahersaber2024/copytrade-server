from flask import Flask, request, jsonify
import time
import logging
import json
import os

# غیرفعال کردن لاگ‌های دسترسی HTTP Flask
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# مسیر فایل برای ذخیره سیگنال‌ها
SIGNALS_FILE = 'signals.json'

# لیست سیگنال‌ها
signals = []

# تابع برای لود سیگنال‌ها از فایل
def load_signals():
    global signals
    if os.path.exists(SIGNALS_FILE):
        try:
            with open(SIGNALS_FILE, 'r') as f:
                signals = json.load(f)
            print(f"📂 Loaded {len(signals)} signals from {SIGNALS_FILE}")
        except Exception as e:
            print(f"❌ Error loading signals from file: {e}")
            signals = []
    else:
        print(f"📂 No signals file found, starting with empty list")
        signals = []

# تابع برای ذخیره سیگنال‌ها در فایل
def save_signals():
    try:
        with open(SIGNALS_FILE, 'w') as f:
            json.dump(signals, f)
        print(f"💾 Signals saved to {SIGNALS_FILE}")
    except Exception as e:
        print(f"❌ Error saving signals to file: {e}")

# لود سیگنال‌ها در زمان شروع برنامه
load_signals()

@app.route('/send-signal', methods=['POST'])
def send_signal():
    global signals
    try:
        data = request.get_json(force=True)  # JSON خام بدون دستکاری
        required_fields = ['unique_id', 'symbol', 'order_type', 'lot', 'open_price', 'stop_loss', 'take_profit', 'open_time']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400
        
        # اضافه کردن زمان دریافت سیگنال
        data['timestamp_received'] = time.time()
        
        # اگر lot=0 باشد، سیگنال را حذف کن
        if data.get('lot', 0) <= 0.0:
            signals = [s for s in signals if s['unique_id'] != data['unique_id']]
            print(f"🗑️ Removed signal with unique_id={data['unique_id']} due to lot=0")
        else:
            # به‌روزرسانی یا اضافه کردن سیگنال
            found = False
            for i, signal in enumerate(signals):
                if signal['unique_id'] == data['unique_id']:
                    signals[i] = data  # به‌روزرسانی سیگنال
                    found = True
                    break
            if not found:
                signals.append(data)  # اضافه کردن سیگنال جدید
            print(f"📤 Server received signal: unique_id={data['unique_id']}, lot={data['lot']}")

        # ذخیره سیگنال‌ها در فایل فقط در این endpoint
        save_signals()
        
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        print(f"❌ Server error in /send-signal: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/get-signals', methods=['GET'])
def get_signals():
    global signals
    current_time = time.time()
    expiration_time = 120  # ۲ دقیقه برای سیگنال‌های بسته‌شده (lot=0)
    
    # حذف سیگنال‌های منقضی‌شده (lot=0 و قدیمی‌تر از ۲ دقیقه)
    signals = [s for s in signals if not (s.get('lot', 0) <= 0.0 and (current_time - s.get('timestamp_received', 0) > expiration_time))]
    
    # مرتب‌سازی بر اساس open_time به‌صورت صعودی
    sorted_signals = sorted(signals, key=lambda x: int(x.get('open_time', 0)))
    
    return jsonify(sorted_signals), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Railway اینو میده
    app.run(host='0.0.0.0', port=port, debug=True)

