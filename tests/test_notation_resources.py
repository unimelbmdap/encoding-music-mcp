"""Notation pagination through resource reads, without tool sessions."""

import asyncio
import json

from fastmcp import Client
from fastmcp.resources import function_resource
from httpx import ASGITransport, AsyncClient

from src.encoding_music_mcp.server import mcp
from src.encoding_music_mcp.tools import notation


def test_notation_pages_and_replay_resource_route_need_no_session(monkeypatch):
    # Exercise real rendering and template reads without process/thread workers.
    async def render_inline(function, *args, **kwargs):
        return function(*args)

    monkeypatch.setattr(notation.to_process, "run_sync", render_inline)
    monkeypatch.setattr(function_resource, "call_sync_fn_in_threadpool", render_inline)
    filename = "Morley_1595_06_Lo_hear_another.mei"
    page_uri = f"notation://pages/{filename}/2"

    async def read_pages():
        async with Client(mcp) as client:
            full = await client.read_resource(page_uri)
            excerpt = await client.read_resource(
                f"notation://pages/{filename}/1?start_measure=1&end_measure=8"
            )
            return json.loads(full[0].text), json.loads(excerpt[0].text)

    full, excerpt = asyncio.run(read_pages())
    assert full["page"] == 2
    assert full["total_pages"] > 1
    assert full["svg"].startswith("<svg")
    assert excerpt["start_measure"] == 1
    assert excerpt["end_measure"] == 8
    assert excerpt["svg"].startswith("<svg")

    async def read_replay_resource():
        async with AsyncClient(
            transport=ASGITransport(app=mcp.http_app()), base_url="http://testserver"
        ) as client:
            report = "\n".join(
                json.dumps(item)
                for item in (
                    {
                        "type": "conversation_report",
                        "version": "1",
                        "session_id": "old-session",
                    },
                    {"tool_name": "show_notation", "args": {"filename": filename}},
                )
            )
            replay = await client.post("/reports/replay", content=report)
            assert replay.status_code == 200
            assert replay.json()["status"] == "success"
            app = replay.json()["calls"][0]["app"]
            assert app["result"]["structuredContent"]["page"] == 1
            viewer = await client.get(app["resource_url"])
            assert viewer.status_code == 200
            assert "readServerResource" in viewer.text

            response = await client.post(
                "/reports/replay/app-resource", json={"uri": page_uri}
            )
            assert response.status_code == 200
            content = response.json()["contents"][0]
            assert content["uri"] == page_uri
            assert content["mimeType"] == "application/json"
            assert json.loads(content["text"])["page"] == 2
            assert (
                await client.post(
                    "/reports/replay/app-resource", json={"uri": "file:///etc/passwd"}
                )
            ).status_code == 400

    asyncio.run(asyncio.wait_for(read_replay_resource(), timeout=10))
