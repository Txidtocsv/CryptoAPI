from flask import Flask, request, jsonify, send_file
import requests
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.debug = True

CHAINLIST_API = "https://chainid.network/chains.json"
BLOCKCHAIR_API = "https://api.blockchair.com/"
ALLCHAINS_API = "https://api.allchains.info/v1/chains"

API_KEYS = {
    "ethereum": os.getenv("ETHERSCAN_API_KEY"),
    "bitcoin": os.getenv("BLOCKCHAIR_API_KEY"),
    "binance": os.getenv("BSCSCAN_API_KEY"),
    "polygon": os.getenv("POLYGONSCAN_API_KEY"),
    "cardano": os.getenv("BLOCKFROST_API_KEY"),
    "solana": os.getenv("SOLANA_API_KEY"),
    "tron": os.getenv("TRONGRID_API_KEY"),
    "xrp": os.getenv("XRPL_API_KEY")
}

def get_chain_data():
    try:
        response = requests.get(CHAINLIST_API)
        return response.json()
    except:
        return []

def detect_network(txid):
    if txid.startswith("0x") and len(txid) == 66:
        return "ethereum"
    elif len(txid) == 64:
        return "bitcoin"
    elif txid.startswith("T"):
        return "tron"
    elif txid.startswith("r"):
        return "xrp"
    elif txid.startswith("S"):
        return "solana"
    else:
        return "unknown"

def convert_time(timestamp):
    try:
        return datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return "N/A"

def get_transaction_by_txid(txid):
    network = detect_network(txid)
    if network == "unknown":
        return {"TxID": txid, "Network": "Unknown", "Status": "Failed"}
    try:
        api_url = f"{BLOCKCHAIR_API}{network}/dashboards/transaction/{txid}"
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()["data"][txid]
            return {
                "TxID": txid,
                "Network": network.capitalize(),
                "From": data.get("inputs", [{}])[0].get("recipient", "N/A"),
                "To": data.get("outputs", [{}])[0].get("recipient", "N/A"),
                "Amount": data.get("outputs", [{}])[0].get("value", "N/A"),
                "Timestamp": convert_time(data.get("transaction", {}).get("time", "0")),
                "Fee": data.get("transaction", {}).get("fee", "N/A"),
                "Status": "Success"
            }
    except:
        return {"TxID": txid, "Network": network.capitalize(), "Status": "Failed"}

@app.route("/transactions", methods=["POST"])
def get_multiple_transactions():
    data = request.json
    txids = data.get("txids", [])
    transactions = [get_transaction_by_txid(txid) for txid in txids]
    transactions = [tx for tx in transactions if tx]

    if not transactions:
        return jsonify({"message": "No transactions found"}), 404

    df = pd.DataFrame(transactions)
    file_path = "transactions.xlsx"
    df.to_excel(file_path, index=False)
    
    return jsonify({"message": "File generated", "file": file_path})

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
