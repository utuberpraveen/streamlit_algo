import json
import requests
from requests import get
import urllib3
import hashlib
import pyotp
from flask import Flask, request, jsonify, session,send_from_directory
from flask_cors import CORS

# Disable SSL warnings (use verify=True in production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Replace with a strong secret key
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Base URL for the Motilal Oswal API endpoints
API_BASE_URL = "https://openapi.motilaloswal.com"

# ---------------------------
# Helper Functions
# ---------------------------

def get_url(api_path):
    """
    Returns the complete URL for the given API path based on the base URL.
    """
    base_url = "https://openapi.motilaloswal.com/"
    endpoints = {
        "Login": "/rest/login/v4/authdirectapi",
        "Logout": "/rest/login/v1/logout",
        "GetProfile": "/rest/login/v1/getprofile",
        "OrderBook": "/rest/book/v1/getorderbook",
        "TradeBook": "/rest/book/v1/gettradebook",
        "GetPosition": "/rest/book/v1/getposition",
        "DPHolding": "/rest/report/v1/getdpholding",
        "PlaceOrder": "/rest/trans/v1/placeorder",
        "ModifyOrder": "/rest/trans/v2/modifyorder",
        "CancelOrder": "/rest/trans/v1/cancelorder",
        "ltadata": "/rest/report/v1/getltpdata",
        # Add other endpoints as needed...
    }
    return base_url + endpoints.get(api_path, "")

def build_headers(api_key, api_secret, auth_token=None, vendorinfo="", client_info={}):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": auth_token if auth_token else "",
        "User-Agent": "MOSL/V.1.1.0",
        "apikey": api_key,
        "apisecretkey": api_secret,
        "macaddress": "00:50:56:BD:F4:0B",
        "clientlocalip": "127.0.0.1",
        "sourceid": "WEB",
        "clientpublicip": "1.2.3.4",
        "vendorinfo": vendorinfo,
        "osname": "Windows",
        "osversion": "10",
        "installedappid": "123",
        "devicemodel": "vServer",
        "manufacturer": "Generic",
        "productname": "TraderApp",
        "productversion": "1",
        "latitude": "26.923974",
        "longitude": "75.826603",
        "sdkversion": ""
    }
    if client_info.get("sourceid", "").upper() == "WEB":
        headers["browsername"] = client_info.get("browsername", "Chrome")
        headers["browserversion"] = client_info.get("browserversion", "10")
    return headers

def send_api_request(url, payload, headers):
    try:
        print("URL", url)
        print("playload",payload)
        print("headers",headers)
        #response = requests.post(url, headers=headers, json=payload, verify=False, timeout=15)
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        print("response",response)
        if response.status_code == 200:
            json_data = response.json()
            print("response JSON:", json_data)  # Print the JSON content
            return json_data
        else:
            return {"error": response.status_code, "message": response.text}
    except Exception as e:
        return {"error": "Request Failed", "message": str(e)}

# ---------------------------
# API Endpoints
# ---------------------------

@app.route('/proxy', methods=['POST'])
def proxy():
    # Read the JSON payload from the incoming request.
    data = request.get_json(force=True)
    
    # Modify headers; update User-Agent and any other headers required.
    headers = {
        "User-Agent": "MOSL/V.1.1.0",
    }
    
    # Forward the request to the broker's API.
    try:
        broker_response = requests.post("https://openapi.motilaloswal.com//rest/login/v4/authdirectapi", data=json.dumps(payload), headers=headers)
    except Exception as e:
        return Response(str(e), status=500)
    
    # Return the broker's response to the caller.
    return Response(
        broker_response.content,
        status=broker_response.status_code,
        mimetype=broker_response.headers.get("Content-Type", "application/json")
    )


@app.route("/api/login", methods=["POST"])
def login():
    """
    Login endpoint.
    Expects JSON with: userid, password, appkey, 2FA, totp (optional), and client_info.
    The password is hashed using SHA-256 after concatenating with the appkey.
    """
    data = request.json
    user_id = data.get("userid")
    password = data.get("password")
    appkey = data.get("appkey")
    twofa = data.get("2FA")
    totp_from_request = data.get("totp")
    
    # Auto-generate TOTP if not provided. Replace 'YOUR_TOTP_SECRET' with your actual secret.
    totp_secret = "VXOULXLW5YT6O2ZO4MXRVWG4RCAUEFLH"
    totp = totp_from_request #if totp_from_request else pyotp.TOTP(totp_secret).now()
    
     # Concatenate password and appkey, then hash using SHA-256.
    combined = password + appkey
    hashed_password = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    
    login_url = get_url("Login")
    payload = {
        "userid": user_id,
        "password": hashed_password,
        "2FA": twofa,
        "totp": totp
    }
    
    # For headers, use appkey as API key; use a default API secret if needed.
    # The vendorinfo is set to the user_id (only for login as per your flow).
    api_key = appkey
    api_secret = ""  # Use your default API secret or leave as an empty string if not required.
    client_info = data.get("client_info", {"sourceid": "WEB"})
    headers = build_headers(api_key, api_secret, auth_token=None, vendorinfo=user_id, client_info=client_info)
    
    response = send_api_request(login_url, payload, headers)
    if "authtoken" in response:
        session["authtoken"] = response["authtoken"]
        return jsonify({"message": "Login successful", "authtoken": response["authtoken"]})
    else:
        return jsonify({"error": "Login failed", "details": response})

@app.route("/api/get-ltp", methods=["POST"])
def get_ltp():
    if "authtoken" not in session:
        return jsonify({"error": "Unauthorized", "message": "Please login first."}), 401

    data = request.json
    symbol = data.get("symbol")
    # Use your configured API key/secret here
    api_key = "your_api_key"
    api_secret = "your_api_secret"
    ltp_url = f"{API_BASE_URL}/getLTP"  # Replace with the actual endpoint

    client_info = data.get("client_info", {"sourceid": "WEB"})
    headers = build_headers(api_key, api_secret, session["authtoken"], vendorinfo="", client_info=client_info)
    payload = {"symbol": symbol}
    response = send_api_request(ltp_url, payload, headers)
    return jsonify(response)

@app.route("/api/place-order", methods=["POST"])
def place_order():
    if "authtoken" not in session:
        return jsonify({"error": "Unauthorized", "message": "Please login first."}), 401

    data = request.json
    symbol = data.get("symbol")
    quantity = data.get("quantity")
    price = data.get("price")
    api_key = "your_api_key"
    api_secret = "your_api_secret"
    order_url = f"{API_BASE_URL}/placeOrder"  # Replace with the actual order endpoint

    client_info = data.get("client_info", {"sourceid": "WEB"})
    headers = build_headers(api_key, api_secret, session["authtoken"], vendorinfo="", client_info=client_info)
    payload = {"symbol": symbol, "action": "BUY", "quantity": quantity, "price": price}
    response = send_api_request(order_url, payload, headers)
    return jsonify(response)

@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("authtoken", None)
    return jsonify({"message": "Logged out successfully"})

@app.route("/")
def index():
    # Serve test.html from the 'static' folder
    return send_from_directory("static", "test.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
