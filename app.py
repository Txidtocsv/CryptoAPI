from flask import Flask, request, jsonify, send_file
import requests
import pandas as pd
from datetime import datetime

app = Flask(__name__)

BLOCKCHAIR_API = "https://api.blockchair.com"
CHAINLIST_API = "https://chainid.network/chains.json"
ONERPC_API = "https://1rpc.io"

def convert_time(timestamp):
    try:
        return datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return "N/A"

def get_network_by_txid(txid):
    try:
        response = requests.get(CHAINLIST_API)
        chains = response.json()
        for chain in chains:
            if "explorers" in chain:
                for explorer in chain["explorers"]:
                    if explorer["url"].startswith("https://api"):
                        return chain["name"], explorer["url"].replace("{tx}", txid)
        return "Unknown", None
    except Exception as e:
        print(f"Error fetching network: {str(e)}")
        return "Unknown", None

def get_transaction_by_txid(txid):
    network, explorer_url = get_network_by_txid(txid)
    
    if network == "Unknown":
        return {"TxID": txid, "Network": "Unknown", "From": "N/A", "To": "N/A", "Amount": "N/A", "Status": "Failed"}

    try:
        response = requests.get(explorer_url)
        data = response.json()

        if "data" in data and txid in data["data"]:
            tx = data["data"][txid]
            return {
                "TxID": txid,
                "Network": network,
                "From": tx.get("sender", "N/A"),
                "To": tx.get("recipient", "N/A"),
                "Amount": tx.get("value", "N/A"),
                "Status": "Success" if tx.get("confirmations", 0) > 0 else "Pending"
            }

        return {"TxID": txid, "Network": network, "From": "N/A", "To": "N/A", "Amount": "N/A", "Status": "Failed"}
    
    except Exception as e:
        print(f"Error fetching transaction: {str(e)}")
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
        print(f"Error: {str(e)}")
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
