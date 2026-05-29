import re


def parse_github_pr_url(pr_url: str) -> tuple[str, str, int] | None:
    match = re.match(
        r"^https://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)/pull/(?P<number>\d+)/?$",
        pr_url,
    )
    if not match:
        return None

    return (
        match.group("owner"),
        match.group("repo"),
        int(match.group("number")),
    )
