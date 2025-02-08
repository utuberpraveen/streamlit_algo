from flask import Flask, request, jsonify
import requests
import hashlib
import os

app = Flask(__name__)

# API Endpoints
MOTILAL_LOGIN_URL = "https://openapi.motilaloswal.com/rest/login/v4/authdirectapi"
GET_HOLDING_URL = "https://openapi.motilaloswal.com/rest/report/v1/getdpholding"

# Default Static Headers (these will be extended per request)
DEFAULT_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'User-Agent': 'MOSL/V.1.1.0',  # Mandatory hardcoded value
    'macaddress': 'b3:f6:ac:cf:be:6e',
    'clientlocalip': '127.0.1.1',
    'sourceid': 'WEB',
    'clientpublicip': '188.245.169.253',
    'osname': 'Linux',
    'osversion': '10.0.19044',
    'installedappid': 'a5ea3052-8fbc-11ef-bd8a-b3f6accfbe6e',
    'devicemodel': 'vServer',
    'manufacturer': 'Hetzner',
    'productname': 'Investor',
    'productversion': '1',
    'latitude': '50.4779',
    'longitude': '12.3713',
    'sdkversion': 'Python 2.1',
    'browsername': 'Chrome',
    'browserversion': '100'
}

def build_headers(api_key, vendorinfo="", auth_token=""):
    """
    Construct headers dynamically for API calls.
    - `api_key` (str): The user's API key (required).
    - `vendorinfo` (str): Vendor info if applicable (optional).
    - `auth_token` (str): If provided, will be included in `Authorization`.
    """
    headers = DEFAULT_HEADERS.copy()
    headers['apikey'] = api_key
    headers['vendorinfo'] = vendorinfo  # May be empty for some API calls
    if auth_token:
        headers['Authorization'] = auth_token  # Used for authenticated calls
    return headers

@app.route('/login', methods=['POST'])
def login():
    """
    Login to Motilal Oswal API.
    Expected JSON payload:
    {
        "userid": "user123",
        "password": "password",
        "2FA": "20/04/1989",
        "totp": "",
        "apikey": "your_api_key",
        "vendorinfo": "BGRKA1202"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "FAILURE", "message": "Missing JSON payload"}), 400

    userid = data.get("userid")
    raw_password = data.get("password")
    two_fa = data.get("2FA")
    totp = data.get("totp", "")
    user_apikey = data.get("apikey")
    vendorinfo = data.get("vendorinfo", "")

    if not userid or not raw_password or not two_fa or not user_apikey:
        return jsonify({"status": "FAILURE", "message": "Missing required parameters"}), 400

    # Create hashed password: SHA-256(raw_password + APIKey)
    hashed_password = hashlib.sha256((raw_password + user_apikey).encode()).hexdigest()

    # Build login payload
    payload = {
        "userid": userid,
        "password": hashed_password,
        "2FA": two_fa
    }
    if totp:
        payload["totp"] = totp

    # Build headers dynamically
    headers = build_headers(user_apikey, vendorinfo)

    try:
        # Send API request to Motilal Oswal
        response = requests.post(MOTILAL_LOGIN_URL, json=payload, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "FAILURE", "message": str(e)}), 500

    return jsonify(response.json()), response.status_code

@app.route('/get_holding', methods=['POST'])
def get_holding():
    """
    Fetch user holdings from Motilal Oswal API.
    Expected JSON payload:
    {
        "clientcode": "client123",
        "auth_token": "token_received_from_login",
        "apikey": "your_api_key",
        "vendorinfo": ""
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "FAILURE", "message": "Missing JSON payload"}), 400

    clientcode = data.get("clientcode")
    auth_token = data.get("auth_token")
    user_apikey = data.get("apikey")
    vendorinfo = data.get("vendorinfo", "")

    if not clientcode or not auth_token or not user_apikey:
        return jsonify({"status": "FAILURE", "message": "Missing required parameters"}), 400

    # Build headers with authentication token
    headers = build_headers(user_apikey, vendorinfo, auth_token)

    # Build payload for holdings request
    payload = {
        "clientcode": clientcode
    }

    try:
        # Send API request to get holdings
        response = requests.post(GET_HOLDING_URL, json=payload, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "FAILURE", "message": str(e)}), 500

    return jsonify(response.json()), response.status_code

if __name__ == '__main__':
    app.run(debug=True)
