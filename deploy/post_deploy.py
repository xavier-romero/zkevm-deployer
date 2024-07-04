import os
import json
from web3 import Web3
from utils import load_or_create_addresses, say, transfer, get_eth_balance

l1_ep = os.getenv('L1_EP')
contracts_repo = os.getenv('CONTRACTS_REPO')
genesis_file = os.getenv('GENESIS_FILE')
erigon_dyn_allocs_file = os.getenv('ERIGON_DYN_ALLOCS_FILE')
erigon_dyn_conf_file = os.getenv('ERIGON_DYN_CONF_FILE')
erigon_dyn_chainspec_file = os.getenv('ERIGON_DYN_CHAINSPEC_FILE')
output_dir = os.getenv('OUTPUT_DIR')
deploy_output_file = os.getenv('DEPLOY_OUTPUT_FILE')
rollup_output_file = os.getenv('ROLLUP_OUTPUT_FILE')
node_genesis_file = os.getenv('NODE_GENESIS_FILE')
addresses_file = os.getenv('ADDRESSES_FILE')
funded_account = os.getenv('FUNDED_ACCOUNT')
network = os.getenv('NETWORK')
forkid = int(os.getenv('FORKID'))
network_ids = {'goerli': 5, 'sepolia': 11155111}
l1_chainid = network_ids[network]
l2_chainid = os.getenv('CHAINID')
network_name = os.getenv('NETWORK_NAME')
w = Web3(Web3.HTTPProvider(l1_ep))

