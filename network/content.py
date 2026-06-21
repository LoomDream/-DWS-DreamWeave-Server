from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from .crypto import developer_proof, encrypt_json_payload, md5_hex


class ContentStore:
    def __init__(self, story_file: Path, story_dir: Path, audio_dir: Path, seed_dir: Path, model_dir: Path, developer_secret: str) -> None:
        self.story_file = story_file
        self.story_dir = story_dir
        self.audio_dir = audio_dir
        self.seed_dir = seed_dir
        self.model_dir = model_dir
        self.developer_secret = developer_secret
        self.model_manifest: dict[str, Any] = empty_model_manifest(model_dir)

    def load_story(self) -> dict[str, Any]:
        if self.story_dir.exists():
            scenes = [scene["content"] for scene in self.list_story_scenes(include_content=True)]
            if scenes:
                return {"meta": {"kind": "story_collection", "scene_count": len(scenes)}, "scenes": scenes}
        with self.story_file.open("r", encoding="utf-8") as story_data:
            return json.load(story_data)

    def encrypted_story_package(self, session_key: bytes) -> dict[str, Any]:
        story = self.load_story()
        raw = json.dumps(story, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        content_md5 = md5_hex(raw)
        return {
            "kind": "story_json",
            "encoding": "base64",
            "encryption": "xor-sha256-session-key",
            "md5": content_md5,
            "server_key": developer_proof(self.developer_secret, session_key, content_md5),
            "payload": encrypt_json_payload(raw, session_key),
        }

    def list_story_scenes(self, include_content: bool = False) -> list[dict[str, Any]]:
        self.story_dir.mkdir(parents=True, exist_ok=True)
        scenes: list[dict[str, Any]] = []
        for path in sorted(self.story_dir.glob("*.json"), key=_story_sort_key):
            try:
                content = self.read_story_scene(path.name)
                meta = _scene_meta(content, path.name)
            except (OSError, json.JSONDecodeError, ValueError):
                content = {}
                meta = {"chapter": 0, "act": 0, "chapter_title": "", "scene_title": path.stem, "invalid": True}
            item = {
                "file": path.name,
                "path": str(path),
                "md5": md5_hex(path.read_bytes()) if path.exists() else "",
                "updated_at": int(path.stat().st_mtime) if path.exists() else 0,
                "meta": meta,
            }
            if include_content:
                item["content"] = content
            scenes.append(item)
        return scenes

    def read_story_scene(self, filename: str) -> dict[str, Any]:
        path = self.story_path(filename)
        with path.open("r", encoding="utf-8") as story_data:
            content = json.load(story_data)
        if not isinstance(content, dict):
            raise ValueError("story scene must be a JSON object")
        return content

    def save_story_scene(self, filename: str, content: dict[str, Any]) -> dict[str, Any]:
        path = self.story_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized = normalize_story_scene(filename, content)
        path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raw = path.read_bytes()
        return {
            "file": path.name,
            "path": str(path),
            "md5": md5_hex(raw),
            "updated_at": int(path.stat().st_mtime),
            "meta": _scene_meta(normalized, path.name),
            "content": normalized,
        }

    def create_story_scene(self, chapter: int, act: int, chapter_title: str, scene_title: str) -> dict[str, Any]:
        content = {
            "meta": {
                "chapter": chapter,
                "act": act,
                "chapter_title": chapter_title,
                "scene_title": scene_title,
            },
            "characters": [],
            "backgrounds": [],
            "dialogues": [],
            "audio": [
                {
                    "id": "scene_bgm",
                    "kind": "bgm",
                    "file": f"chapter{chapter}_act{act}_bgm.wav",
                    "url": f"/api/content/audio/chapter{chapter}_act{act}_bgm.wav",
                    "loop": True,
                    "volume": 0.8,
                }
            ],
            "tasks": [],
        }
        return self.save_story_scene(story_filename(chapter, act), content)

    def story_path(self, filename: str) -> Path:
        safe_name = safe_story_filename(filename)
        path = (self.story_dir / safe_name).resolve()
        root = self.story_dir.resolve()
        if root != path.parent:
            raise ValueError("story filename must stay inside story directory")
        return path

    def list_story_audio(self) -> list[dict[str, Any]]:
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        files = []
        for path in sorted(self.audio_dir.glob("*.wav")):
            files.append(
                {
                    "file": path.name,
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "updated_at": int(path.stat().st_mtime),
                    "url": f"/api/content/audio/{path.name}",
                    "content_type": "audio/wav",
                }
            )
        return files

    def audio_path(self, filename: str) -> Path:
        safe_name = safe_audio_filename(filename)
        path = (self.audio_dir / safe_name).resolve()
        root = self.audio_dir.resolve()
        if root != path.parent:
            raise ValueError("audio filename must stay inside audio directory")
        return path

    def read_map_seed(self, map_id: int) -> dict[str, Any]:
        path = self.seed_path(map_id)
        seed = path.read_text(encoding="utf-8").strip()
        raw = seed.encode("utf-8")
        return {
            "map_id": map_id,
            "seed": seed,
            "algorithm": "perlin-terrain",
            "file": path.name,
            "path": str(path),
            "md5": md5_hex(raw),
            "updated_at": int(path.stat().st_mtime),
        }

    def seed_path(self, map_id: int) -> Path:
        if map_id < 1:
            raise ValueError("map id must start from 1")
        path = (self.seed_dir / f"{map_id}.txt").resolve()
        root = self.seed_dir.resolve()
        if root != path.parent:
            raise ValueError("seed filename must stay inside seed directory")
        return path

    def scan_models(self) -> dict[str, Any]:
        self.model_dir.mkdir(parents=True, exist_ok=True)
        root = self.model_dir.resolve()
        files: list[dict[str, Any]] = []
        for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.relative_to(root).as_posix()):
            relative_path = path.relative_to(root).as_posix()
            if any(part.startswith(".") for part in path.relative_to(root).parts):
                continue
            stat = path.stat()
            files.append(
                {
                    "name": path.name,
                    "relative_path": relative_path,
                    "extension": path.suffix.lower().lstrip("."),
                    "bytes": stat.st_size,
                    "updated_at": int(stat.st_mtime),
                }
            )
        self.model_manifest = {
            "model_dir": str(self.model_dir),
            "scanned_at": int(time.time()),
            "count": len(files),
            "total_bytes": sum(int(item["bytes"]) for item in files),
            "files": files,
        }
        return self.model_manifest

    def list_models(self) -> dict[str, Any]:
        return self.model_manifest

    def model_path(self, relative_path: str) -> Path:
        safe_path = safe_model_relative_path(relative_path)
        root = self.model_dir.resolve()
        path = (root / safe_path).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("model path must stay inside model directory") from exc
        return path


