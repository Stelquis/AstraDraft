from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class AgentConfig(BaseSettings):
    cad_file: str = ""
    index_file: str = ""
    data_dir: str = "data"
    log_level: str = "INFO"
    llm_enabled: bool = False
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "deepseek-v4-flash[1m]"
    langsmith_api_key: str = ""
    langsmith_project: str = "deepastradraft"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    model_config = {"env_prefix": "ASTRADRAFT_", "env_file": ".env", "extra": "ignore"}

    @property
    def cad_path(self) -> Path:
        return Path(self.cad_file) if self.cad_file else Path(self.data_dir) / "cad"

    @property
    def index_path(self) -> Path:
        if self.index_file:
            return Path(self.index_file)
        return Path(self.data_dir) / "index" / "parameters.json"
