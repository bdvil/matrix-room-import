from collections.abc import Mapping
from enum import Enum
from typing import Any

from pydantic import BaseModel, model_validator


class ErrorResponse(BaseModel):
    errcode: str
    error: str | None = None
    retry_after_ms: int | None = None


class Signed(BaseModel):
    mxid: str
    signatures: Any
    token: str


class ThirdPartySigned(Signed):
    sender: str


class Invite(BaseModel):
    displayname: str
    signed: Signed


class AllowCondition(BaseModel):
    room_id: str | None = None
    type: str

    @model_validator(mode="after")
    def room_id_validation(self):
        if self.type == "m.room_membership" and self.room_id is None:
            raise ValueError(
                "room_id should not be empty for type m.room_membership"
            )
        return self


class RoomJoinRules(BaseModel):
    allow: list[AllowCondition] | None = None
    join_rule: str


class JWK(BaseModel):
    kty: str
    key_ops: list[str]
    alg: str
    k: str
    ext: bool


class EncryptedFile(BaseModel):
    url: str
    key: JWK
    iv: str
    hashes: Mapping[str, str]
    v: str


class ThumbnailInfo(BaseModel):
    h: int | None = None
    w: int | None = None
    mimetype: str | None = None
    size: int | None = None


class ImageInfo(BaseModel):
    h: int | None = None
    w: int | None = None
    mimetype: str | None = None
    size: int | None = None
    thumbnail_file: EncryptedFile | None = None
    thumbnail_info: ThumbnailInfo | None = None
    thumbnail_url: str | None = None


class RoomMessage(BaseModel):
    msgtype: str
    body: str

    format: str | None = None
    formatted_body: str | None = None

    file: str | None = None
    filename: str | None = None
    info: ImageInfo | None = None
    url: str | None = None

    @model_validator(mode="after")
    def room_id_validation(self):
        if (
            self.msgtype in ["m.image", "m.file"]
            and self.file is None
            and self.url is None
        ):
            raise ValueError(
                f"either url or file should be provided for msgtype {self.msgtype}"
            )
        return self


class Membership(Enum):
    invite = "invite"
    join = "join"
    knock = "knock"
    leave = "leave"
    ban = "ban"


class RoomMember(BaseModel):
    avatar_url: str | None = None
    displayname: str | None = None
    is_direct: bool | None = None
    join_authorised_via_users_server: str | None = None
    membership: Membership
    reason: str | None = None
    third_party_invite: Invite


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
    content: RoomJoinRules | RoomMessage | RoomMember | Any
    event_id: str
    origin_server_ts: int
    room_id: str
    sender: str
    state_key: str | None = None
    type: str
    unsigned: Any | None = None


class ClientEvents(BaseModel):
    events: list[ClientEvent]


class JoinRoomBody(BaseModel):
    reason: str | None = None
    third_party_signed: ThirdPartySigned | None = None


class JoinRoomResponse(BaseModel):
    room_id: str
