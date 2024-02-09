from urllib import parse

from matrix_migration.appservice.types import PresenceEnum


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


def sync(
    hs_url: str,
    filter: str | None,
    full_state: bool = False,
    set_presence: PresenceEnum | None = None,
    since: str | None = None,
    timeout: int = 0,
) -> str:
    query_data = {"full_state": full_state, "timeout": timeout}
    if filter is not None:
        query_data["filter"] = filter
    if set_presence is not None:
        query_data["set_presence"] = set_presence.value
    if since is not None:
        query_data["since"] = since
    query = parse.urlencode(query_data)
    return sanitize_url(hs_url) + f"/_matrix/client/v3/sync?{query}"
