from typing import Any
from urllib import parse


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


def room_join(
    hs_url: str, room_id: str, user_id: str | None = None, ts: int | None = None
) -> str:
    query_data: dict[str, str] = {}
    if user_id is not None:
        query_data["user_id"] = user_id
    if ts is not None:
        query_data["ts"] = str(ts)
    return sanitize_url(hs_url) + f"/_matrix/client/v3/rooms/{room_id}/join"


def create_room(hs_url: str, user_id: str | None = None, ts: int | None = None) -> str:
    query_data: dict[str, str] = {}
    if user_id is not None:
        query_data["user_id"] = user_id
    if ts is not None:
        query_data["ts"] = str(ts)
    query = urlencode(query_data)
    return sanitize_url(hs_url) + f"/_matrix/client/v3/createRoom?{query}"


def delete_room(hs_url: str, room_id: str) -> str:
    return sanitize_url(hs_url) + f"/_synapse/admin/v2/rooms/{room_id}"


def room_send_event(
    hs_url: str,
    room_id: str,
    event_type: str,
    txn_id: str,
    user_id: str | None = None,
    ts: int | None = None,
) -> str:
    query_data: dict[str, str] = {}
    if user_id is not None:
        query_data["user_id"] = user_id
    if ts is not None:
        query_data["ts"] = str(ts)
    query = urlencode(query_data)
    return (
        sanitize_url(hs_url)
        + f"/_matrix/client/v3/rooms/{room_id}/send/{event_type}/{txn_id}?{query}"
    )


def room_send_state_event(
    hs_url: str,
    room_id: str,
    event_type: str,
    state_key: str,
    user_id: str | None = None,
    ts: int | None = None,
) -> str:
    query_data: dict[str, str] = {}
    if user_id is not None:
        query_data["user_id"] = user_id
    if ts is not None:
        query_data["ts"] = str(ts)
    query = urlencode(query_data)
    return (
        sanitize_url(hs_url)
        + f"/_matrix/client/v3/rooms/{room_id}/state/{event_type}/{state_key}?{query}"
    )
