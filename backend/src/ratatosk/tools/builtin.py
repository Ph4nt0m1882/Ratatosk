import asyncio
import inspect
import mimetypes
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, get_type_hints

from pydantic import BaseModel, Field, create_model
from sqlalchemy import select

from ratatosk.core.idle_worker import idle_worker
from ratatosk.db.models import Attachment, User
from ratatosk.db.session import async_session_maker
from ratatosk.endpoints.db_manipulation.attachments.stats import ATTACHMENT_STATS_TASK
from ratatosk.file_manager import DestPaths, FileStorageManager


class ToolVisibility(StrEnum):
    """Kornak visibility levels for built-in tools."""

    ACTIVE = "active"  # Exposed in LLM tool declarations by default
    KORNAK = "kornak"  # Hidden by default; only exposed when explicitly unlocked


@dataclass(slots=True)
class ToolContext:
    """Execution context injected automatically into built-in tools."""

    user_id: str | None = None
    conversation_id: str | None = None
    is_admin: bool = False


@dataclass(slots=True)
class GeneratedAttachmentInfo:
    id: str
    filename: str
    mime_type: str
    is_generated: bool = True
    external_uri: str | None = None


@dataclass(slots=True)
class ToolExecutionResult:
    output: dict[str, Any]
    attachments: list[GeneratedAttachmentInfo] = field(default_factory=list)


@dataclass(slots=True)
class BuiltinToolSpec:
    name: str
    description: str
    parameters_schema: dict[str, Any]
    func: Callable[..., Any]
    visibility: ToolVisibility = ToolVisibility.ACTIVE
    admin_only: bool = False
    takes_context: str | None = None

    def to_google_declaration(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters_json_schema": self.parameters_schema,
        }


def _build_parameters_schema(
    func: Callable[..., Any],
) -> tuple[dict[str, Any], str | None]:
    """Build a clean JSON schema from function type hints, omitting ToolContext."""
    sig = inspect.signature(func)
    hints = get_type_hints(func)
    fields: dict[str, Any] = {}
    context_param: str | None = None

    for param_name, param in sig.parameters.items():
        annotation = hints.get(param_name, Any)
        if annotation is ToolContext or param_name == "ctx":
            context_param = param_name
            continue

        if param.default is inspect.Parameter.empty:
            fields[param_name] = (annotation, Field(...))
        else:
            fields[param_name] = (annotation, Field(default=param.default))

    model_cls: type[BaseModel] = create_model(f"{func.__name__}_Params", **fields)
    raw_schema = model_cls.model_json_schema()
    clean_schema: dict[str, Any] = {
        "type": "object",
        "properties": raw_schema.get("properties", {}),
    }
    if "required" in raw_schema:
        clean_schema["required"] = raw_schema["required"]
    return clean_schema, context_param


