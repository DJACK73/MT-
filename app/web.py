from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from mt_agent import webapi
from mt_agent.approval import PlanError
from mt_agent.ffx import MediaError
from mt_agent.paths import ROOT
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.routing import Route

STATIC = Path(__file__).parent / "web_static"
THUMBS = (ROOT / "workspace" / "thumbs").resolve()
PREVIEWS = (ROOT / "workspace" / "previews").resolve()
PLACEHOLDER = "<!doctype html><meta charset=utf-8><title>MT</title><p>MT web : page a venir."


class _Json(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(content, ensure_ascii=False, default=str).encode("utf-8")


def _err(code: int, msg: str) -> Response:
    return _Json({"error": msg}, status_code=code)


async def _call(fn: Callable[..., Any], *args: Any) -> Response:
    try:
        return _Json(await run_in_threadpool(fn, *args))
    except (PlanError, MediaError, PermissionError, ValueError) as e:
        return _err(400, str(e))
    except FileNotFoundError as e:
        return _err(404, str(e))


async def index(request: Request) -> Response:
    page = STATIC / "index.html"
    return FileResponse(page) if page.is_file() else HTMLResponse(PLACEHOLDER)


async def plans(request: Request) -> Response:
    return await _call(webapi.list_plans, ROOT)


async def plan(request: Request) -> Response:
    return await _call(webapi.get_plan, ROOT, request.path_params["name"])


async def select(request: Request) -> Response:
    try:
        body = await request.json()
    except ValueError:
        return _err(400, "JSON invalide")
    order = body.get("order") if isinstance(body, dict) else None
    if not isinstance(order, list) or any(type(x) is not int for x in order):
        return _err(400, "order : liste d'entiers attendue")
    return await _call(webapi.apply_selection, ROOT, request.path_params["name"], order)


async def approve(request: Request) -> Response:
    return await _call(webapi.approve_plan, ROOT, request.path_params["name"])


async def thumb(request: Request) -> Response:
    n = request.path_params["n"]
    if n < 1:
        return _err(400, "n >= 1")
    try:
        p = await run_in_threadpool(webapi.thumbnail, ROOT, request.path_params["name"], n)
    except (PlanError, ValueError) as e:
        return _err(400, str(e))
    except FileNotFoundError as e:
        return _err(404, str(e))
    if p is None:
        return _err(404, "vignette indisponible")
    p = Path(p).resolve()
    if not p.is_file() or not p.is_relative_to(THUMBS):
        return _err(404, "vignette indisponible")
    return FileResponse(p, media_type="image/jpeg")


async def inbox(request: Request) -> Response:
    return await _call(webapi.list_inbox, ROOT)


async def music(request: Request) -> Response:
    return await _call(webapi.list_music, ROOT)


async def tool(request: Request) -> Response:
    try:
        body = await request.json()
    except ValueError:
        return _err(400, "JSON invalide")
    if not isinstance(body, dict) or not isinstance(body.get("name"), str) or not isinstance(body.get("tool"), str):
        return _err(400, "name et tool attendus")
    return await _call(webapi.run_tool, ROOT, body["name"], body["tool"])


async def stack(request: Request) -> Response:
    try:
        body = await request.json()
    except ValueError:
        return _err(400, "JSON invalide")
    v = body.get("videos") if isinstance(body, dict) else None
    if (not isinstance(v, list) or not all(isinstance(x, str) for x in v)
            or not isinstance(body.get("mode"), str) or not isinstance(body.get("fit", "ajuster"), str)):
        return _err(400, "videos (liste), mode et fit attendus")
    return await _call(webapi.run_stack, ROOT, body["videos"], body["mode"], body.get("fit", "ajuster"))


async def videos(request: Request) -> Response:
    return await _call(webapi.list_videos, ROOT)


async def export(request: Request) -> Response:
    try:
        body = await request.json()
    except ValueError:
        return _err(400, "JSON invalide")
    if not isinstance(body, dict) or not isinstance(body.get("name"), str):
        return _err(400, "name attendu")
    return await _call(webapi.start_export, ROOT, body["name"], body.get("kind"),
                       body.get("ratio", "9:16"), body.get("speed", 1),
                       body.get("quality", "normal"), body.get("audio", "none"), body.get("mirror", []),
                       body.get("opts"))


async def compose(request: Request) -> Response:
    try:
        body = await request.json()
    except ValueError:
        return _err(400, "JSON invalide")
    if not isinstance(body, dict):
        return _err(400, "objet attendu")
    return await _call(webapi.compose, ROOT, body.get("items"))


async def job(request: Request) -> Response:
    return _Json(webapi.get_job())


async def cutjob(request: Request) -> Response:
    if request.method == "GET":
        return _Json(webapi.get_cutjob())
    try:
        body = await request.json()
    except ValueError:
        return _err(400, "JSON invalide")
    if not isinstance(body, dict):
        return _err(400, "objet JSON attendu")
    return await _call(webapi.start_cut, ROOT, body.get("names"), body.get("mode", "auto"), body.get("threshold"),
                       body.get("min"), body.get("max"), body.get("framing", "blur_pad"), body.get("spans", ""))


async def clean(request: Request) -> Response:
    level = request.path_params["level"]
    if request.method == "GET":
        return await _call(webapi.clean_preview, ROOT, level)
    try:
        body = await request.json()
    except ValueError:
        return _err(400, "JSON invalide")
    c = body.get("confirm") if isinstance(body, dict) else None
    if isinstance(c, bool) or c != level:
        return _err(400, "confirmation requise : confirm = niveau")
    return await _call(webapi.do_clean, ROOT, level)


async def preview(request: Request) -> Response:
    n = request.path_params["n"]
    if n < 1:
        return _err(400, "n >= 1")
    q = request.query_params
    try:
        speed = float(q.get("speed", "1"))
    except ValueError:
        return _err(400, "vitesse invalide")
    try:
        p = await run_in_threadpool(webapi.preview, ROOT, request.path_params["name"], n,
                                    q.get("mirror") == "1", speed)
    except (PlanError, MediaError, ValueError) as e:
        return _err(400, str(e))
    except FileNotFoundError as e:
        return _err(404, str(e))
    p = Path(p).resolve()
    if not p.is_file() or not p.is_relative_to(PREVIEWS):
        return _err(404, "aperçu indisponible")
    return FileResponse(p, media_type="video/mp4")


def _num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


async def cut(request: Request) -> Response:
    try:
        body = await request.json()
    except ValueError:
        return _err(400, "JSON invalide")
    if (not isinstance(body, dict) or not isinstance(body.get("name"), str)
            or not _num(body.get("threshold")) or not _num(body.get("min"))
            or not (body.get("max") is None or _num(body.get("max")))
            or not isinstance(body.get("framing", "blur_pad"), str)):
        return _err(400, "name, threshold, min, max (ou null) et framing attendus")
    mx = body.get("max")
    return await _call(webapi.run_cut, ROOT, body["name"], float(body["threshold"]), float(body["min"]),
                       None if mx is None else float(mx), body.get("framing", "blur_pad"))


app = Starlette(routes=[
    Route("/", index),
    Route("/api/plans", plans),
    Route("/api/plan/{name}", plan),
    Route("/api/plan/{name}/select", select, methods=["POST"]),
    Route("/api/plan/{name}/approve", approve, methods=["POST"]),
    Route("/api/plan/{name}/thumb/{n:int}", thumb),
    Route("/api/plan/{name}/preview/{n:int}", preview),
    Route("/api/inbox", inbox),
    Route("/api/music", music),
    Route("/api/tool", tool, methods=["POST"]),
    Route("/api/stack", stack, methods=["POST"]),
    Route("/api/videos", videos),
    Route("/api/cut", cut, methods=["POST"]),
    Route("/api/export", export, methods=["POST"]),
    Route("/api/job", job),
    Route("/api/cutjob", cutjob, methods=["GET", "POST"]),
    Route("/api/compose", compose, methods=["POST"]),
    Route("/api/clean/{level:int}", clean, methods=["GET", "POST"]),
])
