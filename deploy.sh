#!/bin/bash

echo "zkEVM Deployer 2024.06.03"

NVM_DIR=${NVM_DIR:-/usr/local/nvm}
. $NVM_DIR/nvm.sh

# GENERAL CONFIG
WORKINGDIR=$PWD
FILESDIR=$WORKINGDIR/files
DEPLOYDIR=$WORKINGDIR/deploy
[ -d "$DEPLOYDIR" ] || exit
export CONTRACTS_REPO=${WORKINGDIR}/zkevm-contracts
TERRAFORM_REPO=${WORKINGDIR}/zkevm-terraform
export NETWORK=${NETWORK:-sepolia}

# Vars used in pre and/or post deploy scripts:
export INFURA_KEY=${INFURA_KEY} # required by zkevm-contracts
export L1_EP=https://sepolia.infura.io/v3/$INFURA_KEY
export FUNDED_ACCOUNT=${FUNDED_ACCOUNT}
export FUNDED_PRVKEY=${FUNDED_PRVKEY}
export OUTPUT_DIR=$WORKINGDIR/output
OUTPUT_DIR_PRIVATE_PREFIX=$WORKINGDIR/.output
DOCKERDIR=${OUTPUT_DIR}/docker
export FORKID=${FORKID:-9}
if [[ $FORKID -ge 7 ]]
then
    export FILE_DEPLOYMENT_HELPER=$CONTRACTS_REPO/deployment/helpers/deployment-helpers.ts
else
    export FILE_DEPLOYMENT_HELPER=$CONTRACTS_REPO/deployment/helpers/deployment-helpers.js
fi
export GENESIS_FILE=$OUTPUT_DIR/genesis.json
export DEPLOY_OUTPUT_FILE=$OUTPUT_DIR/deploy_output.json
export ROLLUP_OUTPUT_FILE=$OUTPUT_DIR/create_rollup_output.json
export NODE_GENESIS_FILE=$OUTPUT_DIR/node_genesis.json
export ERIGON_DYN_ALLOCS_FILE=$OUTPUT_DIR/dynamic-integration-allocs.json
export ERIGON_DYN_CONF_FILE=$OUTPUT_DIR/dynamic-integration-conf.json
export ERIGON_DYN_CHAINSPEC_FILE=$OUTPUT_DIR/dynamic-integration-chainspec.json
export ADDRESSES_FILE=$OUTPUT_DIR/wallets.json
export CHAINID=${CHAINID}
export NETWORK_NAME=${NETWORK_NAME:-"zkevm"}
export DEPLOYER_BALANCE=${DEPLOYER_BALANCE:-4}
export SEQUENCER_BALANCE=${SEQUENCER_BALANCE:-0.05}
export AGGREGATOR_BALANCE=${AGGREGATOR_BALANCE:-0.05}
export REAL_VERIFIER=${REAL_VERIFIER:-1}
export IS_VALIDIUM=${IS_VALIDIUM:-1}
export ETHERSCAN_API_KEY=${ETHERSCAN_API_KEY}

# Vars used for Docker
export NODE_IMAGE=hermeznetwork/zkevm-node:${NODE_TAG}
export ZKPROVER_IMAGE=hermeznetwork/zkevm-prover:${PROVER_TAG}
export BRIDGE_IMAGE=hermeznetwork/zkevm-bridge-service:${BRIDGE_TAG:-v0.4.3-RC1}
export BRIDGEUI_IMAGE=hermeznetwork/zkevm-bridge-ui:${BRIDGEUI_TAG:-etrog-v2}
export ERIGON_IMAGE=hermeznetwork/cdk-erigon:${ERIGON_TAG:-2.0.0-beta3}

# keystore passwords
export KS_PASS_DAC=${KS_PASS_DAC:-"test"}
export KS_PASS_SEQ=${KS_PASS_SEQ:-"test"}
export KS_PASS_AGR=${KS_PASS_AGR:-"test"}
export KS_PASS_CTM=${KS_PASS_CTM:-"test"}

#### LOGIC START ####