token_abi = [
    {
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [
            {
                "name": "success",
                "type": "bool"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
]


# def get_deployment_folder():
#     folders = glob.glob(f"{contracts_repo}/deployments/{network}*")
#     deployment_folder = max(folders, key=os.path.getctime)
#     say(f"Deployment folder: {deployment_folder}")
#     return deployment_folder


def approve(token, spender_address, wallet_address, private_key, ether_amount):
    spender = spender_address
    # max_amount = w.to_wei(ether_amount, 'ether')
    max_amount = 115792089237316195423570985008687907853269984665640564039457584007913129639935  # noqa
    nonce = w.eth.get_transaction_count(wallet_address)

    tx = token.functions.approve(spender, max_amount).build_transaction({
        'from': wallet_address,
        'nonce': nonce
    })

    signed_tx = w.eth.account.sign_transaction(tx, private_key)
    tx_hash = w.eth.send_raw_transaction(signed_tx.rawTransaction)
    say(
        f"Approved {ether_amount} to {spender_address}"
        f" on tx {w.to_hex(tx_hash)}")
    return w.to_hex(tx_hash)


def get_deployment_addr():
    f1 = open(deploy_output_file)
    data1 = json.load(f1)
    f1.close()
    if forkid >= 7:
        f2 = open(rollup_output_file)
        data2 = json.load(f2)
        f2.close()
        return (data2['rollupAddress'], data1['polTokenAddress'])
    else:
        return (data1['polygonZkEVMAddress'], data1['maticTokenAddress'])


def generate_node_genesis():
    g = open(genesis_file)
    do = open(deploy_output_file)
    genesis = json.load(g)
    deploy_output = json.load(do)

    say("Creating node genesis file")
    if forkid >= 7:
        ro = open(rollup_output_file)
        rollup_output = json.load(ro)

        l1_config = {
            'polygonZkEVMAddress': rollup_output['rollupAddress'],
            'polTokenAddress': deploy_output['polTokenAddress'],
            'polygonZkEVMGlobalExitRootAddress':
                deploy_output['polygonZkEVMGlobalExitRootAddress']
        }
        if forkid == 7:
            l1_config['polygonRollupManagerAddress'] = deploy_output['polygonRollupManager']  # noqa
            genesis_block_number = rollup_output["createRollupBlock"]
        else:
            l1_config['polygonRollupManagerAddress'] = deploy_output['polygonRollupManagerAddress']  # noqa
            genesis_block_number = rollup_output["createRollupBlockNumber"]
    else:
        l1_config = deploy_output
        del l1_config['chainID']
        genesis_block_number = deploy_output["deploymentBlockNumber"]

    l1_config['chainId'] = l1_chainid
    node_genesis = {
        "l1Config": l1_config,
        "l2chainId": l2_chainid,
        "genesisBlockNumber": genesis_block_number,
        "root": genesis["root"],
        "genesis": genesis["genesis"]
    }
    f = open(node_genesis_file, "w")
    json.dump(node_genesis, f, indent=2)


def generate_erigon_files():
    g = open(genesis_file)
    ro = open(rollup_output_file)
    deployment_genesis = json.load(g)
    rollup_output = json.load(ro)

    erigon_dyn_allocs = {}
    genesis = deployment_genesis.get('genesis')
    for x in genesis:
        _item = {
            'contractName': x.get('contractName'),
            'balance': x.get('balance'),
            'nonce': x.get('nonce'),
            'code': x.get('bytecode'),
            'storage': x.get('storage')
        }
        erigon_dyn_allocs[x.get('address')] = _item

    erigon_dyn_conf = {
        'root': deployment_genesis.get('root'),
        'timestamp': rollup_output['firstBatchData']['timestamp'],
        'gasLimit': 0,
        'difficulty': 0
    }
    rollup_output['firstBatchData']['timestamp']

    f = open(erigon_dyn_allocs_file, "w")
    json.dump(erigon_dyn_allocs, f, indent=2)
    f.close()

    f = open(erigon_dyn_conf_file, "w")
    json.dump(erigon_dyn_conf, f, indent=2)
    f.close()

    erigon_dyn_chainspec = {
        "ChainName": network_name,
        "chainId": int(l2_chainid),
        "consensus": "ethash",
        "homesteadBlock": 0,
        "daoForkBlock": 0,
        "eip150Block": 0,
        "eip155Block": 0,
        "byzantiumBlock": 0,
        "constantinopleBlock": 0,
        "petersburgBlock": 0,
        "istanbulBlock": 0,
        "muirGlacierBlock": 0,
        "berlinBlock": 0,
        "londonBlock": 9999999999999999999999999999999999999999999999999,
        "arrowGlacierBlock": 9999999999999999999999999999999999999999999999999,
        "grayGlacierBlock": 9999999999999999999999999999999999999999999999999,
        "terminalTotalDifficulty": 58750000000000000000000,
        "terminalTotalDifficultyPassed": False,
        "shanghaiTime": 9999999999999999999999999999999999999999999999999,
        "cancunTime": 9999999999999999999999999999999999999999999999999,
        "pragueTime": 9999999999999999999999999999999999999999999999999,
        "ethash": {}
    }
    f = open(erigon_dyn_chainspec_file, "w")
    json.dump(erigon_dyn_chainspec, f, indent=2)
    f.close()


def return_deployer_balance(
    deployment_addr, deployment_prvkey, funded_account
):
    deployer_balance = get_eth_balance(l1_ep, deployment_addr)
    say(
        f"Returning remaining balance ({deployer_balance}) to {funded_account}"
    )
    transfer(
        l1_ep, l1_chainid, deployment_addr, deployment_prvkey, funded_account,
        deployer_balance, gas_from_amount=True, full_amount=True)


addresses = load_or_create_addresses(addresses_file)
sequencer_addr = addresses['Sequencer']['addr']
sequencer_prvkey = addresses['Sequencer']['prvkey']
deployment_addr = addresses['Deployer']['addr']
deployment_prvkey = addresses['Deployer']['prvkey']
# deploy_folder = get_deployment_folder()
(zkevm_addr, matic_addr) = get_deployment_addr()
matic = w.eth.contract(address=matic_addr, abi=token_abi)
approve(matic, zkevm_addr, sequencer_addr, sequencer_prvkey, 100)
generate_node_genesis()
generate_erigon_files()
return_deployer_balance(deployment_addr, deployment_prvkey, funded_account)
