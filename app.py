from flask import Flask, request, jsonify, send_file
import requests
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.debug = True

NETWORK_APIS = {
    "bitcoin": "https://api.blockchair.com/bitcoin/dashboards/transaction/{txid}",
    "ethereum": "https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={txid}&apikey={api_key}",
    "binance": "https://api.bscscan.com/api?module=proxy&action=eth_getTransactionByHash&txhash={txid}&apikey={api_key}",
    "polygon": "https://api.polygonscan.com/api?module=proxy&action=eth_getTransactionByHash&txhash={txid}&apikey={api_key}",
    "tron": "https://api.trongrid.io/v1/transactions/{txid}",
    "xrp": "https://s1.ripple.com:51234", 
    "solana": "https://api.mainnet-beta.solana.com/",
    "cardano": "https://cardano-mainnet.blockfrost.io/api/v0/txs/{txid}",
    "algorand": "https://algoindexer.algoexplorerapi.io/v2/transactions/{txid}"
}

API_KEYS = {
    "ethereum": os.getenv("ETHERSCAN_API_KEY"),
    "binance": os.getenv("BSCSCAN_API_KEY"),
    "polygon": os.getenv("POLYGONSCAN_API_KEY"),
    "cardano": os.getenv("BLOCKFROST_API_KEY")
}

def convert_time(timestamp):
    try:
        return datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return "N/A"

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

def get_transaction_by_txid(txid):
    network = detect_network(txid)
    if network == "unknown":
        return {"TxID": txid, "Network": "Unknown", "Status": "Failed"}
    try:
        url = NETWORK_APIS[network].format(txid=txid, api_key=API_KEYS.get(network, ""))
        response = requests.get(url)
        data = response.json()

        if network in ["ethereum", "binance", "polygon"]:
            tx = data.get("result", {})
            return {
                "TxID": txid,
                "Network": network.capitalize(),
                "From": tx.get("from", "N/A"),
                "To": tx.get("to", "N/A"),
                "Amount": float(int(tx.get("value", "0"), 16)) / 1e18 if "value" in tx else "N/A",
                "Timestamp": "Unknown",
                "Fee": float(int(tx.get("gasPrice", "0"), 16)) / 1e18 if "gasPrice" in tx else "N/A",
                "Status": "Success"
            }
        elif network == "bitcoin":
            tx = data.get("data", {}).get(txid, {}).get("transaction", {})
            return {
                "TxID": txid,
                "Network": "Bitcoin",
                "From": "N/A",
                "To": "N/A",
                "Amount": tx.get("balance_change", "N/A"),
                "Timestamp": convert_time(tx.get("time")),
                "Fee": tx.get("fee", "N/A"),
                "Status": "Confirmed"
            }
    except Exception as e:
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
