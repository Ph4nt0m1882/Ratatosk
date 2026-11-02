import io
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException, Response
from sqlalchemy import select

from ratatosk.core.dynamic_settings import dynamic_settings
from ratatosk.db.models import Conversation, Message, User
from ratatosk.db.session import async_session_maker


def _sanitize_filename(title: str) -> tuple[str, str]:
    """Return an (ascii_safe_stem, utf8_clean_stem) pair for Content-Disposition."""
    clean_utf8 = re.sub(r'[\\/:*?"<>|\r\n]+', "_", title).strip().strip(".")
    if not clean_utf8:
        clean_utf8 = "conversation"

    ascii_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", clean_utf8).strip("_")
    if not ascii_stem:
        ascii_stem = "conversation"

    return ascii_stem[:100], clean_utf8[:100]


def _content_disposition(ascii_name: str, utf8_name: str) -> str:
    encoded = quote(utf8_name, safe="")
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded}'


def _extract_message_sections(msg: Message) -> tuple[list[str], list[dict], str]:
    """Split a message into (thoughts, tool_events, visible_text)."""
    thoughts: list[str] = []
    tool_events: list[dict] = []
    text_chunks: list[str] = []

    if msg.parts:
        for part in msg.parts:
            if not isinstance(part, dict):
                continue

            part_type = part.get("type")

            # 1. Thinking / reasoning blocks
            if part_type in ("thought", "thinking") or part.get("thought") is True:
                thought_text = part.get("text") or part.get("content") or ""
                if thought_text:
                    thoughts.append(str(thought_text).strip())
                continue
            if isinstance(part.get("thought"), str) and part["thought"].strip():
                thoughts.append(part["thought"].strip())
                continue

            # 2. Tool / function calls & responses
            if part_type in (
                "tool_call",
                "tool_response",
                "function_call",
                "function_response",
            ) or any(
                k in part
                for k in (
                    "tool_call",
                    "tool_response",
                    "function_call",
                    "function_response",
                    "executable_code",
                    "code_execution_result",
                )
            ):
                tool_events.append(part)
                continue

            # 3. Visible text parts
            if "text" in part and part["text"] is not None:
                text_chunks.append(str(part["text"]))

    visible_text = "".join(text_chunks).strip() if text_chunks else msg.content.strip()
    return thoughts, tool_events, visible_text


def _format_bubble(text: str) -> str:
    """Wrap Markdown text inside a native blockquote bubble without breaking formatting."""
    if not text:
        return "> *(empty)*"
    return "\n".join(f"> {line}" if line else ">" for line in text.splitlines())


def _render_conversation_markdown(
    conversation: Conversation,
    owner_username: str,
    messages: list[Message],
) -> str:
    created_str = conversation.created_at.strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        f"# {conversation.title}",
        "",
        f"- **Owner**: {owner_username}",
        f"- **Created**: {created_str}",
        f"- **Messages**: {len(messages)}",
        "",
        "---",
        "",
    ]

    for index, msg in enumerate(messages):
        timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        if msg.role == "user":
            header = f"### 👤 {owner_username} · *{timestamp}*"
        elif msg.role in ("assistant", "model"):
            header = (
                f"### 🤖 {dynamic_settings.agent_name} (`{msg.model}`) · *{timestamp}*"
            )
        else:
            header = f"### ⚙️ {msg.role} · *{timestamp}*"

        lines.append(header)
        lines.append("")

        thoughts, tool_events, visible_text = _extract_message_sections(msg)

        if thoughts:
            joined_thoughts = "\n\n---\n\n".join(thoughts)
            lines.extend(
                [
                    "<details>",
                    "<summary>thinking</summary>",
                    "",
                    joined_thoughts,
                    "",
                    "</details>",
                    "",
                ]
            )

        if tool_events:
            formatted_tools = json.dumps(tool_events, indent=2, ensure_ascii=False)
            lines.extend(
                [
                    "<details>",
                    "<summary>tool calls</summary>",
                    "",
                    "```json",
                    formatted_tools,
                    "```",
                    "",
                    "</details>",
                    "",
                ]
            )

        lines.append(_format_bubble(visible_text))
        lines.append("")

        if index < len(messages) - 1:
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def _build_zip_archive(
    md_filename: str,
    md_content: str,
    attachments: list[tuple[str, Path]],
) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(md_filename, md_content.encode("utf-8"))
        for arc_name, file_path in attachments:
            if file_path.is_file():
                zf.write(file_path, arcname=f"attachments/{arc_name}")
    return buffer.getvalue()


async def export_conversation(conversation_id: str, user: User) -> Response:
    async with async_session_maker() as session:
        stmt = (
            select(Conversation, User.username)
            .join(User, Conversation.user_id == User.id)
            .where(Conversation.id == conversation_id)
        )
        row = (await session.execute(stmt)).first()

        if row is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conversation, owner_username = row
        if conversation.user_id != user.id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        msg_stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        messages = list((await session.execute(msg_stmt)).scalars().all())

    md_content = _render_conversation_markdown(conversation, owner_username, messages)
    ascii_stem, utf8_stem = _sanitize_filename(conversation.title)

    # Ready for future ATTACHMENT table integration:
    # populate `attachments` with `(filename, Path(file_path))` when present.
    attachments: list[tuple[str, Path]] = []

    if attachments:
        zip_bytes = _build_zip_archive(f"{utf8_stem}.md", md_content, attachments)
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": _content_disposition(
                    f"{ascii_stem}.zip", f"{utf8_stem}.zip"
                )
            },
        )

    return Response(
        content=md_content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": _content_disposition(
                f"{ascii_stem}.md", f"{utf8_stem}.md"
            )
        },
    )
