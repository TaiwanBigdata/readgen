from pathlib import Path

# Root paths
ROOT_PATH = Path(__file__).parent.parent.parent
DATA_PATH = ROOT_PATH / "data"
MODELS_PATH = ROOT_PATH / "models"
CACHES_PATH = ROOT_PATH / "caches"
BACKUPS_PATH = ROOT_PATH / "backups"
SECRETS_PATH = ROOT_PATH / "secrets"
APP_PATH = ROOT_PATH / "app"


# Ensure critical directories exist
for path in [
    DATA_PATH,
    MODELS_PATH,
    CACHES_PATH,
    BACKUPS_PATH,
    SECRETS_PATH,
]:
    path.mkdir(exist_ok=True, parents=True)
