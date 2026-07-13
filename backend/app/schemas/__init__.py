from pydantic import BaseModel, Field
from datetime import datetime


# Auth
class SendCodeReq(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")


class LoginReq(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    code: str = Field(..., min_length=4, max_length=6)


class TokenResp(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResp(BaseModel):
    id: str
    phone: str
    industry: str | None
    company_name: str | None
    plan_type: str

    class Config:
        from_attributes = True


class UpdateProfileReq(BaseModel):
    industry: str | None = None
    company_name: str | None = None


# Copywriting
class GenerateCopywritingReq(BaseModel):
    keywords: str = Field(..., min_length=1, max_length=200)
    style: str = Field(default="口播", pattern=r"^(口播|展示|促销|剧情)$")
    count: int = Field(default=5, ge=1, le=10)


class ParseLinkReq(BaseModel):
    url: str = Field(..., min_length=5)


class CopywritingResp(BaseModel):
    id: str
    title: str
    body: str
    tags: str | None
    style: str
    source: str
    is_favorited: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Material
class MaterialResp(BaseModel):
    id: str
    type: str
    file_name: str
    file_url: str
    thumbnail_url: str | None
    duration: float | None
    size: int
    tags: list[str]
    created_at: datetime

    class Config:
        from_attributes = True


class FolderResp(BaseModel):
    id: str
    name: str
    parent_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class CreateFolderReq(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: str | None = None


# Edit Task
class CreateEditTaskReq(BaseModel):
    material_ids: list[str] = Field(..., min_length=3)
    copywriting_id: str | None = None
    template_id: str = Field(default="default")
    count: int = Field(default=5, ge=1, le=50)
    duration: int = Field(default=30, ge=15, le=120)  # seconds
    ratio: str = Field(default="9:16")
    voice: str = Field(default="female")  # female/male/none
    subtitle_style: str = Field(default="white_black_border")


class EditTaskResp(BaseModel):
    id: str
    material_ids: list[str]
    status: str
    progress: int
    output_urls: list[str]
    error_message: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# Publish Task
class CreatePublishTaskReq(BaseModel):
    video_url: str
    platform_account_id: str
    title: str = Field(..., max_length=500)
    schedule_type: str = Field(default="now", pattern=r"^(now|timed)$")
    schedule_time: datetime | None = None


class PublishTaskResp(BaseModel):
    id: str
    video_url: str
    platform_account_id: str
    title: str
    schedule_type: str
    schedule_time: datetime | None
    status: str
    publish_result: dict | None
    metrics: dict
    created_at: datetime

    class Config:
        from_attributes = True


# Platform Account
class BindAccountReq(BaseModel):
    platform: str = Field(..., pattern=r"^(douyin|kuaishou|xhs|shipinhao)$")
    auth_token: str


class PlatformAccountResp(BaseModel):
    id: str
    platform: str
    account_name: str
    avatar: str | None
    fans_count: int
    auth_status: str
    created_at: datetime

    class Config:
        from_attributes = True
