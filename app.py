from flask import Flask, request, jsonify, send_file
import requests
import pandas as pd
from datetime import datetime

app = Flask(__name__)

BLOCKCHAIR_API_URL = "https://api.blockchair.com"

def convert_time(timestamp):
    try:
        return datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return "N/A"

def detect_network(txid):
    try:
        response = requests.get(f"{BLOCKCHAIR_API_URL}/ethereum/dashboards/transaction/{txid}")
        if response.status_code == 200:
            return "Ethereum Mainnet"
        
        response = requests.get(f"{BLOCKCHAIR_API_URL}/bitcoin/dashboards/transaction/{txid}")
        if response.status_code == 200:
            return "Bitcoin"
        
        response = requests.get(f"{BLOCKCHAIR_API_URL}/dash/dashboards/transaction/{txid}")
        if response.status_code == 200:
            return "Dash"
        
        response = requests.get(f"{BLOCKCHAIR_API_URL}/litecoin/dashboards/transaction/{txid}")
        if response.status_code == 200:
            return "Litecoin"
        
        return "Unknown"
    except:
        return "Unknown"

def get_transaction_by_txid(txid):
    network = detect_network(txid)
    if network == "Unknown":
        return {"TxID": txid, "Network": "Unknown", "From": "N/A", "To": "N/A", "Amount": "N/A", "Status": "Failed"}

    try:
        response = requests.get(f"{BLOCKCHAIR_API_URL}/ethereum/dashboards/transaction/{txid}")
        data = response.json()
        
        tx_data = data["data"][txid]["transaction"]

        return {
            "TxID": txid,
            "Network": network,
            "From": tx_data.get("sender", "N/A"),
            "To": tx_data.get("recipient", "N/A"),
            "Amount": float(tx_data.get("value", 0)) / 1e18 if "value" in tx_data else "N/A",
            "Status": "Success" if not tx_data.get("failed") else "Failed"
        }
    except Exception as e:
        return {"TxID": txid, "Network": network, "From": "N/A", "To": "N/A", "Amount": "N/A", "Status": "Failed"}

@app.route("/transactions", methods=["POST"])
def get_multiple_transactions():
    try:
        data = request.json
        txids = data.get("txids", [])

        if not txids:
            return jsonify({"error": "Missing txids"}), 400

        transactions = [get_transaction_by_txid(txid) for txid in txids]

        df = pd.DataFrame(transactions)
        file_path = "transactions.xlsx"
        df.to_excel(file_path, index=False)

        return jsonify({"message": "File generated", "file": file_path})
    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route("/download", methods=["GET"])
def download_file():
    try:
        return send_file("transactions.xlsx", as_attachment=True)
    except Exception as e:
        return jsonify({"error": "File not found", "details": str(e)}), 404

@app.route("/")
def home():
    return "Crypto API is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
