from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, RootModel, field_serializer, model_validator


class MsgType(str, Enum):
    text = "m.text"
    emote = "m.emote"
    image = "m.image"
    video = "m.video"
    file = "m.file"
    audio = "m.audio"
    location = "m.location"
    notice = "m.notice"
    server_notice = "m.server_notice"
    key_verification_request = "m.key.verification.request"


class ErrorResponse(BaseModel):
    statuscode: int
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


class Mentions(BaseModel):
    user_ids: Sequence[str] | None = None


class InReplyTo(BaseModel):
    event_id: str


class RelatesTo(BaseModel):
    in_reply_to: InReplyTo | None = Field(alias="m.in_reply_to", default=None)
    rel_type: str | None = None
    event_id: str | None = None
    is_falling_back: bool | None = None


class RoomMessage(BaseModel):
    msgtype: MsgType
    body: str

    format: str | None = None
    formatted_body: str | None = None

    mentions: Mentions | None = Field(serialization_alias="m.mentions", default=None)
    relates_to: RelatesTo | None = Field(
        serialization_alias="m.relates_to", default=None
    )

    file: str | None = None
    filename: str | None = None
    info: ImageInfo | None = None
    url: str | None = None

    @field_serializer("msgtype")
    def serialize_msgtype(self, value: MsgType, _) -> str:
        return value.value

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


class Event(BaseModel):
    content: Mapping[str, Any]
    type: str
    sender: str | None = None


class ToDeviceEvent(Event):
    to_user_id: str
    to_device_id: str


class ClientEvent(Event):
    event_id: str
    origin_server_ts: int
    state_key: str | None = None
    unsigned: Any | None = None
    room_id: str


ArrayOfClientEvents = RootModel[Sequence[ClientEvent]]


class ClientEvents(BaseModel):
    events: Sequence[ClientEvent]
    ephemeral: Sequence[Event] | None = Field(
        alias="de.sorunome.msc2409.ephemeral", default=None
    )
    to_device: Sequence[ToDeviceEvent] | None = Field(
        alias="de.sorunome.msc2409.to_device", default=None
    )


class PreviousRoom(BaseModel):
    event_id: str
    room_id: str


class CreationContent(BaseModel):
    creator: str | None = None
    federate: bool | None = Field(serialization_alias="m.federate", default=None)
    predecessor: PreviousRoom | None = None
    room_version: str | None = None
    type: str | None = None


class StateEvent(BaseModel):
    content: Any
    state_key: str | None = None
    type: str


class Invite3pid(BaseModel):
    address: str
    id_access_token: str
    id_server: str
    medium: str


class PowerLevelContent(BaseModel):
    ban: int | None = None
    events: Mapping[str, int] | None = None
    events_default: int | None = None
    invite: int | None = None
    kick: int | None = None
    notifications: Mapping[str, int] | None = None
    redact: int | None = None
    state_default: int | None = None
    users: Mapping[str, int] | None = None
    users_default: int | None = None


class CreateRoomBody(BaseModel):
    creation_content: CreationContent | None = None
    initial_state: list[StateEvent] | None = None
    invite: list[str] | None = None
    invite_3pid: list[Invite3pid] | None = None
    is_direct: bool | None = None
    name: str | None = None
    power_level_content_override: PowerLevelContent | None = None
    preset: Literal["private_chat", "public_chat", "trusted_private_chat"] | None = None
    room_alias_name: str | None = None
    room_version: str | None = None
    topic: str | None = None
    visibility: Literal["public", "private"] | None = None


class CreateRoomResponse(BaseModel):
    room_id: str


class RedactMessageBody(BaseModel):
    reason: str | None = None


class RedactMessageResponse(BaseModel):
    event_id: str | None = None


class DeleteRoomBody(BaseModel):
    new_room_user_id: str | None = None
    room_name: str | None = None
    message: str | None = None
    block: bool | None = None
    purge: bool | None = None


class DeleteRoomResponse(BaseModel):
    kicked_users: Sequence[str]
    failed_to_kick_users: Sequence[str]
    local_aliases: Sequence[str]
    new_room_id: str | None = None


class InviteToRoomBody(BaseModel):
    reason: str | None = None
    user_id: str


class InviteToRoomResponse(BaseModel):
    pass


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


class LoginType(str, Enum):
    password = "m.login.password"
    token = "m.login.token"
    application_service = "m.login.application_service"


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

    @field_serializer("type")
    def serialize_type(self, value: LoginType, _) -> str:
        return value.value


class PingBody(BaseModel):
    transaction_id: str | None = None


class PingResponse(BaseModel):
    duration_ms: int


class WhoAmIResponse(BaseModel):
    device_id: str | None = None
    is_guest: bool = False
    user_id: str


class ProfileResponse(BaseModel):
    avatar_url: str | None = None
    displayname: str | None = None


class ProfileDisplayNameBody(BaseModel):
    displayname: str


class ProfileDisplayNameResponse(BaseModel):
    pass


class HomeserverInformation(BaseModel):
    base_url: str


class IdentityServerInformation(BaseModel):
    base_url: str


class DiscoveryInformation(BaseModel):
    homeserver: HomeserverInformation = Field(alias="m.homeserver")
    identity_server: IdentityServerInformation | None = Field(
        alias="m.identity_server", default=None
    )


class LoginResponse(BaseModel):
    access_token: str
    device_id: str
    expires_in_ms: int | None = None
    home_server: str | None = None  # deprecated
    refresh_token: str | None = None
    user_id: str
    well_known: DiscoveryInformation | None = None


class RoomSendEventResponse(BaseModel):
    event_id: str


class CreateMediaResponse(BaseModel):
    content_uri: str
    unused_expires_at: int | None = None


class UploadMediaResponse(BaseModel):
    pass


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
