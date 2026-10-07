# The Studio's GPU renderer, on Modal: the same warm Blender worker as render_fn.py, with Cycles
# on a GPU. It takes `render` and `video` (and `ping`) — the long ops — while everything
# interactive stays on the Cycls engine, next to the agent.
#
#   modal secret create cycls-studio-renderer CYCLS_STUDIO_RENDERER_KEY=<a long random key>
#   modal deploy engine/modal_fn.py     → https://<workspace>--cycls-studio-renderer-web.modal.run
#
# An agent sends its renders here with
#
#   CYCLS_STUDIO_RENDERER=<that URL>
#   CYCLS_STUDIO_RENDERER_KEY=<the same key>
#
# and cycls_studio/engine.py speaks wire.py's frames to it: JSON and bytes, never a pickle.
#
# Two functions. `web` is the door: a small CPU container that checks the key and hands the frame
# on, so a stranger who finds the URL wakes that and never a GPU. `gpu` does the work and has no
# URL of its own. Blender runs bare there (bwrap's own /dev would hide the GPU): Modal's sandbox
# is the boundary, the container holds no secrets, and nothing tainted (script, import, encode)
# is accepted.
from pathlib import Path

import modal

import render_fn                       # BLENDER and _studio; it imports without the Cycls SDK

HERE = Path(__file__).parent
GPU = "L4"                             # 24 GB; a T4 is cheaper and slower, an A10G or L40S faster
OPS = {"render", "video", "ping"}


def _with_engine(image):
    """The engine's own files, beside this one as they are in the repo; render_fn reads the schema
    from ../cycls_studio/scene.py, which from /root is /cycls_studio/scene.py."""
    for name in ("render_fn.py", "worker.py", "studio_bpy.py", "scenes.py"):
        image = image.add_local_file(HERE / name, f"/root/{name}")
    return (image.add_local_file(HERE.parent / "cycls_studio" / "wire.py", "/root/wire.py")
            .add_local_file(HERE.parent / "cycls_studio" / "scene.py", "/cycls_studio/scene.py"))


_python = modal.Image.debian_slim(python_version="3.12")
gpu_image = _with_engine(
    # the X/GL client libraries Blender links against even in background mode (as render_fn's image)
    _python.apt_install("curl", "ca-certificates", "xz-utils", "libgl1", "libegl1", "libglib2.0-0",
                        "libx11-6", "libxi6", "libxrender1", "libxxf86vm1", "libxfixes3", "libxext6",
                        "libxkbcommon0", "libsm6", "libice6")
    .run_commands(f"curl -fsSL {render_fn._TARBALL} | tar -xJ -C /opt "
                  f"&& mv /opt/blender-{render_fn.BLENDER}-linux-x64 /opt/blender "
                  "&& ln -s /opt/blender/blender /usr/local/bin/blender "
                  "&& blender --version")
    .env({"CYCLS_STUDIO_DEVICE": "gpu"}))
web_image = _with_engine(_python.pip_install("fastapi[standard]==0.139.2"))

app = modal.App("cycls-studio-renderer")


# One render a container, as the engine has one an instance; it idles five minutes before it goes
# (a cold one boots Blender and loads the GPU kernels first). max_containers is the cost ceiling.
@app.function(image=gpu_image, gpu=GPU, cpu=8, memory=16384, timeout=900, scaledown_window=300, max_containers=2)
def gpu(frame: bytes) -> bytes:
    import wire

    meta, blobs = wire.decode(frame)
    op = meta.get("op")
    if op not in OPS:
        return wire.encode({"ok": False, "error": f"this renderer takes {', '.join(sorted(OPS))} — not {op!r}"})
    try:
        r = render_fn._studio(op, meta.get("scene"), blobs, meta.get("params"),
                              gz=bool(meta.get("gzip")), cache=meta.get("cache"), refs=meta.get("refs"))
    except Exception as e:                           # engine trouble, reported, not raised
        r = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:500]}"}
    return wire.encode(r, r.pop("files", None) or {})


@app.function(image=web_image, cpu=1, memory=2048, timeout=900, scaledown_window=120,
              secrets=[modal.Secret.from_name("cycls-studio-renderer")])
@modal.concurrent(max_inputs=16)
@modal.asgi_app()
def web():
    import hmac
    import os

    from fastapi import FastAPI, Request, Response

    import wire

    api, key = FastAPI(), os.environ["CYCLS_STUDIO_RENDERER_KEY"].encode()

    @api.post("/")
    async def call(request: Request):
        sent = request.headers.get("authorization", "").removeprefix("Bearer ").encode()
        if not hmac.compare_digest(sent, key):
            return Response(status_code=401)
        frame = await request.body()
        try:
            wire.decode(frame)                       # a frame at all, before a GPU is asked
        except ValueError as e:
            return Response(wire.encode({"ok": False, "error": f"bad request: {e}"}), status_code=400,
                            media_type="application/octet-stream")
        return Response(await gpu.remote.aio(frame), media_type="application/octet-stream")

    return api
