import logging
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_key, get_hasher, get_key_repo
from app.models.api_key import APIKey, CreateKeyRequest, CreateKeyResponse, UpdateKeyRequest
from app.repositories.base import APIKeyRepository
from app.security.hashing.base import KeyHasher
from app.security.rbac import Scope, require_scope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/keys", tags=["keys"])


@router.get("", response_model=list[APIKey])
async def list_keys(
    current_key: APIKey = Depends(get_current_key),
    key_repo: APIKeyRepository = Depends(get_key_repo),
    _: APIKey = Depends(require_scope(Scope.KEYS_READ)),
):
    return await key_repo.list_all()


@router.post("", response_model=CreateKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    body: CreateKeyRequest,
    current_key: APIKey = Depends(get_current_key),
    key_repo: APIKeyRepository = Depends(get_key_repo),
    hasher: KeyHasher = Depends(get_hasher),
    _: APIKey = Depends(require_scope(Scope.KEYS_WRITE)),
):
    raw_key = secrets.token_urlsafe(32)
    key_hash = hasher.hash(raw_key)
    new_key = APIKey(id=str(uuid.uuid4()), name=body.name, scopes=body.scopes)
    await key_repo.create(new_key, key_hash)
    logger.info("API key created", extra={"key_id": new_key.id, "name": new_key.name})
    return CreateKeyResponse(
        id=new_key.id,
        name=new_key.name,
        scopes=new_key.scopes,
        raw_key=raw_key,
    )


@router.get("/{key_id}", response_model=APIKey)
async def get_key(
    key_id: str,
    current_key: APIKey = Depends(get_current_key),
    key_repo: APIKeyRepository = Depends(get_key_repo),
    _: APIKey = Depends(require_scope(Scope.KEYS_READ)),
):
    key = await key_repo.get_by_id(key_id)
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found.")
    return key


@router.patch("/{key_id}", response_model=APIKey)
async def update_key(
    key_id: str,
    body: UpdateKeyRequest,
    current_key: APIKey = Depends(get_current_key),
    key_repo: APIKeyRepository = Depends(get_key_repo),
    _: APIKey = Depends(require_scope(Scope.KEYS_WRITE)),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields to update.",
        )
    key = await key_repo.update(key_id, **updates)
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found.")
    logger.info("API key updated", extra={"key_id": key_id, "updates": list(updates.keys())})
    return key


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(
    key_id: str,
    current_key: APIKey = Depends(get_current_key),
    key_repo: APIKeyRepository = Depends(get_key_repo),
    _: APIKey = Depends(require_scope(Scope.KEYS_WRITE)),
):
    deleted = await key_repo.delete(key_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found.")
    logger.info("API key deleted", extra={"key_id": key_id})
