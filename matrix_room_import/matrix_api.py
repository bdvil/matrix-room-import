from typing import Any, Literal
from urllib import parse

from matrix_room_import.appservice.types import RoomEventFilter


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


def invite_room(
    hs_url: str, room_id: str, user_id: str | None = None, ts: int | None = None
) -> str:
    query_data: dict[str, str] = {}
    if user_id is not None:
        query_data["user_id"] = user_id
    if ts is not None:
        query_data["ts"] = str(ts)
    query = urlencode(query_data)
    return sanitize_url(hs_url) + f"/_matrix/client/v3/rooms/{room_id}/invite?{query}"


def room_join(
    hs_url: str, room_id: str, user_id: str | None = None, ts: int | None = None
) -> str:
    query_data: dict[str, str] = {}
    if user_id is not None:
        query_data["user_id"] = user_id
    if ts is not None:
        query_data["ts"] = str(ts)
    query = urlencode(query_data)
    return sanitize_url(hs_url) + f"/_matrix/client/v3/rooms/{room_id}/join?{query}"


def create_room(hs_url: str, user_id: str | None = None, ts: int | None = None) -> str:
    query_data: dict[str, str] = {}
    if user_id is not None:
        query_data["user_id"] = user_id
    if ts is not None:
        query_data["ts"] = str(ts)
    query = urlencode(query_data)
    return sanitize_url(hs_url) + f"/_matrix/client/v3/createRoom?{query}"


def delete_room(hs_url: str, room_id: str) -> str:
    return sanitize_url(hs_url) + f"/_synapse/admin/v1/rooms/{room_id}"


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


def create_media(hs_url: str) -> str:
    return sanitize_url(hs_url) + "/_matrix/media/v1/create"


def upload_media(
    hs_url: str, server_name: str, media_id: str, filename: str | None = None
) -> str:
    query_data: dict[str, str] = {}
    if filename is not None:
        query_data["filename"] = filename
    query = urlencode(query_data)
    return (
        sanitize_url(hs_url)
        + f"/_matrix/media/v3/upload/{server_name}/{media_id}?{query}"
    )


def download_media(
    hs_url: str,
    server_name: str,
    media_id: str,
    allow_redirect: bool = False,
    allow_remote: bool = False,
    timeout_ms: int | None = None,
) -> str:
    query_data: dict[str, str] = {}
    if allow_redirect:
        query_data["allow_redirect"] = str(int(allow_redirect))
    if allow_remote:
        query_data["allow_remote"] = str(int(allow_remote))
    if timeout_ms is not None:
        query_data["timeout_ms"] = str(timeout_ms)
    query = urlencode(query_data)
    return (
        sanitize_url(hs_url)
        + f"/_matrix/media/v3/download/{server_name}/{media_id}?{query}"
    )


def get_room_state(
    hs_url: str,
    room_id: str,
    user_id: str | None = None,
) -> str:
    query_data: dict[str, str] = {}
    if user_id is not None:
        query_data["user_id"] = user_id
    query = urlencode(query_data)
    return sanitize_url(hs_url) + f"/_matrix/client/v3/rooms/{room_id}/state?{query}"


def get_room_messages(
    hs_url: str,
    room_id: str,
    dir: Literal["b", "f"],
    filter: RoomEventFilter | None = None,
    from_: str | None = None,
    limit: int | None = None,
    to: str | None = None,
    user_id: str | None = None,
) -> str:
    query_data: dict[str, str] = {}
    if dir is not None:
        query_data["dir"] = dir
    if filter is not None:
        query_data["filter"] = filter.model_dump_json(
            exclude_unset=True, by_alias=True
        ).replace("\n", "")
    if from_ is not None:
        query_data["from"] = from_
    if limit is not None:
        query_data["limit"] = str(limit)
    if to is not None:
        query_data["to"] = to
    if user_id is not None:
        query_data["user_id"] = user_id
    query = urlencode(query_data)
    return sanitize_url(hs_url) + f"/_matrix/client/v3/rooms/{room_id}/messages?{query}"


def redact_message(
    hs_url: str,
    room_id: str,
    event_id: str,
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
        + f"/_matrix/client/v3/rooms/{room_id}/redact/{event_id}/{txn_id}?{query}"
    )
