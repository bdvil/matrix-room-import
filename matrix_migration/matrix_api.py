from urllib import parse


def sanitize_url(hs_url: str) -> str:
    if hs_url[-1] == "/":
        return hs_url[:-1]
    return hs_url


def ping(hs_url: str, as_id: str) -> str:
    return sanitize_url(hs_url) + f"/_matrix/client/v1/appservice/{as_id}/ping"


def whoami(hs_url: str, user_id: str) -> str:
    query = parse.urlencode({"user_id": user_id})
    return sanitize_url(hs_url) + f"/_matrix/client/v3/account/whoami?{query}"


def profile(hs_url: str, user_id: str) -> str:
    return sanitize_url(hs_url) + f"/_matrix/client/v3/profile/{user_id}"


def profile_displayname(hs_url: str, user_id: str) -> str:
    return (
        sanitize_url(hs_url)
        + f"/_matrix/client/v3/profile/{user_id}/displayname"
    )


def room_join(hs_url: str, room_id: str) -> str:
    return sanitize_url(hs_url) + f"/_matrix/client/v3/rooms/{room_id}/join"


def room_send_event(
    hs_url: str, room_id: str, event_type: str, txn_id: str
) -> str:
    return (
        sanitize_url(hs_url)
        + f"/_matrix/client/v3/rooms/{room_id}/send/{event_type}/{txn_id}"
    )
