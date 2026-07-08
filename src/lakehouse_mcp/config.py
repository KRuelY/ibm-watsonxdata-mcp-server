"""
Configuration management using Pydantic Settings.

This module provides type-safe configuration loading from environment variables.

This file has been modified with the assistance of IBM Bob AI tool
"""

from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class WatsonXConfig(BaseSettings):
    """watsonx.data API configuration."""

    model_config = SettingsConfigDict(
        env_prefix="WATSONX_DATA_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str = Field(
        ...,
        description="watsonx.data API base URL",
        examples=[
            "https://console-ibm-ussouth.lakehouse.test.saas.ibm.com/lakehouse/api",
            "https://console-azure-canadacentral.lakehouse.dev.saas.ibm.com/lakehouse/api",
        ],
    )
    api_key: str = Field(
        ...,
        description="API key for authentication (IBM Cloud IAM or Azure account-IAM)",
    )
    instance_id: str = Field(
        ...,
        description="watsonx.data instance ID (CRN)",
        examples=["crn:v1:bluemix:public:lakehouse:us-south:a/..."],
    )
    timeout_seconds: int = Field(
        default=120,
        description="HTTP request timeout in seconds",
        ge=10,
        le=300,
    )
    tls_insecure_skip_verify: bool = Field(
        default=False,
        description="Skip TLS certificate verification (dev/test only)",
    )

    # Non-IBM hyperscaler fields (Azure, AWS)
    account_iam_host: str | None = Field(
        default=None,
        description="account-IAM host (required for Azure and AWS deployments)",
        examples=["https://account-iam.azure.eastus.platform.test.saas.ibm.com"],
    )
    account_iam_service_id: str | None = Field(
        default=None,
        description="account-IAM service ID (required for Azure and AWS deployments)",
    )

    @property
    def hyperscaler(self) -> str:
        """Detect hyperscaler from base_url hostname.

        Returns 'azure', 'aws', or 'ibm'.
        """
        hostname = urlparse(self.base_url).hostname or ""
        if "azure" in hostname:
            return "azure"
        if "aws" in hostname:
            return "aws"
        return "ibm"

    @model_validator(mode="after")
    def validate_account_iam_fields(self) -> "WatsonXConfig":
        if self.hyperscaler == "ibm":
            return self
        if not self.account_iam_host:
            raise ValueError(
                f"WATSONX_DATA_ACCOUNT_IAM_HOST is required for {self.hyperscaler} deployments"
            )
        if not self.account_iam_service_id:
            # Extract service instance ID from CRN (8th colon-delimited segment, index 7)
            # e.g. crn:v1:azure-staging:public:lakehouse:eastus:sub/<sub-id>:<service-id>::
            parts = self.instance_id.split(":")
            if len(parts) >= 8 and parts[7]:
                self.account_iam_service_id = parts[7]
            else:
                raise ValueError(
                    f"WATSONX_DATA_ACCOUNT_IAM_SERVICE_ID is required for {self.hyperscaler} deployments "
                    "(could not derive it from WATSONX_DATA_INSTANCE_ID)"
                )
        return self


class ServerConfig(BaseSettings):
    """MCP server configuration."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mode: str = Field(
        default="local",
        description="Deployment mode (local, self-hosted, ibm-managed)",
        pattern="^(local|self-hosted|ibm-managed)$",
    )
    log_level: str = Field(
        default="info",
        description="Logging level",
        pattern="^(debug|info|warn|warning|error|critical)$",
    )
    otel_enabled: bool = Field(
        default=False,
        description="Enable OpenTelemetry traces and metrics",
    )
    otel_service_name: str = Field(
        default="ibm-watsonxdata-mcp-server",
        description="OpenTelemetry service name",
    )


class Config:
    """Application configuration container."""

    def __init__(self) -> None:
        """Initialize configuration from environment variables."""
        self.watsonx = WatsonXConfig()
        self.server = ServerConfig()

    def __repr__(self) -> str:
        """Return string representation (without sensitive data)."""
        return f"Config(watsonx_url={self.watsonx.base_url}, mode={self.server.mode}, log_level={self.server.log_level})"
