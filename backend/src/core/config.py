from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import DomainConfig


class ConfigManager:
    def __init__(self, db: Session, tenant_id: str, domain_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.domain_id = domain_id
        self._config_cache: Optional[Dict[str, str]] = None

    def _load_config(self) -> None:
        configs = (
            self.db.query(DomainConfig)
            .filter(
                DomainConfig.tenant_id == self.tenant_id,
                DomainConfig.domain_id == self.domain_id,
            )
            .all()
        )
        self._config_cache = {c.config_key: c.config_value for c in configs}

    def clear_cache(self) -> None:
        self._config_cache = None

    def __getitem__(self, key: str) -> str:
        if self._config_cache is None:
            self._load_config()
        return self._config_cache[key]

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __setitem__(self, key: str, value: str) -> None:
        config = DomainConfig(
            tenant_id=self.tenant_id,
            domain_id=self.domain_id,
            config_key=key,
            config_value=str(value),
        )
        self.db.merge(config)
        self.db.commit()
        self.clear_cache()

    def __iter__(self):
        if self._config_cache is None:
            self._load_config()
        return iter(self._config_cache)

    def __len__(self):
        if self._config_cache is None:
            self._load_config()
        return len(self._config_cache)

    def items(self):
        if self._config_cache is None:
            self._load_config()
        return self._config_cache.items()