# INITIAL CLEANUP
echo "Cleaning up..."
mv $OUTPUT_DIR ${OUTPUT_DIR_PRIVATE_PREFIX}.$(date +%Y%m%d.%H%M%S)
mkdir $OUTPUT_DIR || exit
mkdir $DOCKERDIR || exit
cd $WORKINGDIR || exit
rm -f $CONTRACTS_REPO/.openzeppelin/*
rm -f $CONTRACTS_REPO/deployment/deploy*
rm -fr $DEPLOYDIR/__pycache__

# PRE DEPLOYMENT
echo "Pre deployment"
cd $DEPLOYDIR || exit
python3 pre_deploy.py
cp -f $OUTPUT_DIR/env $CONTRACTS_REPO/.env
if [[ $FORKID -ge 7 ]]
then
    cp -f $OUTPUT_DIR/deploy_parameters.json $CONTRACTS_REPO/deployment/v2/deploy_parameters.json
    cp -f $OUTPUT_DIR/create_rollup_parameters.json $CONTRACTS_REPO/deployment/v2/create_rollup_parameters.json
else
    cp -f $OUTPUT_DIR/deploy_parameters.json $CONTRACTS_REPO/deployment/deploy_parameters.json
fi
# CONTRACT DEPLOYMENT
echo "Deployment"
cd $CONTRACTS_REPO || exit
rm -fr node_modules
rm -f ./deployment/v2/deploy_ongoing.json
npm i
# node deployment/1_createGenesis.js --test
if [[ $FORKID -ge 7 ]]
then
    # npm run deploy:v2:sepolia
    npm run deploy:testnet:v2:sepolia
    cp -f $CONTRACTS_REPO/deployment/v2/genesis.json $OUTPUT_DIR/
    cp -f $CONTRACTS_REPO/deployment/v2/deploy_output.json $OUTPUT_DIR/
    cp -f $CONTRACTS_REPO/deployment/v2/create_rollup_output.json $OUTPUT_DIR/
    npm run verify:v2:sepolia
else
    npm run deploy:deployer:ZkEVM:sepolia
    npm run deploy:testnet:ZkEVM:test:sepolia
    cp -f $CONTRACTS_REPO/deployment/genesis.json $OUTPUT_DIR/
    cp -f $CONTRACTS_REPO/deployment/deploy_output.json $OUTPUT_DIR/
fi
# POST DEPLOYMENT
echo "Post deployment"
cd $DEPLOYDIR || exit
python3 post_deploy.py

echo "Keystore generation..."
cd $OUTPUT_DIR || exit
SEQUENCER_PRVKEY=$(cat $ADDRESSES_FILE | jq .Sequencer.prvkey -r)
docker run --rm $NODE_IMAGE sh -c "/app/zkevm-node encryptKey --pk=$SEQUENCER_PRVKEY \
    --pw=$KS_PASS_SEQ --output=./keystore; cat ./keystore/*" > sequencer.keystore
AGGR_PRVKEY=$(cat $ADDRESSES_FILE | jq .Aggregator.prvkey -r)
docker run --rm $NODE_IMAGE sh -c "/app/zkevm-node encryptKey --pk=$AGGR_PRVKEY \
    --pw=$KS_PASS_AGR --output=./keystore; cat ./keystore/*" > aggregator.keystore
CLAIMTX_PRVKEY=$(cat $ADDRESSES_FILE | jq .ClaimTX.prvkey -r)
docker run --rm $NODE_IMAGE sh -c "/app/zkevm-node encryptKey --pk=$CLAIMTX_PRVKEY \
    --pw=$KS_PASS_CTM --output=./keystore; cat ./keystore/*" > claimtx.keystore
if [[ $IS_VALIDIUM -eq 1 ]]
then
    DAC_PRVKEY=$(cat $ADDRESSES_FILE | jq .DAC.prvkey -r)
    docker run --rm $NODE_IMAGE sh -c "/app/zkevm-node encryptKey --pk=$DAC_PRVKEY \
        --pw=$KS_PASS_DAC --output=./keystore; cat ./keystore/*" > dac.keystore
fi

cd $DOCKERDIR
mkdir config
mkdir config/datastreamer
mkdir config/erigon_seq-datadir
chmod 777 -R config/erigon_seq-datadir
mkdir config/erigon_rpc1-datadir
chmod 777 -R config/erigon_rpc1-datadir
mkdir config/erigon_rpc2-datadir
chmod 777 -R config/erigon_rpc2-datadir
mkdir config/data-seqsender
chmod 777 -R config/data-seqsender
cp -f $OUTPUT_DIR/*.keystore config/
cp -f $OUTPUT_DIR/node_genesis.json config/genesis.json
cp -f $ERIGON_DYN_ALLOCS_FILE config/
cp -f $ERIGON_DYN_CONF_FILE config/
cp -f $ERIGON_DYN_CHAINSPEC_FILE config/
cp -f $FILESDIR/erigon.yaml config/
cp -f $FILESDIR/seqsender.toml config/
cp -f $FILESDIR/aggregator_config.toml config/
cp -f $FILESDIR/node_config.toml config/
cp -f $FILESDIR/bridge_config.toml config/
cp -f $FILESDIR/executor_config.json config/
cp -f $FILESDIR/prover_config.json config/
# cp -f $FILESDIR/prover_config.json config/
cp -f $FILESDIR/init_db.sql config/
cp -f $FILESDIR/compose*.yaml .

AGGR_ADDR=$(cat $ADDRESSES_FILE | jq .Aggregator.addr -r)
SEQ_ADDR=$(cat $ADDRESSES_FILE | jq .Sequencer.addr -r)
GER_ADDR=$(cat config/genesis.json | jq .l1Config.polygonZkEVMGlobalExitRootAddress -r)
POE_ADDR=$(cat config/genesis.json | jq .l1Config.polygonZkEVMAddress -r)
L1_CHAINID=$(cat config/genesis.json | jq .l1Config.chainId -r)
GEN_BLOCKNUM=$(cat config/genesis.json | jq .genesisBlockNumber -r)
ROLLUP_ADDR=$(cat config/genesis.json | jq .l1Config.polygonRollupManagerAddress -r)
BRIDGE_ADDR=$(cat $OUTPUT_DIR/deploy_output.json | jq .polygonZkEVMBridgeAddress -r)

if [[ $IS_VALIDIUM -eq 1 ]]
then
    echo "CDK_ERIGON=$ERIGON_IMAGE
    CDK_NODE=$NODE_IMAGE
    ZKEVM_EXECUTOR=$ZKPROVER_IMAGE
    ZKEVM_BRIDGE=$BRIDGE_IMAGE
    ZKEVM_BRIDGEUI=$BRIDGEUI_IMAGE
    L1_EP=$L1_EP
    SEQUENCER_ADDR=$SEQ_ADDR
    AGGREGATOR_ADDR=$AGGR_ADDR
    BRIDGE_ADDR=$BRIDGE_ADDR
    L1_CHAINID=$L1_CHAINID
    L2_CHAINID=$CHAINID
    ZKEVM_GER_ADDR=$GER_ADDR
    GENESIS_BLOCKNUMER=$GEN_BLOCKNUM
    POE_ADDR=$POE_ADDR
    ROLLUP_ADDR=$ROLLUP_ADDR
    MY_IP=<SET_PUBLIC_IP_HERE>" > .env
else
    echo "ZKEVM_ERIGON=$ERIGON_IMAGE
    ZKEVM_NODE=$NODE_IMAGE
    ZKEVM_EXECUTOR=$ZKPROVER_IMAGE
    ZKEVM_BRIDGE=$BRIDGE_IMAGE
    ZKEVM_BRIDGEUI=$BRIDGEUI_IMAGE
    L1_EP=$L1_EP
    SEQUENCER_ADDR=$SEQ_ADDR
    AGGREGATOR_ADDR=$AGGR_ADDR
    BRIDGE_ADDR=$BRIDGE_ADDR
    L1_CHAINID=$L1_CHAINID
    L2_CHAINID=$CHAINID
    ZKEVM_GER_ADDR=$GER_ADDR
    GENESIS_BLOCKNUMER=$GEN_BLOCKNUM
    POE_ADDR=$POE_ADDR
    ROLLUP_ADDR=$ROLLUP_ADDR
    MY_IP=<SET_PUBLIC_IP_HERE>" > .env
fi

cd $WORKINGDIR
mv $OUTPUT_DIR ${OUTPUT_DIR_PRIVATE_PREFIX}.${NETWORK_NAME}.$(date +%Y%m%d.%H%M%S)
