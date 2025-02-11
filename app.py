from flask import Flask, request, jsonify, send_file
import requests
import pandas as pd
from web3 import Web3
import json
from datetime import datetime

app = Flask(__name__)

BLOCKCHAIN_EXPLORERS = [
    "https://api.blockchair.com/{}/dashboards/transaction/{}",
    "https://blockscout.com/{}/api?module=transaction&action=gettxinfo&txhash={}",
    "https://api.blockcypher.com/v1/{}/main/txs/{}",
    "https://api.trongrid.io/v1/transactions/{}",
    "https://s1.ripple.com:51234/"
]

EVM_NETWORKS = {
    "ethereum": "https://mainnet.infura.io/v3/YOUR_INFURA_API_KEY",
    "bsc": "https://bsc-dataseed.binance.org/",
    "polygon": "https://polygon-rpc.com/",
    "avalanche": "https://api.avax.network/ext/bc/C/rpc",
    "fantom": "https://rpc.ftm.tools/",
    "optimism": "https://mainnet.optimism.io/",
    "arbitrum": "https://arb1.arbitrum.io/rpc"
}

def convert_time(timestamp):
    try:
        return datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return "N/A"

def detect_network(txid):
    for explorer in BLOCKCHAIN_EXPLORERS:
        for network in ["bitcoin", "ethereum", "bsc", "polygon", "litecoin", "dogecoin", "tron", "xrpl"]:
            url = explorer.format(network, txid)
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if "error" not in data:
                    return network
    return None

def get_transaction_by_txid(txid):
    network = detect_network(txid)
    
    if network in EVM_NETWORKS:
        w3 = Web3(Web3.HTTPProvider(EVM_NETWORKS[network]))
        try:
            tx = w3.eth.get_transaction(txid)
            return {
                "TxID": txid,
                "Network": network,
                "From": tx["from"],
                "To": tx["to"],
                "Amount (ETH)": Web3.from_wei(tx["value"], "ether"),
                "Gas Fee": Web3.from_wei(tx["gasPrice"], "ether"),
                "Status": "Success"
            }
        except:
            return {"TxID": txid, "error": "Transaction not found"}

    for explorer in BLOCKCHAIN_EXPLORERS:
        url = explorer.format(network, txid)
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return {
                "TxID": txid,
                "Network": network,
                "Data": data
            }

    return {"TxID": txid, "error": "Transaction not found"}

@app.route("/transactions", methods=["POST"])
def get_multiple_transactions():
    try:
        data = request.json
        txids = data.get("txids", [])

        if not txids:
            return jsonify({"error": "Missing txids"}), 400

        transactions = [get_transaction_by_txid(txid) for txid in txids]
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
        return send_file("transactions.xlsx", as_attachment=True)
    except Exception as e:
        return jsonify({"error": "File not found", "details": str(e)}), 404

@app.route("/")
def home():
    return "Crypto API is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
