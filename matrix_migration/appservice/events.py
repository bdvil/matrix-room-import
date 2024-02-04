from collections.abc import Mapping

from pydantic import BaseModel, model_validator


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
