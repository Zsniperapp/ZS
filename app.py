from flask import Flask, request, jsonify, render_template
from jupiter_swap import load_wallet, get_jupiter_quote, build_swap_transaction, Client, TxOpts, Finalized
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned
import base64
import sys

app = Flask(__name__)

# Configuration from jupiter_swap.py
RPC_URL = "RPC URL"
SOL_MINT = "So11111111111111111111111111111111111111112"
connection = Client(RPC_URL)
wallet = load_wallet()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/swap', methods=['POST'])
def swap():
    try:
        data = request.json
        print('Received swap request:', data)
        action = data['action']
        amount = float(data['amount'])
        token_address = data['tokenAddress']
        public_key = data['publicKey']

        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400

        from solders.pubkey import Pubkey
        try:
            Pubkey.from_string(token_address)
        except:
            return jsonify({'error': 'Invalid token address'}), 400

        input_mint = SOL_MINT if action == 'buy' else token_address
        output_mint = token_address if action == 'buy' else SOL_MINT

        decimals = 9 if input_mint == SOL_MINT else 6
        amount_base_units = int(amount * (10 ** decimals))

        quote_response = get_jupiter_quote(input_mint, output_mint, amount_base_units)
        swap_response = build_swap_transaction(quote_response, public_key)

        tx_bytes = base64.b64decode(swap_response['swapTransaction'])
        raw_tx = VersionedTransaction.from_bytes(tx_bytes)

        message = raw_tx.message
        message_bytes = to_bytes_versioned(message)
        sig = wallet.sign_message(message_bytes)

        signed_tx = VersionedTransaction.populate(message, [sig])
        signed_tx_bytes = bytes(signed_tx)

        opts = TxOpts(skip_preflight=True, max_retries=2, preflight_commitment=Finalized)
        tx_response = connection.send_raw_transaction(signed_tx_bytes, opts=opts)
        print('Transaction response:', tx_response)  # Debug log

        # Extract signature string from SendTransactionResp
        tx_signature_str = str(tx_response).split('Signature(')[1].split(')')[0]

        confirmation_details = {
            'signature': tx_signature_str
        }

        print('Swap successful:', confirmation_details)  # Debug log
        return jsonify(confirmation_details)
    except Exception as e:
        print('Swap error:', str(e))
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)