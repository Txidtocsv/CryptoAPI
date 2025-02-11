from flask import Flask, request, jsonify, send_file
import requests
import pandas as pd
from datetime import datetime

app = Flask(__name__)

CHAINLIST_API = "https://chainid.network/chains.json"
BLOCKCHAIR_API = "https://api.blockchair.com"


def get_all_chains():
    try:
        response = requests.get(CHAINLIST_API)
        if response.status_code == 200:
            return {str(chain["chainId"]): chain for chain in response.json()}
        return {}
    except:
        return {}


def identify_network(txid):
    try:
        chains = get_all_chains()
        for chain_id, chain_info in chains.items():
            explorer_url = chain_info.get("explorers", [{}])[0].get("url", "")
            if explorer_url:
                response = requests.get(f"{explorer_url}/tx/{txid}")
                if response.status_code == 200:
                    return chain_info["name"]
        return "Unknown"
    except:
        return "Unknown"


def get_transaction_data(txid, network):
    try:
        if "Ethereum" in network:
            url = f"{BLOCKCHAIR_API}/ethereum/dashboards/transaction/{txid}"
        elif "Bitcoin" in network:
            url = f"{BLOCKCHAIR_API}/bitcoin/dashboards/transaction/{txid}"
        elif "Tron" in network:
            url = f"https://api.trongrid.io/v1/transactions/{txid}"
        else:
            return {"error": "Unsupported network"}

        response = requests.get(url)
        if response.status_code != 200:
            return {"error": "Transaction not found"}
        data = response.json()
        return {
            "TxID": txid,
            "Network": network,
            "From": data.get("data", {}).get(txid, {}).get("transaction", {}).get("sender", "N/A"),
            "To": data.get("data", {}).get(txid, {}).get("transaction", {}).get("recipient", "N/A"),
            "Amount": data.get("data", {}).get(txid, {}).get("transaction", {}).get("value", "N/A"),
            "Status": "Success" if data else "Failed"
        }
    except:
        return {"error": "Internal error fetching transaction"}


@app.route("/transactions", methods=["POST"])
def get_multiple_transactions():
    try:
        data = request.json
        txids = data.get("txids", [])
        if not txids:
            return jsonify({"error": "Missing txids"}), 400

        transactions = []
        for txid in txids:
            network = identify_network(txid)
            tx_data = get_transaction_data(txid, network)
            transactions.append(tx_data)

        df = pd.DataFrame(transactions)
        file_path = "transactions.xlsx"
        df.to_excel(file_path, index=False)

        return jsonify({"message": "File generated", "file": file_path})
    except:
        return jsonify({"error": "Internal Server Error"}), 500


@app.route("/download", methods=["GET"])
def download_file():
    try:
        return send_file("transactions.xlsx", as_attachment=True)
    except:
        return jsonify({"error": "File not found"}), 404


@app.route("/")
def home():
    return "Crypto API is running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
