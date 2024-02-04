from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from matrix_migration.appservice.events import RoomJoinRules, RoomMessage


class ErrorResponse(BaseModel):
    errcode: str
    error: str | None = None
    retry_after_ms: int | None = None


class Signed(BaseModel):
    mxid: str
    signatures: Any
    token: str


class Invite(BaseModel):
    displayname: str
    signed: Signed


class EventContent(BaseModel):
    avatar_url: str
    displayname: str | None
    is_direct: bool
    join_authorised_via_users_server: str
    membership: str
    reason: str
    third_party_invite: Invite


class UnsignedData(BaseModel):
    age: int
    prev_content: Any
    redacted_because: "ClientEvent"
    transaction_id: str


class ClientEvent(BaseModel):
    content: RoomJoinRules | RoomMessage | Any
    event_id: str
    origin_server_ts: int
    room_id: str
    sender: str
    state_key: str | None = None
    type: str
    unsigned: Any | None = None


class ClientEvents(BaseModel):
    events: list[ClientEvent]


class ThirdPartySigned(BaseModel):
    mxid: str
    sender: str
    signatures: Mapping[str, Mapping[str, str]]
    token: str


class JoinRoomBody(BaseModel):
    reason: str | None = None
    third_party_signed: ThirdPartySigned | None = None


class JoinRoomResponse(BaseModel):
    room_id: str
