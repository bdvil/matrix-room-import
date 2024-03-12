from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from matrix_room_import.appservice.types import Mentions, MsgType, RelatesTo


class EventBase(BaseModel):
    sender: str
    origin_server_ts: int
    unsigned: Any
    event_id: str
    room_id: str


class StateEventBase(EventBase):
    state_key: str


class MemberContent(BaseModel):
    membership: str
    displayname: str
    avatar_url: str
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
    info: Any | None = None
    relates_to: RelatesTo | None = Field(alias="m.relates_to", default=None)


class MessageEvent(EventBase):
    type: Literal["m.room.message"]
    content: MessageContent


class GenericEvent(EventBase):
    type: Literal[
        "m.room.encrypted",
        "org.matrix.msc3381.poll.start",
        "org.matrix.msc3381.poll.end",
    ]
    content: Any


Event = Annotated[
    MemberEvent
    | EncryptionEvent
    | GuestAccessEvent
    | JoinRulesEvent
    | HistoryVisibilityEvent
    | RoomNameEvent
    | TopicEvent
    | MessageEvent
    | GenericEvent,
    Field(discriminator="type"),
]


class ExportFile(BaseModel):
    room_name: str
    room_creator: str
    topic: str
    export_date: str
    exported_by: str
    messages: list[Event]
