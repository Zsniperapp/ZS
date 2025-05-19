import json
import sys
import base64
import requests
from solana.rpc.api import Client
from solana.rpc.commitment import Finalized
from solana.rpc.types import TxOpts
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.signature import Signature
from solders.message import to_bytes_versioned

# Configuration
RPC_URL = "RPC URL"
WALLET_FILE = "wallet.json" # Optional
JUPITER_QUOTE_API = "https://lite-api.jup.ag/swap/v1/quote"
JUPITER_SWAP_API = "https://lite-api.jup.ag/swap/v1/swap"
SOL_MINT = "So11111111111111111111111111111111111111112"

# Load wallet
def load_wallet():
    try:
        with open(WALLET_FILE, 'r') as f:
            keypair_data = json.load(f)
        return Keypair.from_bytes(bytes(keypair_data))
    except Exception as e:
        print(f"Error loading wallet: {e}")
        sys.exit(1)

# Get Jupiter Quote
def get_jupiter_quote(input_mint, output_mint, amount, dynamic_slippage=True):
    try:
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "restrictIntermediateTokens": "true",
            "dynamicSlippage": str(dynamic_slippage).lower(),
        }
        response = requests.get(JUPITER_QUOTE_API, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching quote: {e}")
        raise

# Build Jupiter Swap Transaction
def build_swap_transaction(quote_response, user_public_key):
    try:
        payload = {
            "quoteResponse": quote_response,
            "userPublicKey": str(user_public_key),
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "dynamicSlippage": True,
            "prioritizationFeeLamports": {
                "priorityLevelWithMaxLamports": {
                    "maxLamports": 10000000,
                    "global": False,
                    "priorityLevel": "veryHigh"
                }
            }
        }
        response = requests.post(JUPITER_SWAP_API, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error building swap transaction: {e}")
        raise

# Send Transaction
def send_swap_transaction(swap_response, wallet, connection):
    try:
        # Deserialize base64 Jupiter tx
        tx_bytes = base64.b64decode(swap_response["swapTransaction"])
        raw_tx = VersionedTransaction.from_bytes(tx_bytes)

        # Sign message manually
        message = raw_tx.message
        message_bytes = to_bytes_versioned(message)
        sig = wallet.sign_message(message_bytes)

        # Populate tx with signature
        signed_tx = VersionedTransaction.populate(message, [sig])
        signed_tx_bytes = bytes(signed_tx)

        # Send to Solana
        opts = TxOpts(skip_preflight=True, max_retries=2, preflight_commitment=Finalized)
        tx_signature = connection.send_raw_transaction(signed_tx_bytes, opts=opts)

        # Confirm
        confirmation = connection.confirm_transaction(tx_signature, commitment=Finalized)
        if confirmation.value.err:
            raise Exception(f"Transaction failed: {confirmation.value.err}\nhttps://solscan.io/tx/{tx_signature}")

        print(f"Transaction successful: https://solscan.io/tx/{tx_signature}")
        return tx_signature
    except Exception as e:
        print(f"Error sending transaction: {e}")
        raise

# Execute Swap
def execute_swap(input_mint, output_mint, amount, wallet, connection):
    # Use 1e9 if input mint is SOL, otherwise 1e6 (e.g., USDC)
    decimals = 9 if input_mint == SOL_MINT else 6
    amount_base_units = int(amount * (10 ** decimals))

    quote_response = get_jupiter_quote(input_mint, output_mint, amount_base_units)
    swap_response = build_swap_transaction(quote_response, wallet.pubkey())
    return send_swap_transaction(swap_response, wallet, connection)

# Parse CLI args
def parse_command(args):
    if len(args) != 5 or args[1] not in ["buy", "sell"] or args[3].lower() != "sol":
        print("Usage: python jupiter_swap.py <buy|sell> <amount> SOL <token_address>")
        sys.exit(1)

    action = args[1].lower()
    try:
        amount = float(args[2])
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        print("Invalid amount.")
        sys.exit(1)

    try:
        token_address = args[4]
        Pubkey.from_string(token_address)
    except Exception:
        print("Invalid token address.")
        sys.exit(1)

    return action, amount, token_address

# Main entry
def main():
    action, amount, token_address = parse_command(sys.argv)
    wallet = load_wallet()
    print(f"Using wallet: {wallet.pubkey()}")
    connection = Client(RPC_URL)

    input_mint = SOL_MINT if action == "buy" else token_address
    output_mint = token_address if action == "buy" else SOL_MINT

    try:
        signature = execute_swap(input_mint, output_mint, amount, wallet, connection)
        print(f"Swap completed: {signature}")
    except Exception as e:
        print(f"Swap failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
