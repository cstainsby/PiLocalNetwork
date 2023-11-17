from flask import Flask, request, jsonify, render_template, g
from datetime import datetime
import requests
import json

from db import PiDatabase
import server_helpers
from datatypes import MPU6050_Data

DEBUG_MODE = True
PORT = 8080
HOST = '0.0.0.0'

app = Flask(__name__)
dbo = PiDatabase(debug_mode=DEBUG_MODE)

# device mac_address (identifier) to its ip
active_connections = {}


def build_request_to_self(endpoint: str):
    if endpoint: 
        return "http://" + HOST + ":" + str(PORT) + endpoint
    else: 
        return ""

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def to_pretty_json(json_val):
    temp_json_dict = json.loads(json_val)
    return json.dumps(temp_json_dict, sort_keys=True, indent=4, separators=(',', ': '))
app.jinja_env.filters["tojson_pretty"] = to_pretty_json

@app.route("/", methods=['GET'])
def home():
    data = {
        "devices": []
    }

    with app.app_context():
        conn = dbo.get_db()
        cursor = conn.cursor()

        checked_out_devices = dbo.get_active_devices_with_user_info(cursor)

        for device in checked_out_devices:
            timestamp_datetime = datetime.strptime(device[3], '%Y-%m-%d %H:%M:%S')
            current_time = datetime.now()

            time_dff = current_time - timestamp_datetime

            # Extract hours, minutes, and seconds from the time difference
            hours, remainder = divmod(time_dff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            data["devices"].append({
                "in_use": True,
                "mac_address": device[0],
                "device_name": device[1],
                "device_desc": device[2],
                "time_since_start": f"{hours} hrs, {minutes} minutes",
                "user_fname": device[4],
                "user_lname": device[5]
            })
        # non_in_use_devices = dbo.get_deactivated_devices(cursor)
        # for device in non_in_use_devices:
        #     data["devices"].append({
        #         "in_use": False,
        #         "mac_address": device[0],
        #         "device_name": device[1],
        #         "device_desc": device[2],
        #         "end_time": device[3]
        #     })
        conn.commit()

    return render_template('home_dashboard.html', data=data)

@app.route('/devices/<mac_address>', methods=['GET'])
def device_view(mac_address: str):
    data = {}

    
    return render_template('device_template.html')

@app.route('/devices/logs', methods=['GET'])
def device_log_view():
    params = []
    logs = []
    devices = []
    
    # get query parameters
    device_addr = request.args.get("device_addr", default=None)
    start_time = request.args.get("datetime_from", default=None)
    end_time = request.args.get("datetime_to", default=None)
    checkout_id = request.args.get("checkout_id", default=None)
    if device_addr: params.append(("device_addr", device_addr))
    if start_time: params.append(("datetime_from", start_time))
    if end_time: params.append(("datetime_to", end_time))
    if checkout_id: params.append(("checkout_id", checkout_id))
    # params.append(("filter_topics", request.args.get("filter_topics", default="").split(',')))
    # params.append(("order_by_topics", request.args.get("order_by_topics", default="").split(',')))
    # params.append(("order_by_asc_or_desc", request.args.get("order_by_asc_or_desc", default="ASC")))


    logs_request_endpoint = build_request_to_self("/api/devices/logs")
    logs_request_endpoint_with_params = server_helpers.add_request_parameters(logs_request_endpoint, params)
    log_json_data = requests.get(logs_request_endpoint_with_params).json()

    for log in log_json_data["data"]:
        logs.append({
            "mac_address": log[0],
            "device_name": log[1],
            "device_type": log[2],
            "creation_time": log[3],
            "log_data": log[4],
            "checkout_id": log[5],
            "user_fname": log[6],
            "user_lname": log[7]
        })
    
    # get all devices 
    devices_request_endpoint = build_request_to_self("/api/registered-devices")
    device_json_data = requests.get(devices_request_endpoint).json()

    for device in device_json_data["data"]:
        devices.append({
            "mac_address": device[0],
            "device_name": device[1]
        })
    
    

    return render_template('log_page.html', devices=devices, logs=logs)


@app.route('/devices/checkout/<checkout_id>')
def checkout_view(checkout_id):
    return render_template("checkout_page.html")



@app.route('/ping', methods=['GET'])
def ping():
    return 'Hello from Python server!\n'


@app.route('/api/devices/logs', methods=["GET", "POST"])
def device_log_api():
    if request.method == "GET":
        # get query parameters
        device_addr = request.args.get("device_addr", default=None)
        date_from = request.args.get("datetime_from", default=None)
        date_to = request.args.get("datetime_to", default=None)
        # filter_topics = request.args.get("filter_topics", default="").split(',')
        # order_by_topics = request.args.get("order_by_topics", default="").split(',')
        # order_by_asc_or_desc = request.args.get("order_by_asc_or_desc", default="ASC")

        
        with app.app_context():
            conn = dbo.get_db()
            cursor = conn.cursor()

            logs = dbo.get_device_logs_by_parameters(
                cursor, device_addr, date_from, date_to) 
                # filter_topics, order_by_topics, order_by_asc_or_desc)
            
            conn.commit()
        return jsonify({'status': 'success', 'data': logs})
        
    elif request.method == "POST":
        pass

    return

# @app.route('/devices/<mac_address>/logs', methods=['POST'])
# def device_log_data():
#     '''Some things to possibly measure'''
    
#     return 

@app.route('/api/registered-devices', methods=["GET", "POST"])
def registered_devices():
    if request.method == "GET":
        devices = []

        with app.app_context():
            conn = dbo.get_db()
            cursor = conn.cursor()

            devices = dbo.get_all_devices(cursor)
            
            conn.commit()

        return jsonify({'status': 'success', 'data': devices})
    
    elif request.method == "POST":
        return



@app.route('/dog-tracker/mpu-motion6', methods=['POST'])
def dog_tracker_motion_data():
    try:
        data = request.json  # Assuming the data is sent as JSON
        print(data)

        print(MPU6050_Data(data))

        # motion_data = MPU6050_Data(**data)

        # db.add_dog_motion_data(motion_data)
        
        return jsonify({'status': 'success', 'message': 'Data received successfully'})

    except KeyError as e:
        # Handle missing keys in the request data
        return jsonify({'status': 'error', 'message': f'Missing key: {str(e)}'}), 400

    except Exception as e:
        # Handle other exceptions
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host=HOST, port=PORT, debug=DEBUG_MODE)
