from flask import Flask, jsonify, request
from flask_cors import CORS
import time
import lgpio
import cv2
from ultralytics import YOLO
import firebase_admin
from firebase_admin import credentials, db
from threading import Lock

app = Flask(__name__)
CORS(app)

# Firebase setup
cred = credentials.Certificate("/home/massa/firebase_key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://massa-nae4b-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

# HX711 setup
DT_PIN = 5
SCK_PIN = 6
chip = None
GPIO_AVAILABLE = False

tare_value = 93859.3
scale_factor = 103.27338626672562
weight_lock = Lock()

BANANA_PRICES = {
    "Saba": 10,
    "Lakatan": 100,
    "Latundan": 70,
    "Senyorita": 45
}

def init_hx711():
    global chip, GPIO_AVAILABLE
    try:
        chip = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(chip, SCK_PIN, 0)
        lgpio.gpio_claim_input(chip, DT_PIN)
        GPIO_AVAILABLE = True
        print("[INFO] HX711 initialized successfully.")
    except Exception as e:
        print("[ERROR] HX711 initialization failed:", e)
        if chip:
            try:
                lgpio.gpiochip_close(chip)
            except:
                pass
        chip = None
        GPIO_AVAILABLE = False

def read_hx711():
    global chip, GPIO_AVAILABLE

    if not GPIO_AVAILABLE or chip is None:
        init_hx711()
        if not GPIO_AVAILABLE:
            print("[WARN] HX711 fallback to demo value 100000.")
            return 100000

    try:
        if lgpio.gpio_read(chip, DT_PIN) < 0:
            raise RuntimeError("GPIO read failed")

        lgpio.gpio_write(chip, SCK_PIN, 0)
        time.sleep(0.01)

        timeout_counter = 0
        while lgpio.gpio_read(chip, DT_PIN) == 1:
            timeout_counter += 1
            if timeout_counter > 1000:
                raise TimeoutError("HX711 not responding")
            time.sleep(0.001)

        data = 0
        for _ in range(24):
            lgpio.gpio_write(chip, SCK_PIN, 1)
            data = (data << 1) | lgpio.gpio_read(chip, DT_PIN)
            lgpio.gpio_write(chip, SCK_PIN, 0)

        lgpio.gpio_write(chip, SCK_PIN, 1)
        lgpio.gpio_write(chip, SCK_PIN, 0)

        if data & 0x800000:
            data -= 0x1000000

        return data

    except Exception as e:
        print("[ERROR] HX711 read failed:", e)
        try:
            if chip:
                lgpio.gpiochip_close(chip)
        except:
            pass
        chip = None
        GPIO_AVAILABLE = False
        return 100000

def read_hx711_stable(samples=10, threshold=0.1):
    if not GPIO_AVAILABLE:
        return 100000

    readings = []
    for _ in range(samples):
        reading = read_hx711()
        readings.append(reading)
        time.sleep(0.1)

    if not readings:
        return 0

    median = sorted(readings)[len(readings) // 2]
    filtered = [r for r in readings if abs(r - median) < threshold * abs(median)]

    return sum(filtered) / len(filtered) if filtered else median

def get_model():
    if not hasattr(app, 'banana_model'):
        app.banana_model = YOLO("/home/massa/banana_yolov8_modelv3.pt")
    return app.banana_model

@app.route("/weight", methods=["GET"])
def get_weight():
    try:
        if not hasattr(app, 'weight_history'):
            app.weight_history = []

        raw = read_hx711_stable(samples=10)
        print("Raw HX711 value:", raw)

        global tare_value
        if tare_value == -864.2:  # If using default tare
            with weight_lock:
                tare_value = read_hx711_stable(samples=20)
                print(f"Initialized tare value: {tare_value}")

        grams = (raw - tare_value) * scale_factor
        current_weight = max(0, grams / 1000)

        app.weight_history.append(current_weight)
        if len(app.weight_history) > 10:
            app.weight_history.pop(0)

        sorted_weights = sorted(app.weight_history)
        median_weight = sorted_weights[len(sorted_weights) // 2]
        
        filtered_weights = [w for w in app.weight_history 
                          if abs(w - median_weight) < 0.05 * median_weight or median_weight == 0]
        
        filtered_weight = sum(filtered_weights) / len(filtered_weights) if filtered_weights else median_weight

        return jsonify({
            "weight": round(filtered_weight, 3),
            "status": "success",
            "connected": GPIO_AVAILABLE
        })
    except Exception as e:
        print("Weight endpoint error:", str(e))
        return jsonify({
            "error": str(e),
            "status": "error",
            "connected": GPIO_AVAILABLE
        }), 500

@app.route("/tare", methods=["POST"])
def tare():
    try:
        global tare_value
        with weight_lock:
            tare_value = read_hx711_stable(samples=20)
        return jsonify({
            "status": "success",
            "new_tare": tare_value,
            "connected": GPIO_AVAILABLE
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "connected": GPIO_AVAILABLE
        }), 500

@app.route("/calibrate", methods=["POST"])
def calibrate():
    return jsonify({
        "status": "skipped",
        "message": "Calibration disabled – using static values.",
        "tare": tare_value,
        "scale_factor": scale_factor,
        "connected": GPIO_AVAILABLE
    })

@app.route("/detect", methods=["GET"])
def detect():
    cap = None
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return jsonify({"error": "Camera not available", "connected": GPIO_AVAILABLE}), 500

        ret, frame = cap.read()
        if not ret:
            return jsonify({"error": "Failed to capture image", "connected": GPIO_AVAILABLE}), 500

        model = get_model()
        results = model(frame, conf=0.4, iou=0.6)
        banana_type = "Unknown"

        if results[0].boxes:
            cls_id = int(results[0].boxes[0].cls[0])
            banana_type = results[0].names[cls_id].strip().capitalize()

        if banana_type in BANANA_PRICES:
            return jsonify({
                "banana_type": banana_type,
                "price_per_kg": BANANA_PRICES[banana_type],
                "status": "success",
                "connected": GPIO_AVAILABLE
            })
        return jsonify({
            "error": "No banana detected",
            "connected": GPIO_AVAILABLE
        }), 404
    except Exception as e:
        return jsonify({
            "error": str(e),
            "connected": GPIO_AVAILABLE
        }), 500
    finally:
        if cap:
            cap.release()

@app.route("/transaction", methods=["POST"])
def complete_transaction():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "error": "No data provided",
                "connected": GPIO_AVAILABLE
            }), 400

        payment = float(data.get("payment", 0))
        items = data.get("items", [])

        if not isinstance(items, list):
            return jsonify({
                "error": "Invalid items format",
                "connected": GPIO_AVAILABLE
            }), 400

        total = sum(float(item.get('amount', 0)) for item in items)
        change = round(payment - total, 2)

        if change < 0:
            return jsonify({
                "error": "Payment amount is insufficient",
                "connected": GPIO_AVAILABLE
            }), 400

        transaction = {
            "items": items,
            "total": total,
            "payment": payment,
            "change": change,
            "timestamp": time.time()
        }

        try:
            db.reference("transactions").push(transaction)
            return jsonify({
                "status": "success",
                "transaction": transaction,
                "connected": GPIO_AVAILABLE
            })
        except Exception as firebase_error:
            return jsonify({
                "error": f"Firebase error: {str(firebase_error)}",
                "connected": GPIO_AVAILABLE
            }), 500

    except ValueError:
        return jsonify({
            "error": "Invalid payment value",
            "connected": GPIO_AVAILABLE
        }), 400
    except Exception as e:
        return jsonify({
            "error": str(e),
            "connected": GPIO_AVAILABLE
        }), 500

if __name__ == "__main__":
    init_hx711()
    # Auto-tare on startup
    with weight_lock:
        tare_value = read_hx711_stable(samples=20)
        print(f"Initial tare value set to: {tare_value}")
    app.run(host="0.0.0.0", port=5000, threaded=True)
