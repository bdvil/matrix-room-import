from collections.abc import Sequence
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Discriminator, Field, Tag

from matrix_room_import.appservice.types import Mentions, MsgType, RelatesTo


class EventBase(BaseModel):
    sender: str
    origin_server_ts: int
    unsigned: Any
    event_id: str
    room_id: str
    age: int | None = None
    user_id: str | None = None


class StateEventBase(EventBase):
    state_key: str


class MemberContent(BaseModel):
    membership: str
    displayname: str | None = None
    avatar_url: str | None = None
    join_authorised_via_users_server: str | None = None


class MemberEvent(StateEventBase):
    type: Literal["m.room.member"]
    content: MemberContent


class EncryptionEvent(StateEventBase):
    type: Literal["m.room.encryption"]
    content: Any


class GuestAccessContent(BaseModel):
    guest_access: str


class GuestAccessEvent(StateEventBase):
    type: Literal["m.room.guest_access"]
    content: GuestAccessContent


class JoinRuleAllow(BaseModel):
    type: str
    room_id: str


class JoinRulesContent(BaseModel):
    join_rule: str
    allow: list[JoinRuleAllow] | None = None


class JoinRulesEvent(StateEventBase):
    type: Literal["m.room.join_rules"]
    content: JoinRulesContent


class HistoryVisibilityContent(BaseModel):
    history_visibility: str


class HistoryVisibilityEvent(StateEventBase):
    type: Literal["m.room.history_visibility"]
    content: HistoryVisibilityContent


class RoomNameContent(BaseModel):
    name: str


class RoomNameEvent(StateEventBase):
    type: Literal["m.room.name"]
    content: RoomNameContent


class TopicContent(BaseModel):
    topic: str


class TopicEvent(StateEventBase):
    type: Literal["m.room.topic"]
    content: TopicContent


class MessageContent(BaseModel):
    msgtype: MsgType
    body: str
    format: Any | None = None
    formatted_body: Any | None = None
    mentions: Mentions | None = Field(alias="m.mentions", default=None)
    file: Any | None = None
    info: dict[str, Any] = Field(default_factory=dict)
    relates_to: RelatesTo | None = Field(alias="m.relates_to", default=None)


class MessageEvent(EventBase):
    type: Literal["m.room.message"]
    content: MessageContent


class ReactionContent(BaseModel):
    relates_to: RelatesTo | None = Field(alias="m.relates_to", default=None)


class ReactionEvent(EventBase):
    type: Literal["m.room.reaction"]
    content: ReactionContent


class SkippedEvent(EventBase):
    type: str
    content: Any


class GenericEvent(EventBase):
    type: str
    content: Any


class SpaceChildContent(BaseModel):
    via: Sequence[str]
    order: str | None = None
    suggested: bool | None = None


class SpaceChildEvent(StateEventBase):
    type: Literal["m.space.child"]
    content: SpaceChildContent


skipped_event_types = ["m.room.encrypted"]

event_types = [
    "m.room.member",
    "m.space.child",
    "m.room.encrypted",
    "m.room.reaction",
    "m.room.message",
    "m.room.topic",
    "m.room.name",
    "m.room.history_visibility",
    "m.room.join_rules",
    "m.room.guest_access",
    "m.room.encryption",
]


def get_event_type(event_type) -> str:
    if isinstance(event_type, dict):
        t = event_type.get("type", "__default__")
    else:
        t = getattr(event_type, "type", "__default__")
    if t in skipped_event_types:
        return "__skipped__"
    if t in event_type:
        return t
    return "__default__"


Event = Annotated[
    Annotated[MemberEvent, Tag("m.room.member")]
    | Annotated[EncryptionEvent, Tag("m.room.encrypted")]
    | Annotated[GuestAccessEvent, Tag("m.room.guest_access")]
    | Annotated[JoinRulesEvent, Tag("m.room.join_rules")]
    | Annotated[HistoryVisibilityEvent, Tag("m.room.history_visibility")]
    | Annotated[RoomNameEvent, Tag("m.room.name")]
    | Annotated[TopicEvent, Tag("m.room.topic")]
    | Annotated[SpaceChildEvent, Tag("m.space.child")]
    | Annotated[MessageEvent, Tag("m.room.message")]
    | Annotated[ReactionEvent, Tag("m.room.reaction")]
    | Annotated[SkippedEvent, Tag("__skipped__")]
    | Annotated[GenericEvent, Tag("__default__")],
    Field(discriminator=Discriminator(get_event_type)),
]


class ExportFile(BaseModel):
    room_name: str
    room_creator: str
    topic: str
    export_date: str
    exported_by: str
    messages: list[Event]
