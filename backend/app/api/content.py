from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import CopywritingTemplate, Material, MaterialFolder, EditTask, User
from app.schemas import (
    GenerateCopywritingReq, ParseLinkReq, CopywritingResp, MaterialResp,
    FolderResp, CreateFolderReq, CreateEditTaskReq, EditTaskResp,
)
from app.services.ai_service import generate_copywriting, parse_video_link
from app.services.tasks import process_edit_task
from app.services.quota import check_edit_quota, check_storage_quota
from app.utils.auth import decode_access_token, security

router = APIRouter(prefix="/content", tags=["content"])


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Copywriting
@router.post("/copywriting/generate")
async def generate(
    req: GenerateCopywritingReq, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    results = await generate_copywriting(req.keywords, req.style, req.count)
    saved = []
    for r in results:
        tpl = CopywritingTemplate(
            user_id=user.id, title=r["title"], body=r["body"],
            tags=r.get("tags", ""), style=req.style, source="ai",
        )
        db.add(tpl)
        saved.append(tpl)
    await db.commit()
    return [CopywritingResp.model_validate(t) for t in saved]


@router.post("/copywriting/parse-link")
async def parse_link(
    req: ParseLinkReq, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    info = await parse_video_link(req.url)
    if not info:
        raise HTTPException(status_code=400, detail="解析失败，请检查链接")
    return info


@router.get("/copywriting/list", response_model=list[CopywritingResp])
async def list_copywriting(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
    style: str | None = None,
):
    q = select(CopywritingTemplate).where(CopywritingTemplate.user_id == user.id)
    if style:
        q = q.where(CopywritingTemplate.style == style)
    q = q.order_by(CopywritingTemplate.created_at.desc()).limit(50)
    result = await db.execute(q)
    return [CopywritingResp.model_validate(r) for r in result.scalars().all()]


# Materials
@router.post("/materials/upload")
async def upload_material(
    file: UploadFile = File(...), folder_id: str | None = Form(None),
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    # Check storage quota
    ok, msg = await check_storage_quota(db, user.id, file.size or 0)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    # In production: upload to MinIO/OSS, generate thumbnail, extract metadata
    file_url = f"/uploads/{user.id}/{file.filename}"
    material = Material(
        user_id=user.id, folder_id=folder_id,
        type="video" if file.content_type and "video" in file.content_type else "image",
        file_name=file.filename, file_url=file_url, size=file.size or 0,
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)
    return MaterialResp.model_validate(material)


@router.get("/materials", response_model=list[MaterialResp])
async def list_materials(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
    folder_id: str | None = None, type: str | None = None,
):
    q = select(Material).where(Material.user_id == user.id)
    if folder_id:
        q = q.where(Material.folder_id == folder_id)
    if type:
        q = q.where(Material.type == type)
    q = q.order_by(Material.created_at.desc()).limit(100)
    result = await db.execute(q)
    return [MaterialResp.model_validate(r) for r in result.scalars().all()]


@router.delete("/materials/{material_id}")
async def delete_material(
    material_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Material).where(Material.id == material_id, Material.user_id == user.id)
    )
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")
    await db.delete(material)
    await db.commit()
    return {"message": "已删除"}


@router.post("/folders", response_model=FolderResp)
async def create_folder(
    req: CreateFolderReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    folder = MaterialFolder(user_id=user.id, name=req.name, parent_id=req.parent_id)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


@router.get("/folders", response_model=list[FolderResp])
async def list_folders(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MaterialFolder).where(MaterialFolder.user_id == user.id).order_by(MaterialFolder.created_at)
    )
    return result.scalars().all()


# Edit Tasks
@router.post("/edit-tasks", response_model=EditTaskResp)
async def create_edit_task(
    req: CreateEditTaskReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    ok, msg = await check_edit_quota(db, user.id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    task = EditTask(
        user_id=user.id, material_ids=req.material_ids, copywriting_id=req.copywriting_id,
        template_id=req.template_id, params=req.model_dump(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Dispatch async Celery task (material_paths to be resolved from material_ids)
    process_edit_task.delay(
        task_id=task.id,
        material_paths=req.material_ids,  # In production: resolve URLs to local paths
        params=req.model_dump(),
    )
    return task


@router.get("/edit-tasks", response_model=list[EditTaskResp])
async def list_edit_tasks(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EditTask).where(EditTask.user_id == user.id).order_by(EditTask.created_at.desc()).limit(50)
    )
    return result.scalars().all()


@router.get("/edit-tasks/{task_id}", response_model=EditTaskResp)
async def get_edit_task(
    task_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EditTask).where(EditTask.id == task_id, EditTask.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task
