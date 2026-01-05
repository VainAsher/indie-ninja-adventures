"""
Logging System - Multi-level structured logging with persistent storage

This module provides configurable logging with:
- DEBUG/INFO/WARNING/ERROR levels
- Persistent file storage (session-based)
- User-selectable log directory
- Platform-specific default locations
- Rotating file handlers (10MB per file, 3 backups)
"""

import logging
import logging.config
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path

from core.paths import get_user_data_dir


class GameLogger:
    """
    Centralized logging with persistent storage and user-configurable paths

    Features:
    - Session-based log files with timestamps
    - Platform-specific default directories
    - User-selectable log location via settings
    - Rotating file handler (10MB x 3 = 30MB total)
    - Console and file output

    Usage:
        logger = GameLogger()
        logger.get_logger("mechanics.jump").info("Jump activated")
    """

    # Log levels
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR

    def __init__(self, user_data_dir: Path | None = None, config_path: Path | None = None):
        """
        Initialize game logger

        Args:
            user_data_dir: Custom user data directory (defaults to platform-specific)
            config_path: Path to logging.yaml config (optional)
        """
        self.user_data_dir = user_data_dir or self._get_env_or_default_user_data_dir()
        self.log_dir = self.user_data_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create session-specific log file
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.log_dir / f"VainAsherGamings_IndieNinjaAdventures_{timestamp}.log"

        self.config_path = config_path
        self._configure_logging()
        self.root_logger = logging.getLogger("ninja_dash")

        self.root_logger.info("=" * 60)
        self.root_logger.info(
            "Vain Asher Gaming's: Indie Ninja Adventures Logging System Initialized"
        )
        self.root_logger.info(f"Log directory: {self.log_dir}")
        self.root_logger.info(f"Session log file: {self.log_file.name}")
        self.root_logger.info("=" * 60)

    def _get_env_or_default_user_data_dir(self) -> Path:
        """
        Get user data directory from env override or project-local default

        Priority:
        1. NINJADASH_USER_DATA environment variable (full override)
        2. Project-local user_data/ directory (default)

        Automatically handles PyInstaller frozen executables.

        Returns:
            Path to user data directory
        """
        return get_user_data_dir()

    def _configure_logging(self):
        """Configure logging from YAML or defaults"""
        if self.config_path and self.config_path.exists():
            try:
                import yaml

                with open(self.config_path) as f:
                    config = yaml.safe_load(f)
                logging.config.dictConfig(config)
                return
            except Exception as e:
                print(f"Warning: Failed to load logging config from {self.config_path}: {e}")
                print("Falling back to default configuration")

        # Default configuration
        self._configure_default_logging()

    def _configure_default_logging(self):
        """Set up default logging configuration"""
        # Create formatters
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)8s] %(name)30s | %(message)s", datefmt="%H:%M:%S"
        )
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)

        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(self.log_file), maxBytes=10485760, backupCount=3, encoding="utf-8"  # 10MB
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)

        # Configure root logger
        root = logging.getLogger("ninja_dash")
        root.setLevel(logging.DEBUG)
        root.handlers.clear()  # Remove any existing handlers
        root.addHandler(console_handler)
        root.addHandler(file_handler)

        # Prevent propagation to avoid duplicate logs
        root.propagate = False

    def get_logger(self, module_name: str) -> logging.Logger:
        """
        Get logger for specific module

        Args:
            module_name: Module name (e.g., "mechanics.jump")

        Returns:
            Logger instance for the module
        """
        return logging.getLogger(f"ninja_dash.{module_name}")

    def set_level(self, level: int):
        """
        Set global logging level

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.root_logger.setLevel(level)
        for handler in self.root_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(level)

    def set_log_directory(self, new_path: Path):
        """
        Change log directory at runtime (from settings menu)

        Args:
            new_path: New directory path for logs

        Note:
            This creates a new log file in the new directory.
            Previous logs remain in the old directory.
        """
        self.log_dir = Path(new_path) / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create new session file in new directory
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.log_dir / f"VainAsherGamings_IndieNinjaAdventures_{timestamp}.log"

        # Reconfigure file handler
        self._reconfigure_file_handler()

        self.root_logger.info(f"Log directory changed to: {self.log_dir}")
        self.root_logger.info(f"New session log file: {self.log_file.name}")

    def _reconfigure_file_handler(self):
        """Reconfigure file handler with new log file"""
        # Remove old file handler
        for handler in self.root_logger.handlers[:]:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                handler.close()
                self.root_logger.removeHandler(handler)

        # Add new file handler
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(self.log_file), maxBytes=10485760, backupCount=3, encoding="utf-8"  # 10MB
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        self.root_logger.addHandler(file_handler)


class MechanicLogger:
    """
    Logger wrapper for mechanics with structured logging methods

    Provides convenience methods for common logging patterns in game mechanics.
    """

    def __init__(self, mechanic_name: str, logger: logging.Logger):
        """
        Initialize mechanic logger

        Args:
            mechanic_name: Name of the mechanic (for prefixing)
            logger: Underlying logger instance
        """
        self.mechanic_name = mechanic_name
        self.logger = logger

    def state_transition(self, from_state: str, to_state: str):
        """Log state transition"""
        self.logger.info(f"{self.mechanic_name}: {from_state} -> {to_state}")

    def input_processed(self, input_type: str, result: str):
        """Log input processing"""
        self.logger.debug(f"{self.mechanic_name}: Input '{input_type}' -> {result}")

    def timer_update(self, timer_name: str, value: float):
        """Log timer update"""
        self.logger.debug(f"{self.mechanic_name}: {timer_name} = {value:.3f}s")

    def collision_response(self, collision_type: str, action: str):
        """Log collision response"""
        self.logger.debug(f"{self.mechanic_name}: Collision '{collision_type}' -> {action}")

    def error(self, message: str):
        """Log error"""
        self.logger.error(f"{self.mechanic_name}: ERROR - {message}")

    def warning(self, message: str):
        """Log warning"""
        self.logger.warning(f"{self.mechanic_name}: WARNING - {message}")

    def info(self, message: str):
        """Log info"""
        self.logger.info(f"{self.mechanic_name}: {message}")

    def debug(self, message: str):
        """Log debug"""
        self.logger.debug(f"{self.mechanic_name}: {message}")


class LoggerFactory:
    """Factory for creating loggers"""

    def __init__(self, game_logger: GameLogger):
        self.game_logger = game_logger

    def get(self, module_name: str) -> logging.Logger:
        """Get standard logger"""
        return self.game_logger.get_logger(module_name)

    def get_mechanic_logger(self, mechanic_name: str) -> MechanicLogger:
        """Get mechanic logger with convenience methods"""
        logger = self.game_logger.get_logger(f"mechanics.{mechanic_name}")
        return MechanicLogger(mechanic_name, logger)
