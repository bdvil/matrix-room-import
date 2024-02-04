from typing import Any

from pydantic import BaseModel


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
    content: Any
    event_id: str
    origin_server_ts: int
    room_id: str
    sender: str
    state_key: str | None = None
    type: str
    unsigned: UnsignedData | None = None


class ClientEvents(BaseModel):
    events: list[ClientEvent]
