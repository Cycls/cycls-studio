# Cycls Studio

A Blender-style 3D studio for any [Cycls](https://github.com/Cycls/cycls) agent. The agent builds
a scene from a sentence and renders it with real Blender (Cycles). The person opens the same scene
as an app on the canvas, with an outliner, a viewport, Object and Edit modes, modifiers, materials,
a timeline and a Render button. What either side changes, the other sees.

## Add it to an agent

```python
import cycls
import cycls_studio

@cycls.agent(
    image=cycls.Image().pip("https://github.com/Cycls/cycls-studio/archive/refs/heads/main.zip"),
    web=cycls.Web().auth(cycls.Clerk()).use(cycls_studio.Studio()),
    volumes={"/workspace": cycls.Volume("my-agent")},
)
async def my_agent(context):
    async for ev in llm.run(context=context):
        yield ev
```

```
CYCLS_STUDIO_ENGINE=cycls-render      # the deployed Blender engine (engine/)
CYCLS_API_KEY=...                     # cycls.remote calls the engine with it: a key of the account that owns it
CYCLS_STUDIO_RENDERER=https://…       # optional: the GPU renderer (engine/modal_fn.py) for render and video
CYCLS_STUDIO_RENDERER_KEY=...         # its key
```

`.use(Studio())` adds the `studio` tool to every `llm.run()` of the agent and mounts the route the
app calls Blender through. Without the first two env vars, the tool isn't offered. A person can
switch it off in Settings like a builtin.

What the agent needs besides:

- A `cycls` with the extension hook (`cycls.Extension`, `Web().use`): the SDK's `feat/extensions`
  branch until it reaches main. An agent built on another SDK branch can't `.use()` anything.
- Python 3.12, as the engine runs: a call to it needs the same Python on both sides.
- `.auth(...)` on its `Web`, and a workspace volume: the Studio installs its app into each workspace.
- To pick up a change here, a new image: pin the package by commit
  (`…/cycls-studio/archive/<sha>.zip`) and bump the pin, since a `main.zip` line that hasn't
  changed leaves the old package in a cached layer.

## What's here

```
cycls_studio/   the package: the Studio extension, the `studio` tool, the app's engine route,
                scene.py (the document), store, video jobs, the installer, app/index.html (built)
app/            the app's source: Preact + three.js; `npm run build` writes cycls_studio/app/index.html
engine/         the Blender engine, deployed on its own as cycls-render (a warm, sandboxed worker)
tests/          the package's tests (pytest); app/tests/ has the app's (vitest)
examples/       studio.py, an agent with the Studio; render.py, a one-shot product render tool
docs/studio.md  how it all works
```

## Develop

```bash
uv sync --group test && uv run pytest tests/          # the package (engine faked)
uv run pytest tests/live_test.py --live               # against the deployed engine (CYCLS_API_KEY)
cd app && npm ci && npm test && npm run build         # the app
cd engine && cycls deploy render_fn.py                # the engine (Python 3.12)
```

`app/dev/` drives the built app headless in Chrome through the SDK's real shim and bridge: see
`app/dev/README.md`.
