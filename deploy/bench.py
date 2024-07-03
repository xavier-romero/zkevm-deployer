import os
import time
import psycopg2
from eth_account import Account
from web3 import Web3
from utils import load_or_create_addresses, say


chainid = int(os.getenv('CHAINID'))
addresses_file = os.getenv('ADDRESSES_FILE')
addresses = load_or_create_addresses(addresses_file)

transactions_to_send = 2000
l2_ep = "http://localhost:8545"

deployment_addr = addresses['Deployment']['addr']
deployment_prvkey = addresses['Deployment']['prvkey']

pooldb = {
    'database': 'pool_db',
    'host': 'localhost',
    'port': 5555,
    'password': 'pool_password',
    'user': 'pool_user',
    'connect_timeout': 3,
    'options': '-c statement_timeout=5000'
}
sql = "select status, count(status) from pool.transaction group by status;"
conn = psycopg2.connect(**pooldb)
cur = conn.cursor()

Account.enable_unaudited_hdwallet_features()
addresses = []
for i in range(transactions_to_send):
    acct = Account.create()
    addresses.append((acct.address, acct.key.hex()))

w = Web3(Web3.HTTPProvider(l2_ep))
wei_amount = w.to_wei(0.01, 'ether')
gas = 21000
gas_price = w.eth.gas_price

cur.execute(sql)
results = cur.fetchall()
for result in results:
    print(f"Pool tx {result[0]}: {result[1]}")

transactions = []
nonce = w.eth.get_transaction_count(deployment_addr)
start = time.time()
for i in range(transactions_to_send):
    tx = {
        'chainId': chainid,
        'nonce': nonce + i,
        'to': addresses[i][0],
        'value': wei_amount,
        'gas': gas,
        'gasPrice': gas_price,
    }
    signed_tx = w.eth.account.sign_transaction(tx, deployment_prvkey)
    transactions.append(
        w.eth.send_raw_transaction(signed_tx.rawTransaction).hex()
    )
elapsed = time.time() - start
say(
    f"Sent {transactions_to_send} tx in {elapsed} seconds "
    f"({round(transactions_to_send/elapsed, 2)}tps)"
)

for i in range(transactions_to_send):
    w.eth.wait_for_transaction_receipt(
        transactions[i], timeout=180, poll_latency=0.1
    )
elapsed = time.time() - start
say(
    f"Confirmed {transactions_to_send} tx in {elapsed} seconds "
    f"({round(transactions_to_send/elapsed, 2)}tps)"
)

pendint_tx = True
while pendint_tx:
    cur.execute(sql)
    results = cur.fetchall()
    pendint_tx = False
    for result in results:
        print(f"Tx {result[0]}: {result[1]}")
        if result[0] != 'selected':
            pending_tx = True
