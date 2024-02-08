from collections.abc import Mapping
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


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


class MembershipEnum(Enum):
    invite = "invite"
    join = "join"
    knock = "knock"
    leave = "leave"
    ban = "ban"


class PresenceEnum(Enum):
    online = "online"
    offline = "offline"
    unavailable = "unavailable"


class RoomMember(BaseModel):
    membership: MembershipEnum
    avatar_url: str | None = None
    displayname: str | None = None
    is_direct: bool | None = None
    join_authorised_via_users_server: str | None = None
    reason: str | None = None
    third_party_invite: Invite | None = None


class EventContent(BaseModel):
    avatar_url: str | None = None
    displayname: str | None
    is_direct: bool | None = None
    join_authorised_via_users_server: str | None = None
    membership: str
    reason: str | None = None
    third_party_invite: Invite | None = None


class UnsignedDataWithoutRoomId(BaseModel):
    age: int | None = None
    prev_content: EventContent | None = None
    redacted_because: "ClientEventWithoutRoomID | None" = None
    transaction_id: str | None = None


class UnsignedData(BaseModel):
    age: int | None = None
    prev_content: EventContent | None = None
    redacted_because: "ClientEvent | None" = None
    transaction_id: str


class ClientEventWithoutRoomID(BaseModel):
    content: dict[str, Any]
    event_id: str
    origin_server_ts: int
    sender: str
    state_key: str | None = None
    type: str
    unsigned: UnsignedDataWithoutRoomId | None = None


class ClientEvent(BaseModel):
    content: dict[str, Any]
    event_id: str
    origin_server_ts: int
    sender: str
    state_key: str | None = None
    type: str
    unsigned: UnsignedData | None = None
    room_id: str


class ClientEvents(BaseModel):
    events: list[ClientEvent]


class JoinRoomBody(BaseModel):
    reason: str | None = None
    third_party_signed: ThirdPartySigned | None = None


class JoinRoomResponse(BaseModel):
    room_id: str


class Event(BaseModel):
    content: dict[str, Any]
    type: str


class AccountData(BaseModel):
    events: list[Event] | None = None


class DeviceLists(BaseModel):
    changed: list[str] | None = None
    left: list[str] | None = None


class Presence(BaseModel):
    events: list[Event] | None = None


class StrippedStateEvent(BaseModel):
    content: EventContent
    sender: str
    state_key: str
    type: str


class Ephemeral(BaseModel):
    events: list[Event] | None = None


class State(BaseModel):
    events: list[ClientEventWithoutRoomID] | None = None


class RoomSummary(BaseModel):
    heroes: list[str] | None = Field(alias="m.heroes", default=None)
    invited_member_count: int | None = Field(
        alias="m.invited_member_count", default=None
    )
    joined_member_count: int | None = Field(
        alias="m.joined_member_count", default=None
    )


class InviteState(BaseModel):
    events: list[StrippedStateEvent] | None = None


class InvitedRoom(BaseModel):
    invite_state: InviteState | None = None


class JoinedRoom(BaseModel):
    account_data: AccountData | None = None
    ephemeral: Ephemeral | None = None
    state: State | None = None
    summary: RoomSummary | None = None


class KnockedRoom(BaseModel):
    pass


class LeftRoom(BaseModel):
    pass


class ThreadNotificationCounts(BaseModel):
    highlight_count: int | None = None
    notification_count: int | None = None


class UnreadNotificationCounts(BaseModel):
    highlight_count: int | None = None
    notification_count: int | None = None


class Rooms(BaseModel):
    invite: InvitedRoom | None = None
    join: JoinedRoom | None = None
    knock: KnockedRoom | None = None
    leave: LeftRoom | None = None


class ToDevice(BaseModel):
    pass


class SyncResponse(BaseModel):
    account_data: AccountData | None = None
    device_lists: DeviceLists | None = None
    device_one_time_keys_count: dict[str, int] | None = None
    next_batch: str
    presence: Presence | None = None
    rooms: Rooms | None = None
    to_device: ToDevice | None = None
