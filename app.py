from flask import Flask, request, jsonify, send_file
import requests
import pandas as pd
import os

app = Flask(__name__)

CHAINLIST_API = os.getenv("CHAINLIST_API")
ANKR_API = os.getenv("ANKR_API")
ALLCHAINS_API = os.getenv("ALLCHAINS_API")
BLOCKCHAIR_API = os.getenv("BLOCKCHAIR_API")
ONE_RPC_API = os.getenv("ONE_RPC_API")

def get_chain_info():
    try:
        response = requests.get(CHAINLIST_API)
        chains = response.json()
        return {str(chain["chainId"]): chain for chain in chains}
    except Exception as e:
        return {}

CHAIN_INFO = get_chain_info()

def detect_network(txid):
    for chain_id, chain in CHAIN_INFO.items():
        if chain.get("explorers"):
            for explorer in chain["explorers"]:
                api_url = explorer.get("url")
                if api_url:
                    tx_url = f"{api_url}/tx/{txid}"
                    response = requests.get(tx_url)
                    if response.status_code == 200:
                        return chain["name"], chain_id
    return "Unknown", None

def fetch_transaction_data(txid):
    network, chain_id = detect_network(txid)
    if network == "Unknown":
        return {"TxID": txid, "Error": "Network not found"}

    try:
        response = requests.post(ANKR_API, json={"jsonrpc": "2.0", "method": "eth_getTransactionByHash", "params": [txid], "id": 1})
        data = response.json().get("result", {})
        return {
            "TxID": txid,
            "Network": network,
            "From": data.get("from", "N/A"),
            "To": data.get("to", "N/A"),
            "Amount": int(data.get("value", "0"), 16) / 1e18 if "value" in data else "N/A",
            "Status": "Success" if data else "Failed"
        }
    except Exception as e:
        return {"TxID": txid, "Error": str(e)}

@app.route("/transactions", methods=["POST"])
def get_multiple_transactions():
    try:
        data = request.json
        txids = data.get("txids", [])

        if not txids:
            return jsonify({"error": "Missing txids"}), 400

        transactions = [fetch_transaction_data(txid) for txid in txids]

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
