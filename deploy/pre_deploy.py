import os
import sys
import json
import fileinput
import secrets
from requests import get
from web3 import Web3
from utils import load_or_create_addresses, say, transfer, get_eth_balance
from time import sleep

infura_key = os.getenv('INFURA_KEY')
l1_ep = os.getenv('L1_EP')
funded_account = os.getenv('FUNDED_ACCOUNT')
funded_prvkey = os.getenv('FUNDED_PRVKEY')
output = os.getenv('OUTPUT_DIR')
deployment_helper = os.getenv('FILE_DEPLOYMENT_HELPER')
addresses_file = os.getenv('ADDRESSES_FILE')
chainid = os.getenv('CHAINID')
network_name = os.getenv('NETWORK_NAME')
deployer_balance_desired = float(os.getenv('DEPLOYER_BALANCE'))
aggregator_balance_desired = float(os.getenv('AGGREGATOR_BALANCE'))
sequencer_balance_desired = float(os.getenv('SEQUENCER_BALANCE'))
real_verifier = True
real_verifier_str = os.getenv('REAL_VERIFIER')
if real_verifier_str in ('0', 'false', 'False'):
    real_verifier = False
is_validium = True
is_validium = os.getenv('IS_VALIDIUM')
if is_validium in ('0', 'false', 'False'):
    is_validium = False
network = os.getenv('NETWORK')
forkid = int(os.getenv('FORKID'))
etherscan_apikey = os.getenv('ETHERSCAN_API_KEY')

network_ids = {'goerli': 5, 'sepolia': 11155111}
l1_chainid = network_ids[network]
ip = get('https://ident.me').content.decode('utf8')

ks_pass_dac = os.getenv("KS_PASS_DAC")
ks_pass_seq = os.getenv("KS_PASS_SEQ")
ks_pass_agr = os.getenv("KS_PASS_AGR")
ks_pass_ctm = os.getenv("KS_PASS_CTM")

if not (infura_key and funded_account and output):
    print("ERROR: Missing env vars")
    sys.exit(1)


def gen_env_file(deployment_mnemonic, infura_key):
    env_file = open(f"{output}/env", "w")
    env_file.write(
        f'MNEMONIC="{deployment_mnemonic}"\n'
        f'INFURA_PROJECT_ID="{infura_key}"\n'
        f'ETHERSCAN_API_KEY="{etherscan_apikey}"\n'
    )
    env_file.close()


def gen_deployment_pars_file(
    sequencer_addr, aggregator_addr, deployment_addr, is_validium=False
):
    global ip
    create_rollup_parameters = {
        "realVerifier": real_verifier,
        "trustedSequencerURL": f"http://{ip}:8545",
        "networkName": f"{network_name}",
        "description": "0.0.1",
        "trustedSequencer": f"{sequencer_addr}",
        "chainID": chainid,
        "adminZkEVM": f"{deployment_addr}",
        "forkID": forkid,
        "consensusContract": "PolygonZkEVMEtrog",
        "gasTokenAddress": "",
        "deployerPvtKey": "",
        "maxFeePerGas": "",
        "maxPriorityFeePerGas": "",
        "multiplierGas": "",
    }
    if is_validium:
        create_rollup_parameters["consensusContract"] = "PolygonValidiumEtrog"
        create_rollup_parameters["dataAvailabilityProtocol"] = \
            "PolygonDataCommittee"

    deployment_parameters = {
        "test": True,
        "timelockAdminAddress": f"{deployment_addr}",
        "minDelayTimelock": 3600,
        # "salt": "0x0000000000000000000000000000000000000000000000000000000000000000",  # noqa
        "salt": f"0x{secrets.token_hex(32)}",
        "initialZkEVMDeployerOwner": f"{deployment_addr}",
        "admin": f"{deployment_addr}",
        "trustedAggregator": f"{aggregator_addr}",
        "trustedAggregatorTimeout": 604799,
        "pendingStateTimeout": 604799,
        "emergencyCouncilAddress": f"{deployment_addr}",
        "polTokenAddress": "",
        "zkEVMDeployerAddress": "",
        "deployerPvtKey": "",
        "maxFeePerGas": "",
        "maxPriorityFeePerGas": "",
        "multiplierGas": ""
    }

    if forkid >= 7:
        deployment_file = open(f"{output}/deploy_parameters.json", "w")
        json.dump(deployment_parameters, deployment_file, indent=2)
        create_rollup_file = \
            open(f"{output}/create_rollup_parameters.json", "w")
        json.dump(create_rollup_parameters, create_rollup_file, indent=2)
    else:
        deployment_file = open(f"{output}/deploy_parameters.json", "w")
        v6_pars = create_rollup_parameters | deployment_parameters
        v6_pars['version'] = v6_pars['description']
        v6_pars['zkEVMOwner'] = v6_pars['initialZkEVMDeployerOwner']
        v6_pars['timelockAddress'] = v6_pars['timelockAdminAddress']
        v6_pars['maticTokenAddress'] = v6_pars['polTokenAddress']
        json.dump(v6_pars, deployment_file, indent=2)


