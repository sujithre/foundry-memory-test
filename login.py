from azure.identity import AzureCliCredential


def get_credential() -> AzureCliCredential:
    """Use the identity from `az login`."""
    return AzureCliCredential(process_timeout=60)
