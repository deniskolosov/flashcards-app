"""
Configuration management for the flashcard app.
Handles API keys, model selection, and other settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.schemas import ConfigResponse, ConfigUpdate
from backend.spaced_repetition import SpacedRepetitionConfig


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # Default provider
    default_ai_provider: str = "anthropic"

    # Model settings
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_model: str = "gpt-4o"

    # Database
    database_url: str = "postgresql://flashcards:flashcards_password@localhost:5432/flashcards_dev"

    # Spaced Repetition defaults
    initial_interval_days: int = 1
    easy_multiplier: float = 2.5
    good_multiplier: float = 1.8
    minimum_interval_days: int = 1
    maximum_interval_days: int = 180

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


class ConfigManager:
    """Manager for application configuration."""

    def __init__(self, config_dao=None):
        """
        Initialize configuration manager.

        Args:
            config_dao: Optional ConfigDAO for persistent storage
        """
        self.settings = Settings()
        self.config_dao = config_dao

    def get_config_response(self) -> ConfigResponse:
        """
        Get configuration response (without exposing API keys).

        Returns:
            ConfigResponse with safe config data
        """
        # Get values from database if available, otherwise use env
        if self.config_dao:
            default_provider = self.config_dao.get(
                "default_provider", self.settings.default_ai_provider
            )
            anthropic_model = self.config_dao.get("anthropic_model", self.settings.anthropic_model)
            openai_model = self.config_dao.get("openai_model", self.settings.openai_model)
            anthropic_key = self.config_dao.get("anthropic_api_key")
            openai_key = self.config_dao.get("openai_api_key")
        else:
            default_provider = self.settings.default_ai_provider
            anthropic_model = self.settings.anthropic_model
            openai_model = self.settings.openai_model
            anthropic_key = self.settings.anthropic_api_key
            openai_key = self.settings.openai_api_key

        # Use env keys as fallback
        anthropic_key = anthropic_key or self.settings.anthropic_api_key
        openai_key = openai_key or self.settings.openai_api_key

        # Get spaced repetition settings
        if self.config_dao:
            initial_interval_days = int(
                self.config_dao.get("initial_interval_days", self.settings.initial_interval_days)
            )
            easy_multiplier = float(
                self.config_dao.get("easy_multiplier", self.settings.easy_multiplier)
            )
            good_multiplier = float(
                self.config_dao.get("good_multiplier", self.settings.good_multiplier)
            )
            minimum_interval_days = int(
                self.config_dao.get("minimum_interval_days", self.settings.minimum_interval_days)
            )
            maximum_interval_days = int(
                self.config_dao.get("maximum_interval_days", self.settings.maximum_interval_days)
            )
        else:
            initial_interval_days = self.settings.initial_interval_days
            easy_multiplier = self.settings.easy_multiplier
            good_multiplier = self.settings.good_multiplier
            minimum_interval_days = self.settings.minimum_interval_days
            maximum_interval_days = self.settings.maximum_interval_days

        return ConfigResponse(
            default_provider=default_provider,
            anthropic_model=anthropic_model,
            openai_model=openai_model,
            has_anthropic_key=bool(anthropic_key),
            has_openai_key=bool(openai_key),
            initial_interval_days=initial_interval_days,
            easy_multiplier=easy_multiplier,
            good_multiplier=good_multiplier,
            minimum_interval_days=minimum_interval_days,
            maximum_interval_days=maximum_interval_days,
        )

    def update_config(self, config_update: ConfigUpdate) -> ConfigResponse:
        """
        Update configuration values.

        Args:
            config_update: Configuration updates

        Returns:
            Updated ConfigResponse
        """
        if not self.config_dao:
            raise ValueError("ConfigDAO not available for updates")

        # Update API keys if provided
        if config_update.anthropic_api_key is not None:
            self.config_dao.set("anthropic_api_key", config_update.anthropic_api_key)

        if config_update.openai_api_key is not None:
            self.config_dao.set("openai_api_key", config_update.openai_api_key)

        # Update provider if provided
        if config_update.default_provider is not None:
            self.config_dao.set("default_provider", config_update.default_provider)

        # Update model settings if provided
        if config_update.anthropic_model is not None:
            self.config_dao.set("anthropic_model", config_update.anthropic_model)

        if config_update.openai_model is not None:
            self.config_dao.set("openai_model", config_update.openai_model)

        # Update spaced repetition settings if provided
        if config_update.initial_interval_days is not None:
            self.config_dao.set("initial_interval_days", str(config_update.initial_interval_days))

        if config_update.easy_multiplier is not None:
            self.config_dao.set("easy_multiplier", str(config_update.easy_multiplier))

        if config_update.good_multiplier is not None:
            self.config_dao.set("good_multiplier", str(config_update.good_multiplier))

        if config_update.minimum_interval_days is not None:
            self.config_dao.set("minimum_interval_days", str(config_update.minimum_interval_days))

        if config_update.maximum_interval_days is not None:
            self.config_dao.set("maximum_interval_days", str(config_update.maximum_interval_days))

        return self.get_config_response()

    def get_api_key(self, provider: str) -> str | None:
        """
        Get API key for a provider.

        Args:
            provider: "anthropic" or "openai"

        Returns:
            API key if available, None otherwise
        """
        key_name = f"{provider}_api_key"

        # Try database first
        if self.config_dao:
            db_key = self.config_dao.get(key_name)
            if db_key:
                return db_key

        # Fall back to environment
        if provider == "anthropic":
            return self.settings.anthropic_api_key
        elif provider == "openai":
            return self.settings.openai_api_key
        else:
            return None

    def get_model(self, provider: str) -> str:
        """
        Get model name for a provider.

        Args:
            provider: "anthropic" or "openai"

        Returns:
            Model name
        """
        model_key = f"{provider}_model"

        # Try database first
        if self.config_dao:
            db_model = self.config_dao.get(model_key)
            if db_model:
                return db_model

        # Fall back to environment/defaults
        if provider == "anthropic":
            return self.settings.anthropic_model
        elif provider == "openai":
            return self.settings.openai_model
        else:
            return ""

    def get_default_provider(self) -> str:
        """Get the default AI provider."""
        if self.config_dao:
            return self.config_dao.get("default_provider", self.settings.default_ai_provider)
        return self.settings.default_ai_provider

    def get_spaced_repetition_config(self) -> SpacedRepetitionConfig:
        """
        Get spaced repetition configuration.

        Returns:
            SpacedRepetitionConfig with current settings
        """
        if self.config_dao:
            initial_interval_days = int(
                self.config_dao.get("initial_interval_days", self.settings.initial_interval_days)
            )
            easy_multiplier = float(
                self.config_dao.get("easy_multiplier", self.settings.easy_multiplier)
            )
            good_multiplier = float(
                self.config_dao.get("good_multiplier", self.settings.good_multiplier)
            )
            minimum_interval_days = int(
                self.config_dao.get("minimum_interval_days", self.settings.minimum_interval_days)
            )
            maximum_interval_days = int(
                self.config_dao.get("maximum_interval_days", self.settings.maximum_interval_days)
            )
        else:
            initial_interval_days = self.settings.initial_interval_days
            easy_multiplier = self.settings.easy_multiplier
            good_multiplier = self.settings.good_multiplier
            minimum_interval_days = self.settings.minimum_interval_days
            maximum_interval_days = self.settings.maximum_interval_days

        return SpacedRepetitionConfig(
            initial_interval_days=initial_interval_days,
            easy_multiplier=easy_multiplier,
            good_multiplier=good_multiplier,
            minimum_interval_days=minimum_interval_days,
            maximum_interval_days=maximum_interval_days,
        )
