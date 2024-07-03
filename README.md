# zkevm-deployer
Automate full zkEVM local deployment

## Requirements
Some system packages required to run, mainly:
- npm
- Python
- Docker

```bash
sudo apt-get -y install jq docker.io python3 python3-pip python3-psycopg2
pip3 install web3

curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh | bash
source ~/.bashrc
nvm install 16
```

## Environment variables
- NETWORK: defaults to "sepolia"
- INFURA_KEY: Required by the zkevm-contracts repo to deploy the contracts. It is also used to set L1 EP on docker-compose
ETHERSCAN_API_KEY: Used by zkevm-contracts to verify the contracts
- FUNDED_ACCOUNT: Wallet with balance enough to send eths to the Deployer + Sequencer + Aggregator
- FUNDED_PRVKEY: Private key for the funded account, if you don't specify the private key as environment variable, you'll be asked for the key during execution.
- CHAINID: Chainid for the L2 network that will be deployed.
- NETWORK_NAME: Network name to be set for the rollup
- DEPLOYER_BALANCE: Defaults to 4. Balance desired for the deployer, there will be transfered from the FUNDED_ACCOUNT as much balance as required to reach that amount.
- SEQUENCER_BALANCE: Defaults to 0.05. Balance desired for the sequencer, there will be transfered from the FUNDED_ACCOUNT as much balance as required to reach that amount.
- AGGREGATOR_BALANCE: Defaults to 0.05. Balance desired for the aggregator, there will be transfered from the FUNDED_ACCOUNT as much balance as required to reach that amount.
- REAL_VERIFIER: Defaults to 1 (True). Set to 0 to use Mock prover.
- IS_VALIDIUM: Defaults to 1 (True). Set to 0 to deploy a zkEVM Rollup.
- ERIGON_TAG: Set the tag to use from the docker repo for Erigon
- NODE_TAG: Set the tag to use from the docker repo for the node
- PROVER_TAG: Set the tag to use from the docker repo for the prover
- BRIDGE_TAG: Set the tag to use from the docker repo for the bridge-api, defaults to v0.4.2
- BRIDGEUI_TAG: Set the tag to use from the docker repo for the bridge-ui, defaults to etrog-v2
- KS_PASS_DAC: Keystore password for DAC, defaults to "test"
- KS_PASS_SEQ: Keystore password for Sequencer, defaults to "test"
- KS_PASS_AGR: Keystore password for Aggregator, defaults to "test"
- KS_PASS_CTM: Keystore password for ClaimTxManager, defaults to "test"

## Example deployment
```bash
cd zkevm-contracts
git checkout v6.0.0-rc.1-fork.9
cd ..

IS_VALIDIUM=false \
REAL_VERIFIER=true \
NETWORK_NAME=erigon-network6 CHAINID=9631 FORKID=9 \
NETWORK=sepolia \
NODE_TAG=v0.7.0 PROVER_TAG=v6.0.3-RC18 ERIGON_TAG=20240703001110-e2ffe0b \
FUNDED_ACCOUNT=0x**************************************** \
FUNDED_PRVKEY=**************************************************************** \
INFURA_KEY=**************************** \
ETHERSCAN_API_KEY=************************ \
./deploy.sh

IS_VALIDIUM=true \
REAL_VERIFIER=true \
NETWORK_NAME=erigon-cdk2 CHAINID=452 FORKID=9 \
NETWORK=sepolia \
NODE_TAG=v0.7.0 PROVER_TAG=v6.0.3-RC18 ERIGON_TAG=20240703001110-e2ffe0b \
KS_PASS_DAC=test KS_PASS_SEQ=test KS_PASS_AGR=test KS_PASS_CTM=test \
FUNDED_ACCOUNT=0x**************************************** \
FUNDED_PRVKEY=**************************************************************** \
INFURA_KEY=**************************** \
ETHERSCAN_API_KEY=************************ \
./deploy.sh

```
