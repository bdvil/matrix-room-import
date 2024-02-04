from urllib import parse


def sanitize_url(hs_url: str) -> str:
    if hs_url[-1] == "/":
        return hs_url[:-1]
    return hs_url


def ping(hs_url: str, as_id: str):
    return sanitize_url(hs_url) + f"/_matrix/client/v1/appservice/{as_id}/ping"


def whoami(hs_url: str, user_id: str):
    query = parse.urlencode({"user_id": user_id})
    return sanitize_url(hs_url) + f"/_matrix/client/v3/account/whoami?{query}"
