from flask import Flask, request, jsonify, send_file
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
    try:
        print(f"Fetching transaction {txid} from {network}")
        if network == "ethereum":
            url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={txid}&apikey=YOUR_ETHERSCAN_API_KEY"
        elif network == "bitcoin":
            url = f"https://api.blockchair.com/bitcoin/dashboards/transaction/{txid}"
        elif network == "tron":
            url = f"https://api.trongrid.io/v1/transactions/{txid}"
        else:
            return {"error": "Unsupported network"}

        response = requests.get(url)
        data = response.json()

        print(f"🔍 API Response for {txid}: {data}")

        if isinstance(data, str):  
            return {"error": "Invalid response format from API"}

        if network == "ethereum":
            tx = data.get("result", {})
            return {
                "TxID": txid,
                "Date": "Unknown",
                "From": tx.get("from", "N/A"),
                "To": tx.get("to", "N/A"),
                "Amount (ETH)": float(int(tx.get("value", "0"), 16)) / 1e18 if "value" in tx else "N/A",
                "Gas Fee (ETH)": float(int(tx.get("gasPrice", "0"), 16)) / 1e18 if "gasPrice" in tx else "N/A",
                "Status": "Success"
            }
        elif network == "bitcoin":
            tx = data.get("data", {}).get(txid, {}).get("transaction", {})
            return {
                "TxID": txid,
                "Date": convert_time(tx.get("time")),
                "Amount (BTC)": tx.get("balance_change", "N/A"),
                "Fee (BTC)": tx.get("fee", "N/A"),
                "Status": "Confirmed"
            }
        elif network == "tron":
            tx = data.get("data", [{}])[0]
            return {
                "TxID": txid,
                "Date": convert_time(tx.get("block_timestamp", 0) / 1000),
                "From": tx.get("owner_address", "N/A"),
                "To": tx.get("to_address", "N/A"),
                "Amount (TRX)": float(tx.get("amount", 0)) / 1e6 if "amount" in tx else "N/A",
                "Status": "Success" if tx.get("confirmed") else "Pending"
            }

    except Exception as e:
        print(f"❌ ERROR in get_transaction_by_txid: {str(e)}")
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
        print(f"❌ ERROR: {str(e)}")
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
