import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.dependencies import get_current_key, get_log_repo, get_provider_registry
from app.models.api_key import APIKey
from app.models.message import Message
from app.models.result import BatchSendResult, NotificationLog, SendResult
from app.models.target import Target
from app.providers.base import InvalidTargetError
from app.repositories.base import NotificationLogRepository
from app.providers.registry import ProviderRegistry
from app.security.rbac import Scope, require_scope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notify", tags=["notify"])


class NotifyRequest(BaseModel):
    target: Target
    message: Message


class BatchNotifyRequest(BaseModel):
    targets: list[Target]
    message: Message


async def _dispatch(
    target: Target,
    message: Message,
    api_key_id: str,
    registry: ProviderRegistry,
    log_repo: NotificationLogRepository,
) -> SendResult:
    """Resolve provider, validate target, send, and write audit log."""
    try:
        provider = registry.get_or_raise(target.provider)
    except KeyError as exc:
        result = SendResult(
            success=False,
            provider=target.provider,
            identifier=target.identifier,
            error=str(exc),
        )
        await _write_log(log_repo, api_key_id, target, result)
        return result

    try:
        await provider.validate_target(target)
    except (InvalidTargetError, NotImplementedError) as exc:
        result = SendResult(
            success=False,
            provider=target.provider,
            identifier=target.identifier,
            error=str(exc),
        )
        await _write_log(log_repo, api_key_id, target, result)
        return result

    result = await provider.send(target, message)
    await _write_log(log_repo, api_key_id, target, result)

    if result.success:
        logger.info(
            "Message sent",
            extra={"provider": target.provider, "identifier": target.identifier, "key_id": api_key_id},
        )
    else:
        logger.warning(
            "Message send failed",
            extra={"provider": target.provider, "identifier": target.identifier, "error": result.error},
        )

    return result


async def _write_log(
    log_repo: NotificationLogRepository,
    api_key_id: str,
    target: Target,
    result: SendResult,
) -> None:
    entry = NotificationLog(
        id=str(uuid.uuid4()),
        api_key_id=api_key_id,
        target_provider=target.provider,
        target_identifier=target.identifier,
        status="success" if result.success else "failure",
        error=result.error,
    )
    await log_repo.append(entry)


@router.post("", response_model=SendResult)
async def notify(
    body: NotifyRequest,
    current_key: APIKey = Depends(get_current_key),
    registry: ProviderRegistry = Depends(get_provider_registry),
    log_repo: NotificationLogRepository = Depends(get_log_repo),
    _: APIKey = Depends(require_scope(Scope.NOTIFY_SEND)),
):
    return await _dispatch(body.target, body.message, current_key.id, registry, log_repo)


@router.post("/batch", response_model=BatchSendResult)
async def notify_batch(
    body: BatchNotifyRequest,
    current_key: APIKey = Depends(get_current_key),
    registry: ProviderRegistry = Depends(get_provider_registry),
    log_repo: NotificationLogRepository = Depends(get_log_repo),
    _: APIKey = Depends(require_scope(Scope.NOTIFY_SEND)),
):
    if not body.targets:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="targets must not be empty.",
        )

    tasks = [
        _dispatch(target, body.message, current_key.id, registry, log_repo)
        for target in body.targets
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    send_results = []
    for target, result in zip(body.targets, results):
        if isinstance(result, Exception):
            send_results.append(
                SendResult(
                    success=False,
                    provider=target.provider,
                    identifier=target.identifier,
                    error=str(result),
                )
            )
        else:
            send_results.append(result)

    return BatchSendResult(results=send_results)
