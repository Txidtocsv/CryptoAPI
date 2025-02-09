from flask import Flask, request, jsonify
import requests
import pandas as pd
from datetime import datetime

app = Flask(__name__)

def convert_time(timestamp):
    try:
        return datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return "N/A"

def get_transaction_by_txid(txid, network):
    if network == "ethereum":
        url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={txid}&apikey=YOUR_ETHERSCAN_API_KEY"
    elif network == "bitcoin":
        url = f"https://api.blockchair.com/bitcoin/dashboards/transaction/{txid}"
    elif network == "tron":
        url = f"https://api.trongrid.io/v1/transactions/{txid}"
    else:
        return None

    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if network == "ethereum":
            tx = data.get("result", {})
            return {
                "TxID": txid,
                "Date": "Unknown",
                "From": tx.get("from"),
                "To": tx.get("to"),
                "Amount (ETH)": float(int(tx.get("value", "0"), 16)) / 1e18,
                "Gas Fee (ETH)": float(int(tx.get("gasPrice", "0"), 16)) / 1e18,
                "Status": "Success"
            }
        elif network == "bitcoin":
            tx = data["data"][txid]["transaction"]
            return {
                "TxID": txid,
                "Date": convert_time(tx.get("time")),
                "Amount (BTC)": tx.get("balance_change"),
                "Fee (BTC)": tx.get("fee"),
                "Status": "Confirmed"
            }
        elif network == "tron":
            tx = data.get("data", [])[0]
            return {
                "TxID": txid,
                "Date": convert_time(tx.get("block_timestamp") / 1000),
                "From": tx.get("owner_address"),
                "To": tx.get("to_address"),
                "Amount (TRX)": float(tx.get("amount", 0)) / 1e6,
                "Status": "Success" if tx.get("confirmed") else "Pending"
            }
    return None

@app.route("/transactions", methods=["POST"])
def get_multiple_transactions():
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

