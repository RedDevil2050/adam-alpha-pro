import os
from typing import Optional
import json
from functools import lru_cache
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from backend.config.settings import get_settings
from loguru import logger

class SecretsManager:
    """
    Manages secrets across different environments using environment variables,
    Azure Key Vault, or other secret stores based on the environment.
    """
    def __init__(self):
        self.settings = get_settings()
        self._key_vault_client = None
        self._managed_identity = None

    @property
    def is_production(self) -> bool:
        return self.settings.is_production

    @property
    def key_vault_client(self) -> Optional[SecretClient]:
        """Lazy initialization of Key Vault client"""
        if self.is_production and not self._key_vault_client:
            try:
                vault_url = os.getenv("AZURE_KEY_VAULT_URL")
                if not vault_url:
                    logger.warning("AZURE_KEY_VAULT_URL not set in production")
                    return None
                    
                credential = self._get_azure_credential()
                if credential:
                    self._key_vault_client = SecretClient(
                        vault_url=vault_url,
                        credential=credential
                    )
            except Exception as e:
                logger.error(f"Failed to initialize Key Vault client: {e}")
                return None
        return self._key_vault_client

    def _get_azure_credential(self):
        """Get appropriate Azure credential based on environment"""
        try:
            # Try Managed Identity first (for Azure services)
            if not self._managed_identity:
                self._managed_identity = ManagedIdentityCredential()
            return self._managed_identity
        except Exception:
            try:
                # Fallback to DefaultAzureCredential (works with service principal, managed identity, etc)
                return DefaultAzureCredential()
            except Exception as e:
                logger.error(f"Failed to get Azure credential: {e}")
                return None

    @lru_cache(maxsize=128)
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Get a secret from the appropriate store based on environment.
        Uses caching to prevent repeated calls to the secret store.
        
        Args:
            secret_name: Name of the secret to retrieve
            
        Returns:
            The secret value or None if not found
        """
        # Production: Try Key Vault first, fallback to env vars
        if self.is_production:
            if self.key_vault_client:
                try:
                    secret = self.key_vault_client.get_secret(secret_name)
                    return secret.value
                except Exception as e:
                    logger.warning(f"Failed to get secret from Key Vault: {e}")
            
        # Development/Testing or Key Vault fallback: Use environment variables
        return os.getenv(secret_name)

    def get_connection_string(self, service_name: str) -> Optional[str]:
        """
        Get a connection string for a service, handling different formats and sources.
        
        Args:
            service_name: Name of the service (e.g., 'DATABASE', 'REDIS')
            
        Returns:
            Connection string or None if not found
        """
        # Try specific connection string first
        conn_str = self.get_secret(f"{service_name}_CONNECTION_STRING")
        if conn_str:
            return conn_str
            
        # Try to build from components for database
        if service_name == "DATABASE":
            try:
                components = {
                    "host": self.get_secret("DATABASE_HOST"),
                    "port": self.get_secret("DATABASE_PORT"),
                    "name": self.get_secret("DATABASE_NAME"),
                    "user": self.get_secret("DATABASE_USER"),
                    "password": self.get_secret("DATABASE_PASSWORD")
                }
                
                if all(components.values()):
                    return (
                        f"postgresql+asyncpg://{components['user']}:{components['password']}"
                        f"@{components['host']}:{components['port']}/{components['name']}"
                    )
            except Exception as e:
                logger.error(f"Failed to build connection string: {e}")
                
        return None

    def clear_cache(self):
        """Clear the secret cache"""
        self.get_secret.cache_clear()

# Global instance
_secrets_manager = None

def get_secrets_manager():
    """Get or create the global SecretsManager instance"""
    global _secrets_manager
    if not _secrets_manager:
        _secrets_manager = SecretsManager()
    return _secrets_manager