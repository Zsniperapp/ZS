document.addEventListener('DOMContentLoaded', () => {
    const swapForm = document.getElementById('swap-form');
    const swapButton = document.getElementById('swap-button');
    const resultDisplay = document.getElementById('result');
    const walletAddressDisplay = document.getElementById('wallet-address');

    walletAddressDisplay.textContent = 'Wallet: Using server-side wallet';

    swapForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const action = document.getElementById('action').value;
        const amount = document.getElementById('amount').value;
        const tokenAddress = document.getElementById('token-address').value;
        const publicKey = 'PUBLIC KEY';

        resultDisplay.textContent = 'Processing swap...';

        try {
            console.log('Sending swap request:', { action, amount, tokenAddress, publicKey });
            const response = await fetch('/swap', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action, amount, tokenAddress, publicKey })
            });
            const data = await response.json();

            if (response.ok) {
                resultDisplay.innerHTML = `
                    <strong>Swap Successful!</strong><br>
                    Transaction: <a href="https://solscan.io/tx/${data.signature}" target="_blank">https://solscan.io/tx/${data.signature}</a>
                `;
            } else {
                resultDisplay.textContent = `Error: ${data.error}`;
            }
        } catch (err) {
            console.error('Error:', err);
            resultDisplay.textContent = `Error: ${err.message}`;
        }
    });
});