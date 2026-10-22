#!/bin/sh
# Generates the Fernet key for the PII vault (docker secret). Run once.
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > secrets/pii_vault_key
chmod 600 secrets/pii_vault_key && echo "wrote secrets/pii_vault_key"
