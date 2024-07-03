import json
import datetime
from eth_account import Account
from web3 import Web3
from web3 import exceptions as web3_exceptions


def say(message):
    now = datetime.datetime.now()
    print(
        f"[{now.year}-{now.month:02}-{now.day:02} "
        f"{now.hour:02}:{now.minute:02}:{now.second:02}] {message}"
    )


def load_or_create_addresses(
    addresses_file, ks_pass_dac=None, ks_pass_seq=None, ks_pass_agr=None,
    ks_pass_ctm=None
):
    try:
        f = open(addresses_file)
        addresses = json.load(f)
        say(
            f"Addresses loaded from {addresses_file}:\n"
            f"\tDAC: {addresses['DAC']['addr']}\n"
            f"\tSequencer: {addresses['Sequencer']['addr']}\n"
            f"\tAggregator: {addresses['Aggregator']['addr']}\n"
            f"\tClaimTX: {addresses['ClaimTX']['addr']}\n"
            f"\tDeployer: {addresses['Deployer']['addr']}"
        )
    except FileNotFoundError:
        say(f"No {addresses_file} file found, creating one.")
        Account.enable_unaudited_hdwallet_features()
        addresses = {
            "DAC": {"keystore_password": ks_pass_dac},
            "Deployer": {},
            "Sequencer": {"keystore_password": ks_pass_seq},
            "ClaimTX": {"keystore_password": ks_pass_ctm},
            "Aggregator": {"keystore_password": ks_pass_agr},
        }
        for addr in addresses.keys():
            (acct, addresses[addr]['mnemonic']) = \
                Account.create_with_mnemonic()
            addresses[addr]['addr'] = acct.address
            addresses[addr]['prvkey'] = acct.key.hex()

        print(addresses)
        f = open(addresses_file, "w")
        json.dump(addresses, f, indent=2)

    return addresses


def transfer(
    ep, chainid, src, src_prvkey, dst, eth_amount, gas_from_amount=False,
    full_amount=False, retries=3, gas_price_multiplier=1.0, nonce=None,
    wait=True
):
    web3 = Web3(Web3.HTTPProvider(ep))
    src = Web3.to_checksum_address(src)
    dst = Web3.to_checksum_address(dst)
    src_balance = web3.eth.get_balance(src)

    if full_amount:
        wei_amount = src_balance
    else:
        wei_amount = web3.to_wei(eth_amount, 'ether')

    gas = 21000
    gas_price = int(web3.eth.gas_price * gas_price_multiplier)

    if gas_from_amount:
        wei_amount -= gas*gas_price

    try:
        assert (src_balance >= (wei_amount + gas*gas_price))
    except AssertionError:
        say(
            "*** ERROR. Not enough balance on source account:"
            f"{web3.from_wei(src_balance, 'ether')} | "
            f"desired:{web3.from_wei(wei_amount + gas*gas_price, 'ether')}"
        )
        if full_amount and retries:
            return transfer(
                ep, chainid, src, src_prvkey, dst, eth_amount, gas_from_amount,
                full_amount, retries=retries-1,
                gas_price_multiplier=gas_price_multiplier+0.1
            )
        else:
            return None

    tx = {
        'chainId': chainid,
        'nonce': nonce or web3.eth.get_transaction_count(src),
        'to': dst,
        'value': wei_amount,
        'gas': gas,
        'gasPrice': gas_price,
    }
    # sign the transaction
    signed_tx = web3.eth.account.sign_transaction(tx, src_prvkey)

    # send transaction
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction).hex()
    say(
        f"Sending tx:{tx_hash} from:{src} to:{dst} "
        f"amount:{eth_amount} gas:{gas} gasPrice:{gas_price}"
    )
    if wait:
        try:
            web3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=120, poll_latency=0.4
            )
        except web3_exceptions.TimeExhausted:
            say(f"*** ERROR waiting for tx with tx_hash: {tx_hash}")
            if retries:
                say(f"*** Retrying {retries} more times")
                retries = retries - 1
                return transfer(
                    ep, chainid, src, src_prvkey, dst, eth_amount,
                    gas_from_amount, retries)
        finally:
            return tx_hash
    else:
        return tx_hash


def get_eth_balance(ep, addr):
    w = Web3(Web3.HTTPProvider(ep))
    balance = w.eth.get_balance(addr)
    return float(w.from_wei(balance, 'ether'))
