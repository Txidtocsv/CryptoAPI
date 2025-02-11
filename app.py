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
            url = f"https://blockscout.com/eth/mainnet/api?module=transaction&action=gettxinfo&txhash={txid}"
        elif network == "bitcoin":
            url = f"https://mempool.space/api/tx/{txid}"
        elif network == "tron":
            url = f"https://apilist.tronscan.org/api/transaction-info?hash={txid}"
        else:
            return {"error": "Unsupported network"}

        response = requests.get(url)
        data = response.json()

        print(f"🔍 API Response for {txid}: {data}")

        if "error" in data:
            return {"error": "Failed to fetch data"}

        if network == "ethereum":
            return {
                "TxID": txid,
                "From": data.get("result", {}).get("from", "N/A"),
                "To": data.get("result", {}).get("to", "N/A"),
                "Amount (ETH)": float(int(data.get("result", {}).get("value", "0"), 16)) / 1e18 if "value" in data.get("result", {}) else "N/A",
                "Status": "Success"
            }
        elif network == "bitcoin":
            return {
                "TxID": txid,
                "Date": convert_time(data.get("time", 0)),
                "Amount (BTC)": sum(output["value"] for output in data.get("vout", [])) / 1e8,
                "Fee (BTC)": data.get("fee", "N/A"),
                "Status": "Confirmed" if data.get("status", {}).get("confirmed", False) else "Pending"
            }
        elif network == "tron":
            return {
                "TxID": txid,
                "From": data.get("ownerAddress", "N/A"),
                "To": data.get("toAddress", "N/A"),
                "Amount (TRX)": float(data.get("amount", 0)) / 1e6 if "amount" in data else "N/A",
                "Status": "Success" if data.get("confirmed") else "Pending"
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
        return send_file(
            "transactions.xlsx",
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"error": "File not found", "details": str(e)}), 404


@app.route("/")
def home():
    return "Crypto API is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