class BuiltinToolRegistry:
    """Registry and executor for Ratatosk built-in tools with Kornak visibility filtering."""

    def __init__(self) -> None:
        self._tools: dict[str, BuiltinToolSpec] = {}

    def register(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        visibility: ToolVisibility | str = ToolVisibility.ACTIVE,
        admin_only: bool = False,
    ) -> Any:
        def _do_register(f: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or f.__name__
            doc = (description or inspect.getdoc(f) or tool_name).strip()
            schema, context_param = _build_parameters_schema(f)
            vis = (
                visibility
                if isinstance(visibility, ToolVisibility)
                else ToolVisibility(visibility)
            )
            self._tools[tool_name] = BuiltinToolSpec(
                name=tool_name,
                description=doc,
                parameters_schema=schema,
                func=f,
                visibility=vis,
                admin_only=admin_only,
                takes_context=context_param,
            )
            return f

        if func is not None:
            return _do_register(func)
        return _do_register

    def get(self, name: str) -> BuiltinToolSpec | None:
        return self._tools.get(name)

    def list_exposed_specs(
        self,
        unlocked_tools: list[str] | set[str] | None = None,
        *,
        is_admin: bool = False,
    ) -> list[BuiltinToolSpec]:
        """Return ACTIVE tools plus any KORNAK tools explicitly unlocked for this turn."""
        unlocked = set(unlocked_tools or ())
        exposed: list[BuiltinToolSpec] = []
        for spec in self._tools.values():
            if spec.admin_only and not is_admin:
                continue
            if spec.visibility == ToolVisibility.ACTIVE or spec.name in unlocked:
                exposed.append(spec)
        return exposed

    def get_google_declarations(
        self,
        unlocked_tools: list[str] | set[str] | None = None,
        *,
        is_admin: bool = False,
    ) -> list[dict[str, Any]]:
        return [
            spec.to_google_declaration()
            for spec in self.list_exposed_specs(unlocked_tools, is_admin=is_admin)
        ]

    async def execute(
        self,
        name: str,
        args: dict[str, Any] | None,
        ctx: ToolContext,
    ) -> ToolExecutionResult:
        """Execute a registered built-in tool, enforcing admin_only privileges."""
        spec = self._tools.get(name)
        if spec is None:
            return ToolExecutionResult(output={"error": f"Unknown built-in tool '{name}'"})

        if spec.admin_only and not ctx.is_admin:
            if ctx.user_id:
                async with async_session_maker() as session:
                    user = await session.get(User, ctx.user_id)
                    if user is not None and user.is_admin:
                        ctx.is_admin = True
            if not ctx.is_admin:
                return ToolExecutionResult(
                    output={"error": "Permission denied: admin privileges required"}
                )

        call_kwargs = dict(args or {})
        if spec.takes_context:
            call_kwargs[spec.takes_context] = ctx

        try:
            res = spec.func(**call_kwargs)
            if inspect.isawaitable(res):
                res = await res
            if isinstance(res, ToolExecutionResult):
                return res
            if isinstance(res, dict):
                return ToolExecutionResult(output=res)
            return ToolExecutionResult(output={"result": res})
        except Exception as exc:  # noqa: BLE001
            return ToolExecutionResult(output={"error": str(exc)})


builtin_registry = BuiltinToolRegistry()


def builtin_tool(
    func: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    visibility: ToolVisibility | str = ToolVisibility.ACTIVE,
    admin_only: bool = False,
) -> Any:
    """Decorator to register a Ratatosk built-in tool with Kornak visibility & admin_only support."""
    if func is not None:
        return builtin_registry.register(
            func,
            name=name,
            description=description,
            visibility=visibility,
            admin_only=admin_only,
        )

    def _decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        return builtin_registry.register(
            f,
            name=name,
            description=description,
            visibility=visibility,
            admin_only=admin_only,
        )

    return _decorator


def _sanitize_generated_filename(filename: str) -> str:
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    clean = re.sub(r'[\x00-\x1f<>:"/\\|?*]+', "_", base).strip().strip(".")
    if not clean:
        clean = "generated.txt"
    elif "." not in clean:
        clean = f"{clean}.txt"
    return clean[:255]


@builtin_tool(visibility=ToolVisibility.ACTIVE)
async def create_file(
    filename: str,
    content: str,
    mime_type: str = "",
    description: str = "",
    ctx: ToolContext | None = None,
) -> ToolExecutionResult:
    """Create a downloadable text or code file attachment (`is_generated=True`) from UTF-8 content.

    When the tool returns `attachment_id` and `embed_markdown`, place
    `[filename](attachment://<attachment_id>)` at the exact position in your Markdown response
    where the file card should appear.
    """
    clean_filename = _sanitize_generated_filename(filename)
    guessed_mime, _ = mimetypes.guess_type(clean_filename)
    resolved_mime = (
        mime_type.strip().lower()
        if mime_type and "/" in mime_type
        else (guessed_mime or "text/plain")
    )

    raw_bytes = content.encode("utf-8")
    storage = FileStorageManager()
    file_hash, rel_path, file_size = await asyncio.to_thread(
        storage.save_file,
        DestPaths.GENERATED,
        raw_bytes,
    )

    user_id = ctx.user_id if ctx else None
    source_tag = "tool:create_file"
    desc = description.strip() or None

    async with async_session_maker() as session:
        existing = (
            await session.execute(
                select(Attachment).where(
                    Attachment.user_id == user_id,
                    Attachment.source == source_tag,
                    Attachment.file_hash == file_hash,
                )
            )
        ).scalar_one_or_none()

        if existing is not None:
            if desc and not existing.description:
                existing.description = desc
            existing.expires_at = None
            await session.commit()
            await session.refresh(existing)
            attachment = existing
        else:
            attachment = Attachment(
                user_id=user_id,
                source=source_tag,
                file_hash=file_hash,
                mime_type=resolved_mime,
                file_path=rel_path,
                file_size=file_size,
                description=desc,
                is_generated=True,
                expires_at=None,
            )
            session.add(attachment)
            await session.commit()
            await session.refresh(attachment)

    idle_worker.mark_dirty(ATTACHMENT_STATS_TASK)

    return ToolExecutionResult(
        output={
            "status": "created",
            "attachment_id": attachment.id,
            "filename": clean_filename,
            "mime_type": resolved_mime,
            "size": file_size,
            "embed_markdown": f"[{clean_filename}](attachment://{attachment.id})",
            "placement_hint": (
                f"Insert [{clean_filename}](attachment://{attachment.id}) at the exact "
                "position in your Markdown response where this file should appear."
            ),
        },
        attachments=[
            GeneratedAttachmentInfo(
                id=attachment.id,
                filename=clean_filename,
                mime_type=resolved_mime,
                is_generated=True,
                external_uri=None,
            )
        ],
    )
