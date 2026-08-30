from __future__ import annotations

import json
import queue
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

EVENT_TYPES = ("comment", "join", "follow", "share", "like", "gift", "room")

@dataclass
class LiveEvent:
    type: str
    userId: str = ""
    uniqueId: str = ""
    nickname: str = ""
    avatarUrl: str = ""
    timestamp: float = 0.0
    comment: str = ""
    likeCount: int = 0
    giftName: str = ""
    giftId: str = ""
    giftCount: int = 0
    diamondCount: int = 0
    viewerCount: int = 0
    roomId: str = ""

class LocalEventBus:
    def __init__(self) -> None:
        self._subscribers: list[Callable[[LiveEvent], None]] = []

    def subscribe(self, callback: Callable[[LiveEvent], None]) -> None:
        self._subscribers.append(callback)

    def publish(self, event: LiveEvent) -> None:
        for callback in tuple(self._subscribers):
            callback(event)

class EventNormalizer:
    """Only this class maps provider payloads to the app-wide event contract."""
    def normalize(self, payload: dict[str, Any]) -> list[LiveEvent]:
        messages = payload.get("messages", [payload])
        result: list[LiveEvent] = []
        for raw in messages:
            if not isinstance(raw, dict):
                continue
            kind = str(raw.get("type") or raw.get("event") or raw.get("eventType") or "").lower()
            aliases = {"chat": "comment", "commentevent": "comment", "member": "join", "memberevent": "join", "likeevent": "like", "giftevent": "gift", "shareevent": "share", "followevent": "follow", "roomstats": "room", "roominfo": "room"}
            kind = aliases.get(kind, kind)
            if kind not in EVENT_TYPES:
                continue
            user = raw.get("user") or raw.get("userInfo") or {}
            result.append(LiveEvent(
                type=kind, userId=str(raw.get("userId") or user.get("id") or ""),
                uniqueId=str(raw.get("uniqueId") or user.get("uniqueId") or ""),
                nickname=str(raw.get("nickname") or user.get("nickname") or ""),
                avatarUrl=str(raw.get("avatarUrl") or user.get("avatarUrl") or ""),
                timestamp=time.time(), comment=str(raw.get("comment") or raw.get("text") or ""),
                likeCount=int(raw.get("likeCount") or raw.get("count") or 0),
                giftName=str(raw.get("giftName") or raw.get("gift", {}).get("name", "")),
                giftId=str(raw.get("giftId") or raw.get("gift", {}).get("id", "")),
                giftCount=int(raw.get("giftCount") or raw.get("repeatCount") or 0),
                diamondCount=int(raw.get("diamondCount") or 0), viewerCount=int(raw.get("viewerCount") or raw.get("viewer_count") or 0), roomId=str(raw.get("roomId") or "")))
        return result

class SettingsStore:
    def __init__(self, path: Path) -> None: self.path = path
    def load(self) -> dict[str, Any]:
        try: return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): return {}
    def save(self, values: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")

class EventFilter:
    def __init__(self) -> None: self.last_seen: dict[str, float] = {}
    def allow(self, event: LiveEvent, settings: dict[str, Any]) -> bool:
        if event.type != "comment": return True
        if len(event.comment) > int(settings.get("max_comment_length", 220)): return False
        key = event.userId or event.uniqueId or event.nickname
        now = time.time(); cooldown = float(settings.get("cooldown", 3))
        if key and now - self.last_seen.get(key, 0) < cooldown: return False
        forbidden = [x.strip().lower() for x in settings.get("blocked_words", "").split(",") if x.strip()]
        text = event.comment.lower()
        if any(word in text for word in forbidden): return False
        if key: self.last_seen[key] = now
        return True

def speech_for(event: LiveEvent, s: dict[str, Any]) -> str:
    nick = event.nickname[:int(s.get("max_nickname_length", 24))]
    prefix = (nick + " schreibt: ") if s.get("say_username", True) and nick else ""
    if event.type == "comment": return prefix + event.comment
    if event.type == "join": return f"{nick} ist dem Live beigetreten."
    if event.type == "follow": return f"{nick} folgt dir."
    if event.type == "share": return f"{nick} hat das Live geteilt."
    if event.type == "like" and event.likeCount >= int(s.get("like_threshold", 100)): return f"{nick} sendet {event.likeCount} Likes."
    if event.type == "gift": return f"{nick} sendet {event.giftCount or 1} mal {event.giftName or 'ein Geschenk'}."
    return ""
