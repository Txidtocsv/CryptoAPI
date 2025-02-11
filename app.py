from flask import Flask, request, jsonify, send_file
import requests
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)

NETWORK_APIS = {
    "ethereum": "https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={txid}&apikey={api_key}",
    "bitcoin": "https://api.blockchair.com/bitcoin/dashboards/transaction/{txid}",
    "tron": "https://api.trongrid.io/v1/transactions/{txid}",
    "binance": "https://api.bscscan.com/api?module=proxy&action=eth_getTransactionByHash&txhash={txid}&apikey={api_key}",
    "polygon": "https://api.polygonscan.com/api?module=proxy&action=eth_getTransactionByHash&txhash={txid}&apikey={api_key}",
    "solana": "https://api.mainnet-beta.solana.com/",  # Solana requires a different approach
}

API_KEYS = {
    "ethereum": os.getenv("ETHERSCAN_API_KEY"),
    "binance": os.getenv("BSCSCAN_API_KEY"),
    "polygon": os.getenv("POLYGONSCAN_API_KEY"),
}

def convert_time(timestamp):
    try:
        return datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return "N/A"

def get_transaction_by_txid(txid, network):
    try:
        if network not in NETWORK_APIS:
            return {"error": "Unsupported network"}
        
        url = NETWORK_APIS[network].format(txid=txid, api_key=API_KEYS.get(network, ""))
        response = requests.get(url)
        data = response.json()
        
        if network == "ethereum" or network == "binance" or network == "polygon":
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
        elif network == "tron":
            tx = data.get("data", [{}])[0]
            return {
                "TxID": txid,
                "Network": "Tron",
                "From": tx.get("owner_address", "N/A"),
                "To": tx.get("to_address", "N/A"),
                "Amount": float(tx.get("amount", 0)) / 1e6 if "amount" in tx else "N/A",
                "Timestamp": convert_time(tx.get("block_timestamp", 0) / 1000),
                "Fee": "N/A",
                "Status": "Success" if tx.get("confirmed") else "Pending"
            }
    except Exception as e:
        return {"error": "Internal error fetching transaction"}

@app.route("/transactions", methods=["POST"])
def get_multiple_transactions():
    try:
        data = request.json
        txids = data.get("txids", [])
        network = data.get("network")
        
        if not txids or not network:
            return jsonify({"error": "Missing txids or network"}), 400
        
        transactions = [get_transaction_by_txid(txid, network) for txid in txids]
        transactions = [tx for tx in transactions if tx]
        
        if not transactions:
            return jsonify({"message": "No transactions found"}), 404
        
        df = pd.DataFrame(transactions)
        file_path = "transactions.xlsx"
        df.to_excel(file_path, index=False)
        
        return jsonify({"message": "File generated", "file": file_path})
    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route("/download", methods=["GET"])
def download_file():
    try:
        file_path = "transactions.xlsx"
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
        return send_file(file_path, as_attachment=True, download_name="transactions.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return jsonify({"error": "File not found", "details": str(e)}), 404

@app.route("/")
def home():
    return "Crypto API is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
