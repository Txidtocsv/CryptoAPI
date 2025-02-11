from flask import Flask, request, jsonify, send_file
import requests
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.debug = True

CHAINLIST_API = "https://chainid.network/chains.json"
BLOCKCHAIR_API = "https://api.blockchair.com/{network}/dashboards/transaction/{txid}"
ANKR_API = "https://rpc.ankr.com/multichain"
ALLCHAINS_API = "https://api.allchains.info/v1/chains"

API_KEYS = {
    "etherscan": os.getenv("ETHERSCAN_API_KEY"),
    "bscscan": os.getenv("BSCSCAN_API_KEY"),
    "polygonscan": os.getenv("POLYGONSCAN_API_KEY")
}

def convert_time(timestamp):
    try:
        return datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return "N/A"

def detect_network(txid):
    try:
        response = requests.get(ALLCHAINS_API)
        chains = response.json()
        for chain in chains:
            url = BLOCKCHAIR_API.format(network=chain["name"].lower(), txid=txid)
            res = requests.get(url)
            if res.status_code == 200:
                return chain["name"].lower()
    except:
        return "unknown"
    return "unknown"

def get_transaction_by_txid(txid):
    network = detect_network(txid)
    if network == "unknown":
        return {"TxID": txid, "Network": "Unknown", "From": "N/A", "To": "N/A", "Amount": "N/A", "Timestamp": "N/A", "Fee": "N/A", "Status": "Failed"}
    
    url = BLOCKCHAIR_API.format(network=network, txid=txid)
    response = requests.get(url)
    data = response.json()
    tx = data.get("data", {}).get(txid, {}).get("transaction", {})
    
    return {
        "TxID": txid,
        "Network": network.capitalize(),
        "From": tx.get("sender", "N/A"),
        "To": tx.get("recipient", "N/A"),
        "Amount": tx.get("value", "N/A"),
        "Timestamp": convert_time(tx.get("time")),
        "Fee": tx.get("fee", "N/A"),
        "Status": "Confirmed" if tx else "Failed"
    }

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
