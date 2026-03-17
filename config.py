from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseSettings):
    model_id: str = Field("us.amazon.nova-micro-v1:0", alias="BEDROCK_MODEL_ID")
    temperature: float = Field(0.1, alias="BEDROCK_TEMPERATURE")
    max_tokens: int = Field(30, alias="MAX_TOKENS")
    max_tokens_json: int = Field(150, alias="MAX_TOKENS")


class Coverage(BaseSettings):
    # Domain Constants: Define the very essence of the coverage metric.
    # Defined in src/metrics/coverage.py
    # DEFAULT_COLLECTED_FIELDS = [
    #     'conditions', 'anatomy', 'medications', 'treatments', 'onset_duration'
    # ]
    # DEFAULT_TARGET_FIELDS = [
    #     'conditions', 'anatomy', 'medications', 'treatments', 'time_expressions'
    # ]

    coverage_threshold: float =Field(
        0.20, 
        description="Minimum relative coverage for LLM done=true to be accepted"
    )


class DataConfig(BaseSettings):
    profiles_path: str = "data/processed/patient_profiles.jsonl"
    metrics_output_path: str = "data/output/"
    metrics_output_file: str = "metrics.jsonl"
    dialogues_output_path: str = "data/output/dialogues/"
    research_metrics_file: str = "research_metrics.jsonl"
    agregate_metrics_file: str = "aggregate_metrics.json"

class Settings(BaseSettings):
    aws_access_key_id: str | None = Field(None, alias="AWS_ACCESS_KEY_ID")

    aws_secret_access_key: str | None = Field(None, alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field("us-east-1", alias="AWS_REGION")

    logging_level: str = Field(
        default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"
    )
    logging_format: str = Field(
        default="%(asctime)s UTC - %(levelname)s - %(message)s",
        description="Log message format with UTC timezone",
    )
    boto3_debug_logging: bool = Field(
        False, description="True if you want to see boto3 dubuging info."
    )
    asyncio_debug_logging: bool = Field(
        False, description="True if you want to see asyncio dubuging info."
    )
    urllib_debug_logging: bool = Field(
        False, description="True if you want to see urllib dubuging info."
    )
    max_steps: int = 10
    min_words: int = 5
    max_words: int = 12

    model: ModelConfig = Field(default_factory=ModelConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    coverage: Coverage = Field(default_factory=Coverage)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def get_aws_credentials(self) -> dict[str, str | None]:
        creds = {"region_name": self.aws_region}
        if self.aws_access_key_id:
            creds["aws_access_key_id"] = self.aws_access_key_id
        if self.aws_secret_access_key:
            creds["aws_secret_access_key"] = self.aws_secret_access_key
        return 


settings = Settings()
