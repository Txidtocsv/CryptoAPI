from flask import Flask, request, jsonify, send_file
import requests
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)

GLOBAL_BLOCKCHAIN_APIS = [
    "https://chainid.network/chains.json",
    "https://rpc.ankr.com/multichain",
    "https://api.allchains.info/v1/chains",
    "https://api.blockchair.com",
    "https://1rpc.io"
]

def convert_time(timestamp):
    try:
        return datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return "N/A"

def detect_network(txid):
    for api in GLOBAL_BLOCKCHAIN_APIS:
        try:
            response = requests.get(f"{api}/transaction/{txid}")
            if response.status_code == 200:
                return response.json().get("network", "Unknown")
        except:
            continue
    return "Unknown"

def get_transaction_by_txid(txid):
    network = detect_network(txid)
    if network == "Unknown":
        return {"TxID": txid, "Network": network, "From": "N/A", "To": "N/A", "Amount": "N/A", "Timestamp": "N/A", "Fee": "N/A", "Status": "Failed"}
    
    try:
        response = requests.get(f"https://api.blockchair.com/{network}/dashboards/transaction/{txid}")
        data = response.json()
        tx = data.get("data", {}).get(txid, {}).get("transaction", {})
        
        return {
            "TxID": txid,
            "Network": network,
            "From": tx.get("sender", "N/A"),
            "To": tx.get("recipient", "N/A"),
            "Amount": tx.get("value", "N/A"),
            "Timestamp": convert_time(tx.get("time")),
            "Fee": tx.get("fee", "N/A"),
            "Status": "Confirmed" if tx.get("confirmations", 0) > 0 else "Pending"
        }
    except Exception as e:
        return {"TxID": txid, "Network": network, "Error": "Failed to fetch transaction details"}

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