def deployment_helper_set_gas_price(ep):
    web3 = Web3(Web3.HTTPProvider(ep))
    # gas_price = web3.eth.gas_price
    gas_price_gwei = web3.from_wei(web3.eth.gas_price, 'gwei')
    gas_price_gwei = round(float(gas_price_gwei)*1.10, 8)

    for line in fileinput.input(deployment_helper, inplace=1):
        if "const gasPriceKeylessDeployment" in line:
            line = \
                f"const gasPriceKeylessDeployment = '{gas_price_gwei:.8f}';\n"
        sys.stdout.write(line)
    say(
        f"Patched file {deployment_helper} to gasPrice "
        f"{gas_price_gwei:.8f} gweis")


def set_balances(deployment_addr, aggregator_addr, sequencer_addr):
    deployer_balance = get_eth_balance(l1_ep, deployment_addr)
    aggregator_balance = get_eth_balance(l1_ep, aggregator_addr)
    sequencer_balance = get_eth_balance(l1_ep, sequencer_addr)
    say(
        f"Current balances: Deployer {deployer_balance}ETH | Sequencer "
        f"{sequencer_balance}ETH | Aggregator {aggregator_balance}ETH"
    )
    amount = 0
    src_prvkey = funded_prvkey

    web3 = Web3(Web3.HTTPProvider(l1_ep))
    nonce = web3.eth.get_transaction_count(funded_account)

    if deployer_balance < deployer_balance_desired:
        amount = deployer_balance_desired - deployer_balance
        src_prvkey = src_prvkey or input(f"Priv key for {funded_account}: ")
        transfer(
            l1_ep, l1_chainid, funded_account, src_prvkey, deployment_addr,
            amount, wait=False, nonce=nonce)
        nonce += 1

    if aggregator_balance < aggregator_balance_desired:
        amount = aggregator_balance_desired - aggregator_balance
        src_prvkey = src_prvkey or input(f"Priv key for {funded_account}: ")
        transfer(
            l1_ep, l1_chainid, funded_account, src_prvkey, aggregator_addr,
            amount, wait=False, nonce=nonce)
        nonce += 1

    if sequencer_balance < sequencer_balance_desired:
        amount = sequencer_balance_desired - sequencer_balance
        src_prvkey = src_prvkey or input(f"Priv key for {funded_account}: ")
        transfer(
            l1_ep, l1_chainid, funded_account, src_prvkey, sequencer_addr,
            amount, wait=False, nonce=nonce)
        nonce += 1

    say("Allowing 30s for tx to be mined")
    sleep(30)

    if amount:
        deployer_balance = get_eth_balance(l1_ep, deployment_addr)
        aggregator_balance = get_eth_balance(l1_ep, aggregator_addr)
        sequencer_balance = get_eth_balance(l1_ep, sequencer_addr)
        say(
            f"Final balances: Deployer {deployer_balance}ETH | Sequencer "
            f"{sequencer_balance}ETH | Aggregator {aggregator_balance}ETH"
        )
        if not deployer_balance:
            say("ERROR: Deployer balance is 0")
            sys.exit(1)


addresses = load_or_create_addresses(
    addresses_file=addresses_file, ks_pass_dac=ks_pass_dac,
    ks_pass_seq=ks_pass_seq, ks_pass_agr=ks_pass_agr, ks_pass_ctm=ks_pass_ctm
)
sequencer_addr = addresses['Sequencer']['addr']
aggregator_addr = addresses['Aggregator']['addr']
deployment_addr = addresses['Deployer']['addr']

deployment_mnemonic = addresses['Deployer']['mnemonic']
gen_env_file(deployment_mnemonic, infura_key)

gen_deployment_pars_file(
    sequencer_addr, aggregator_addr, deployment_addr, is_validium=is_validium)

deployment_helper_set_gas_price(l1_ep)

set_balances(deployment_addr, aggregator_addr, sequencer_addr)
