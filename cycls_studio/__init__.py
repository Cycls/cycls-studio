"""Cycls Studio — a Blender-style 3D environment as a workspace app, with real
Blender (a deployed engine) behind it. See docs/studio.md.

Added to an agent as an extension, on its Web:

    cycls.Web().auth(cycls.Clerk()).use(cycls_studio.Studio())

once CYCLS_STUDIO_ENGINE names the engine deployment (and an API key can call it).
Unset, the tool is silently absent and the app's route unmounted, like Browser
without BROWSER_URL.
"""
import os

from cycls.extension import Extension, Tool, api_key

SLUG = "studio"
APP_DIR = f"apps/{SLUG}"
SCENE = f"{APP_DIR}/data/scene.json"


def engine_name():
    return os.environ.get("CYCLS_STUDIO_ENGINE") or None


def renderer_name():
    """Final renders may live on their own deployment; interactive ops then never
    queue behind a minute-long render."""
    return os.environ.get("CYCLS_STUDIO_RENDERER") or engine_name()


def configured():
    return bool(engine_name() and api_key())


class Studio(Extension):
    """The `studio` tool, and the route the Studio app calls Blender through."""
    name = "Studio"

    def configured(self):
        return configured()

    def tools(self):
        from . import tool
        return {"studio": (tool.STUDIO_TOOL, Tool(
            lambda inp, ws, **_: tool.run(inp, ws), tool.step, prompt=tool.STUDIO_GUIDANCE,
            interrupted="The scene may or may not have saved — `inspect` before repeating the change."))}

    def router(self, workspace, user):
        from .route import studio_router
        return studio_router(workspace, user)
