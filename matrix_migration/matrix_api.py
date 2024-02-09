from typing import Any
from urllib import parse

from matrix_migration.appservice.types import PresenceEnum


def urlencode(data: dict[str, Any]) -> str:
    return parse.urlencode(
        [(k, str(v).lower() if isinstance(v, bool) else v) for k, v in data.items()]
    )


def sanitize_url(hs_url: str) -> str:
    if hs_url[-1] == "/":
        return hs_url[:-1]
    return hs_url


def ping(hs_url: str, as_id: str) -> str:
    return sanitize_url(hs_url) + f"/_matrix/client/v1/appservice/{as_id}/ping"


def whoami(hs_url: str, user_id: str) -> str:
    query = urlencode({"user_id": user_id})
    return sanitize_url(hs_url) + f"/_matrix/client/v3/account/whoami?{query}"


def profile(hs_url: str, user_id: str) -> str:
    return sanitize_url(hs_url) + f"/_matrix/client/v3/profile/{user_id}"


def profile_displayname(hs_url: str, user_id: str) -> str:
    return sanitize_url(hs_url) + f"/_matrix/client/v3/profile/{user_id}/displayname"


def room_join(hs_url: str, room_id: str) -> str:
    return sanitize_url(hs_url) + f"/_matrix/client/v3/rooms/{room_id}/join"


def room_send_event(hs_url: str, room_id: str, event_type: str, txn_id: str) -> str:
    return (
        sanitize_url(hs_url)
        + f"/_matrix/client/v3/rooms/{room_id}/send/{event_type}/{txn_id}"
    )


def query_key(hs_url: str) -> str:
    return sanitize_url(hs_url) + "/_matrix/client/v3/keys/query"


def sync(
    hs_url: str,
    filter: str | None,
    full_state: bool = False,
    set_presence: PresenceEnum | None = None,
    since: str | None = None,
    timeout: int = 0,
    user_id: str | None = None,
) -> str:
    query_data = {"full_state": full_state, "timeout": timeout}
    if filter is not None:
        query_data["filter"] = filter
    if set_presence is not None:
        query_data["set_presence"] = set_presence.value
    if since is not None:
        query_data["since"] = since
    if user_id is not None:
        query_data["user_id"] = user_id
    query = urlencode(query_data)
    return sanitize_url(hs_url) + f"/_matrix/client/v3/sync?{query}"
