from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, RootModel, model_validator


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
            raise ValueError("room_id should not be empty for type m.room_membership")
        return self


class RoomJoinRules(BaseModel):
    allow: Sequence[AllowCondition] | None = None
    join_rule: str


class JWK(BaseModel):
    kty: str
    key_ops: Sequence[str]
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
    displayname: str | None = None
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
    transaction_id: str | None = None


class ClientEventWithoutRoomID(BaseModel):
    content: Mapping[str, Any]
    event_id: str
    origin_server_ts: int
    sender: str
    state_key: str | None = None
    type: str
    unsigned: UnsignedDataWithoutRoomId | None = None


class ClientEvent(BaseModel):
    content: Mapping[str, Any]
    event_id: str
    origin_server_ts: int
    sender: str
    state_key: str | None = None
    type: str
    unsigned: UnsignedData | None = None
    room_id: str


class ClientEvents(BaseModel):
    events: Sequence[ClientEvent]


class JoinRoomBody(BaseModel):
    reason: str | None = None
    third_party_signed: ThirdPartySigned | None = None


class JoinRoomResponse(BaseModel):
    room_id: str


class QueryKeysBody(BaseModel):
    device_keys: Mapping[str, Sequence[str]]
    timeout: int


class UserIdentifierUser(BaseModel):
    type: Literal["m.id.user"] = "m.id.user"
    user: str  # user_id or user localpart


class UserIdentifierThirdParty(BaseModel):
    type: Literal["m.id.thirdparty"] = "m.id.thirdparty"
    medium: str
    address: str


class UserIdentifierPhone(BaseModel):
    type: Literal["m.id.phone"] = "m.id.phone"
    country: str
    phone: str


class LoginType(Enum):
    password = "m.login.password"
    token = "m.login.token"


class LoginBody(BaseModel):
    device_id: str | None = None
    identifier: (
        UserIdentifierUser | UserIdentifierThirdParty | UserIdentifierPhone | None
    ) = Field(discriminator="type", default=None)
    initial_device_display_name: str | None = None
    password: str | None = None
    refresh_token: bool = False
    token: str | None = None
    type: LoginType


class HomeserverInformation(BaseModel):
    base_url: str


class IdentityServerInformation(BaseModel):
    base_url: str


class DiscoveryInformation(BaseModel):
    homeserver: HomeserverInformation = Field(alias="m.homeserver")
    identity_server: IdentityServerInformation = Field(alias="m.identity_server")


class LoginResponse(BaseModel):
    access_token: str
    device_id: str
    expires_in_ms: int | None = None
    home_server: str | None = None  # deprecated
    refresh_token: str | None = None
    user_id: str
    well_known: DiscoveryInformation | None = None


Signatures = RootModel[Mapping[str, Mapping[str, str]]]


class CrossSigningKey(BaseModel):
    keys: Mapping[str, str]
    signatures: Signatures | None = None
    usage: Sequence[str]
    user_id: str


class UnsignedDeviceInfo(BaseModel):
    device_display_name: str | None = None


class DeviceInformation(BaseModel):
    algorithms: Sequence[str]
    device_id: str
    keys: Mapping[str, str]
    signatures: Signatures
    unsigned: UnsignedDeviceInfo | None = None
    user_id: str


class QueryKeysResponse(BaseModel):
    device_keys: Mapping[str, Mapping[str, DeviceInformation]] | None = None
    failures: Mapping[str, Any] | None = None
    master_keys: Mapping[str, CrossSigningKey] | None = None
    self_signing_keys: Mapping[str, CrossSigningKey] | None = None
    user_signing_keys: Mapping[str, CrossSigningKey] | None = None


class Event(BaseModel):
    content: Mapping[str, Any]
    type: str
    sender: str | None = None


class AccountData(BaseModel):
    events: Sequence[Event] | None = None


class DeviceLists(BaseModel):
    changed: Sequence[str] | None = None
    left: Sequence[str] | None = None


class Presence(BaseModel):
    events: Sequence[Event] | None = None


class StrippedStateEvent(BaseModel):
    content: Mapping[str, Any]
    sender: str
    state_key: str
    type: str


class Ephemeral(BaseModel):
    events: Sequence[Event] | None = None


class State(BaseModel):
    events: Sequence[ClientEventWithoutRoomID] | None = None


class RoomSummary(BaseModel):
    heroes: Sequence[str] | None = Field(alias="m.heroes", default=None)
    invited_member_count: int | None = Field(
        alias="m.invited_member_count", default=None
    )
    joined_member_count: int | None = Field(alias="m.joined_member_count", default=None)


class InviteState(BaseModel):
    events: Sequence[StrippedStateEvent] | None = None


class InvitedRoom(BaseModel):
    invite_state: InviteState | None = None


class Timeline(BaseModel):
    events: Sequence[ClientEventWithoutRoomID]
    limited: bool | None = None
    prev_batch: str | None = None


class ThreadNotificationCounts(BaseModel):
    highlight_count: int | None = None
    notification_count: int | None = None


class UnreadNotificationCounts(BaseModel):
    notification_count: int | None = None
    highlight_count: int | None = None


class JoinedRoom(BaseModel):
    account_data: AccountData | None = None
    ephemeral: Ephemeral | None = None
    state: State | None = None
    summary: RoomSummary | None = None
    timeline: Timeline | None = None
    unread_notifications: UnreadNotificationCounts | None = None
    unread_thread_notifications: ThreadNotificationCounts | None = None


class KnockState(BaseModel):
    events: Sequence[StrippedStateEvent] | None = None


class KnockedRoom(BaseModel):
    knock_state: KnockState | None = None


class LeftRoom(BaseModel):
    account_data: AccountData | None = None
    state: State | None = None
    timeline: Timeline | None = None


class Rooms(BaseModel):
    invite: InvitedRoom | None = None
    join: JoinedRoom | None = None
    knock: KnockedRoom | None = None
    leave: LeftRoom | None = None


class ToDevice(BaseModel):
    events: Sequence[Event] | None = None


class SyncResponse(BaseModel):
    account_data: AccountData | None = None
    device_Sequences: DeviceLists | None = None
    device_one_time_keys_count: Mapping[str, int] | None = None
    next_batch: str
    presence: Presence | None = None
    rooms: Rooms | None = None
    to_device: ToDevice | None = None
