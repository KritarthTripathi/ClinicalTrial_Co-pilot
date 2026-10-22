#!/bin/sh
# Illustrative Azure provisioning. REVIEW before running: SKUs, regions, quota and
# image names change. GPU quota (NCasT4_v3) usually needs a request first.
# Keep this folder separate from the app: the app only needs "Linux + Docker + NVIDIA GPU".
set -e
RG=zerobytes-rg; LOC=eastus; VM=zerobytes-vm; SIZE=Standard_NC4as_T4_v3

az group create -n $RG -l $LOC
az network vnet create -g $RG -n vnet --address-prefix 10.10.0.0/16 --subnet-name vm --subnet-prefix 10.10.1.0/24
az network nsg create -g $RG -n nsg

# Inbound: only from inside the VNet (use Bastion/VPN for access). No public IP.
az network nsg rule create -g $RG --nsg-name nsg -n deny-inet-out --priority 4000 \
  --direction Outbound --access Deny --protocol '*' --destination-address-prefixes Internet \
  --destination-port-ranges '*' --source-address-prefixes '*' --source-port-ranges '*'

az vm create -g $RG -n $VM --size $SIZE --image Canonical:ubuntu-24_04-lts:server:latest \
  --vnet-name vnet --subnet vm --nsg nsg --public-ip-address "" \
  --admin-username azureuser --generate-ssh-keys --os-disk-size-gb 256

# NVIDIA driver extension (check current extension name/version in Azure docs)
az vm extension set -g $RG --vm-name $VM --publisher Microsoft.HpcCompute \
  --name NvidiaGpuDriverLinux --version 1.9

# STAGING NOTE: the outbound-deny rule blocks pulls. Either (a) delete the rule temporarily
# during setup, pull images/models, then re-add it, or (b) bake an image from the offline bundle.
# Remember: deallocate the VM when idle  ->  az vm deallocate -g $RG -n $VM
