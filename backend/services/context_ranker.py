from ..schemas import ChangedFile


RISK_KEYWORDS = [
    "auth",
    "login",
    "token",
    "password",
    "secret",
    "permission",
    "admin",
    "payment",
    "delete",
    "db",
    "database",
    "migration",
    "sql",
    "eval",
    "exec",
    "subprocess",
    "cors",
]

LOCK_SUFFIXES = ("package-lock.json", "yarn.lock", "pnpm-lock.yaml")


def score_changed_file(file: ChangedFile) -> int:
    score = 0
    file_type = getattr(file.file_type, "value", file.file_type)

    if file_type == "code":
        score += 4
    if file_type in {"config", "dependency"}:
        score += 3

    change_size = file.additions + file.deletions
    if change_size >= 100:
        score += 3
    elif change_size >= 30:
        score += 2
    else:
        score += 1

    filename = file.filename.lower()
    patch = (file.patch or "").lower()
    if any(keyword in filename for keyword in RISK_KEYWORDS):
        score += 4
    if any(keyword in patch for keyword in RISK_KEYWORDS):
        score += 2

    if filename.endswith(LOCK_SUFFIXES):
        score -= 5

    return score
