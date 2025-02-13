from flask import Flask, request, send_file
import requests
import pandas as pd
from io import BytesIO

app = Flask(__name__)

NETWORKS = {
    "ethereum": {
        "chainlist": "https://chainid.network/chains.json",
        "ankr": "https://rpc.ankr.com/multichain",
        "blockchair": "https://api.blockchair.com/ethereum/dashboards/transaction/"
    },
    "bitcoin": {
        "blockchair": "https://api.blockchair.com/bitcoin/dashboards/transaction/"
    },
    "binance": {
        "chainlist": "https://chainid.network/chains.json",
        "ankr": "https://rpc.ankr.com/multichain",
        "allchains": "https://api.allchains.info/v1/chains"
    },
    "polygon": {
        "chainlist": "https://chainid.network/chains.json",
        "ankr": "https://rpc.ankr.com/multichain",
        "allchains": "https://api.allchains.info/v1/chains"
    }
}

def get_transaction_data(network, txid):
    result = None
    if network in NETWORKS:
        for api, url in NETWORKS[network].items():
            try:
                if api == "blockchair":
                    response = requests.get(f"{url}{txid}?limit=1")
                    data = response.json()["data"][txid]
                    result = {
                        "txid": txid,
                        "network": network,
                        "from": data["sender"],
                        "to": data["recipient"],
                        "value": data["value"],
                        "fee": data["fee"],
                        "timestamp": data["time"],
                        "status": "Success" if data["success"] else "Failed"
                    }
                    break
            except:
                pass
    return result or {"txid": txid, "status": "Unknown"}

@app.route('/', methods=['POST'])
def get_transactions():
    txids = request.json["txids"]
    data = []

    for txid in txids:
        if txid.startswith("0x"):
            network = "ethereum"
        elif len(txid) == 64:
            network = "bitcoin"
        elif txid.startswith("0x38"):
            network = "binance"
        elif txid.startswith("0x"):
            network = "polygon"  
        else:
            network = None

        if network:
            data.append(get_transaction_data(network, txid))
        else:
            data.append({"txid": txid, "status": "Unsupported network"})

    df = pd.DataFrame(data)

    excel_file = BytesIO()
    writer = pd.ExcelWriter(excel_file, engine='openpyxl')
    df.to_excel(writer, index=False)
    writer.save()
    excel_file.seek(0)

    return send_file(excel_file, download_name='transactions.xlsx', as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