def story_filename(chapter: int, act: int) -> str:
    if chapter < 1 or act < 1:
        raise ValueError("chapter and act must be positive integers")
    return f"{chapter}-{act}.json"


def empty_model_manifest(model_dir: Path) -> dict[str, Any]:
    return {
        "model_dir": str(model_dir),
        "scanned_at": 0,
        "count": 0,
        "total_bytes": 0,
        "files": [],
    }


def safe_model_relative_path(value: str) -> Path:
    normalized = value.replace("\\", "/").strip()
    path = Path(normalized)
    if not normalized or path.is_absolute():
        raise ValueError("model path must be relative")
    if any(part in {"", ".", ".."} or part.startswith(".") for part in path.parts):
        raise ValueError("model path must not contain hidden, empty, or parent segments")
    if len(path.parts) > 8:
        raise ValueError("model path is too deep")
    if not all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", part) for part in path.parts):
        raise ValueError("model path contains invalid characters")
    return path


def safe_story_filename(filename: str) -> str:
    name = Path(filename).name
    if not re.fullmatch(r"[1-9]\d*-[1-9]\d*\.json", name):
        raise ValueError("story filename must match <chapter>-<act>.json")
    return name


def normalize_story_scene(filename: str, content: dict[str, Any]) -> dict[str, Any]:
    safe_name = safe_story_filename(filename)
    chapter, act = _chapter_act_from_name(safe_name)
    scene = dict(content)
    meta = scene.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    meta = dict(meta)
    meta["chapter"] = _safe_positive_int(meta.get("chapter"), chapter)
    meta["act"] = _safe_positive_int(meta.get("act"), act)
    meta.setdefault("chapter_title", f"\u7b2c {meta['chapter']} \u7ae0")
    meta.setdefault("scene_title", f"\u7b2c {meta['act']} \u5e55")
    scene["meta"] = meta
    scene.setdefault("characters", [])
    scene.setdefault("dialogues", [])
    scene.setdefault("backgrounds", [])
    scene.setdefault("audio", [])
    scene.setdefault("tasks", [])
    return scene


def _scene_meta(content: dict[str, Any], filename: str) -> dict[str, Any]:
    chapter, act = _chapter_act_from_name(filename)
    meta = content.get("meta") if isinstance(content, dict) else {}
    if not isinstance(meta, dict):
        meta = {}
    return {
        "chapter": _safe_positive_int(meta.get("chapter"), chapter),
        "act": _safe_positive_int(meta.get("act"), act),
        "chapter_title": str(meta.get("chapter_title") or f"\u7b2c {chapter} \u7ae0"),
        "scene_title": str(meta.get("scene_title") or f"\u7b2c {act} \u5e55"),
    }


def _story_sort_key(path: Path) -> tuple[int, int, str]:
    try:
        chapter, act = _chapter_act_from_name(path.name)
    except ValueError:
        return (999999, 999999, path.name)
    return (chapter, act, path.name)


def _chapter_act_from_name(filename: str) -> tuple[int, int]:
    match = re.fullmatch(r"([1-9]\d*)-([1-9]\d*)\.json", Path(filename).name)
    if not match:
        raise ValueError("story filename must match <chapter>-<act>.json")
    return int(match.group(1)), int(match.group(2))


def safe_audio_filename(filename: str) -> str:
    name = Path(filename).name
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.wav", name):
        raise ValueError("audio filename must be a safe .wav filename")
    return name


def _safe_positive_int(value: Any, fallback: int) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError, OverflowError):
        return fallback
    return result if result > 0 else fallback
