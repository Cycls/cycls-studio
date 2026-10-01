# Cycls Studio

A Blender-style 3D studio that any Cycls agent adds as an extension
(`cycls.Web().use(cycls_studio.Studio())`). Three parts, one repo:

- `cycls_studio/` — the Python package the agent imports: `Studio` (the `cycls.Extension`),
  `tool.py` (the `studio` tool), `route.py` (`POST /apps/studio/engine`, the app's relay to
  Blender), `scene.py` (the document — stdlib only, the one schema), `store.py`, `video.py`,
  `engine.py` (the `cycls.remote` client), `install.py`, `app/index.html` (the built app).
- `app/` — the Studio app's source (Preact + three.js). `npm run build` writes
  `cycls_studio/app/index.html` and refuses past 1.2 MB; the bundle is committed.
- `engine/` — the Blender engine, deployed on its own as `cycls-render` (a warm worker behind
  unshare + bwrap). It captures `cycls_studio/scene.py` by value at deploy.

The SDK side is generic and lives in the cycls repo: `cycls.Extension` / `Web().use` /
`cycls.extension` helpers (docs/notes/extensions.md) and the app bridge verbs `engine`,
`onCommand`, `ask` (docs/notes/apps.md). The package imports nothing private from the SDK —
keep it that way; if it needs more, add a helper to `cycls.extension`. Tests may reach into
SDK internals to check the seam (`tests/studio_test.py` registers the extension and drives
`build_tools`/`dispatch`).

How it works in depth: [docs/studio.md](docs/studio.md).

## Commands

```bash
uv sync --group test
uv run pytest tests/                                   # mocked (engine faked)
set -a && source .env && set +a                        # CYCLS_API_KEY
uv run pytest tests/live_test.py --live -v             # against the deployed engine
cd app && npm test                                     # vitest: doc, mesh, anim, app controller
cd app && npm run build                                # → cycls_studio/app/index.html
cd app && npm run schema                               # src/schema.json from scene.py (a test fails on drift)
cd engine && cycls deploy render_fn.py                 # the engine, Python 3.12
cd engine && PYTHONPATH=.. python studio_try.py dev selftest evaluate snapshot   # engine code on a cloud executor
```

`pyproject.toml` points `cycls` at a local SDK checkout (`../cycls-sdk-ext`, the
`feat/extensions` branch) until the extension hook is released.

## Gotchas

- The engine is shared: four instances, one job each. Redeploy it whenever `scene.py` or
  anything in `engine/` changes the protocol.
- The app is sandboxed (opaque origin, `connect-src 'none'`): every network call goes through
  the host bridge. Its viewport needs WebGL — check it in a browser (`app/dev/`), not vitest.
- The dev harness serves the bundle installed into `app/dev/ws` at startup: restart it after
  `npm run build`, and delete `app/dev/ws/apps/studio/data/*` for a fresh scene.
- Never leave an unminified bundle installed (the 1.2 MB budget).
- Check an mp4's frames with PyAV, not Blender's VSE (it can return frame 1 for every frame).
- On Windows, Python's `open(..., "w")` writes CRLF — pass `newline="\n"`.
