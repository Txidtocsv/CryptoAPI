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
    "cardano": os.getenv("BLOCKFROST_API_KEY")
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
        if network == "bitcoin":
            response = requests.get(f"{BLOCKCHAIR_API}bitcoin/dashboards/transaction/{txid}")
            data = response.json()["data"][txid]
            return {
                "TxID": txid,
                "Network": "Bitcoin",
                "From": data["inputs"][0]["recipient"] if "inputs" in data else "N/A",
                "To": data["outputs"][0]["recipient"] if "outputs" in data else "N/A",
                "Amount": data["outputs"][0]["value"] if "outputs" in data else "N/A",
                "Timestamp": convert_time(data.get("time", "0")),
                "Fee": data.get("fee", "N/A"),
                "Status": "Success"
            }
        elif network == "ethereum":
            response = requests.get(f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={txid}&apikey={API_KEYS['ethereum']}")
            data = response.json()["result"]
            return {
                "TxID": txid,
                "Network": "Ethereum",
                "From": data.get("from", "N/A"),
                "To": data.get("to", "N/A"),
                "Amount": data.get("value", "N/A"),
                "Timestamp": "N/A",  # Requires further conversion
                "Fee": data.get("gasPrice", "N/A"),
                "Status": "Success"
            }
        else:
            return {"TxID": txid, "Network": network, "Status": "Unsupported"}
    except:
        return {"error": "Internal error fetching transaction"}

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
