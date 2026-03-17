import asyncio
import logging
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Optional

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError

logger = logging.getLogger(__name__)


@dataclass
class AWSCredentials:
    """Container for AWS credentials with caching"""

    region_name: str
    aws_access_key_id: str
    aws_secret_access_key: str


class BedrockClientManager:
    """
    Production-grade singleton manager for aioboto3 session.

    Optimizations:
    - Connection pooling with auto-scaling
    - Retry logic with exponential backoff for throttling
    - Credential caching
    - Graceful shutdown
    - Idempotent initialization
    """

    _instance: Optional["BedrockClientManager"] = None
    _session: Optional[aioboto3.Session] = None
    _credentials: Optional[AWSCredentials] = None
    _config: Optional[Config] = None
    _lock: threading.Lock = threading.Lock()  # don`t block threads if Instance created
    _init_lock: threading.Lock = threading.Lock()  # atomicity guarantee

    def __new__(cls) -> "BedrockClientManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(BedrockClientManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def initialize(
        cls,
        region_name: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        max_pool_connections: int = 50,
        connect_timeout: float = 10.0,
        read_timeout: float = 60.0,
        max_attempts: int = 3,
        pool_scaling_factor: int = 2,
        benchmark_workers: Optional[int] = None,
    ) -> None:
        """
        Initializes the manager with credentials and configuration.

        Args:
            benchmark_workers: If set, auto-scales the connection pool
            to ensure it's larger than the number of workers (workers * 2).
        """
        with cls._init_lock:
            instance = cls()
            if instance._session is not None:
                logger.warning(
                    "BedrockClientManager already initialized, skipping reinit"
                )
                return

            if not all([region_name, aws_access_key_id, aws_secret_access_key]):
                raise ValueError("AWS credentials cannot be empty")

            # Auto-scale pool for benchmarks
            if benchmark_workers is not None:
                # avoid waiting for sockets
                scaled_pool = max(
                    benchmark_workers * pool_scaling_factor, max_pool_connections
                )
                if scaled_pool > max_pool_connections:
                    max_pool_connections = scaled_pool
                    logger.info(
                        f"Auto-scaled connection pool to "
                        f"{max_pool_connections} for {benchmark_workers} workers"
                    )

            instance._credentials = AWSCredentials(
                region_name=region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
            )

            instance._config = Config(
                region_name=region_name,
                max_pool_connections=max_pool_connections,
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                retries={"max_attempts": max_attempts, "mode": "adaptive"},
            )

            instance._session = aioboto3.Session(
                region_name=region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
            )

            logger.info(
                "BedrockClientManager initialized",
                extra={
                    "region": region_name,
                    "max_pool_connections": max_pool_connections,
                },
            )

    def is_initialized(self) -> bool:
        return self._session is not None

    def get_session(self) -> aioboto3.Session:
        if self._session is None:
            raise RuntimeError(
                "BedrockClientManager not initialized. "
                "Call BedrockClientManager.initialize() first"
            )
        return self._session

    @asynccontextmanager
    async def get_client(self) -> AsyncGenerator[Any, None]:
        if self._session is None:
            raise RuntimeError(
                "BedrockClientManager not initialized. "
                "Call BedrockClientManager.initialize() first"
            )

        try:
            async with self._session.client(
                "bedrock-runtime", config=self._config
            ) as client:
                yield client
        except EndpointConnectionError:
            logger.error("Failed to connect to Bedrock endpoint", exc_info=True)
            raise
        except ClientError as e:
            logger.error(f"Bedrock API error: {e}", exc_info=True)
            raise
        except Exception:
            logger.error("Unexpected error getting Bedrock client", exc_info=True)
            raise

    async def close(self, grace_period_sec: float = 0.250) -> None:
        if self._session is not None:
            try:
                logger.info("BedrockClientManager shutting down")
                self._session = None
                self._credentials = None
                self._config = None
                # Give aiohttp time to close connectors
                await asyncio.sleep(grace_period_sec)
            except Exception:
                logger.error("Error during shutdown", exc_info=True)
                raise


bedrock_manager = BedrockClientManager()
