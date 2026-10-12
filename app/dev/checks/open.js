// A .blend opened from Files, as the chat hands it over (`__open`, or `?open=` for one handed
// to a Studio that isn't up yet). Needs a model file in the workspace: globalThis.FILE, or
// exports/cube.blend — make one with
//   curl -X POST :8094/apps/studio/engine -H 'content-type: application/json' \
//        -d '{"op":"export","params":{"format":"blend"},"name":"cube"}'
// on a fresh workspace (data/scene.json deleted): the first open then needs no question.
const HOST = globalThis.HOST || "http://127.0.0.1:8094/";
const FILE = globalThis.FILE || "exports/cube.blend";
const state = () => evalApp(`(() => { const s = __studio.state; return JSON.stringify({ locked: s.locked, busy: s.busy,
  opening: s.opening, toast: s.toast && s.toast.text, objects: Object.keys(s.doc.objects).sort(), camera: s.doc.render.camera,
  rev: s.doc.rev, undo: s.undo.length && s.undo.at(-1).label, status: s.status }); })()`).then(JSON.parse);
const settled = async (ms = 240000) => {
  for (const t0 = Date.now(); Date.now() - t0 < ms; await sleep(500)) { const s = await state(); if (!s.locked) return s; }
  throw new Error("still opening");
};
const disk = async () => JSON.parse(await (await fetch(`${HOST}files/apps/studio/data/scene.json`)).text());
const button = (label) => evalApp(`(() => { const b = [...document.querySelectorAll(".dialog button")].find((x) => x.textContent === ${JSON.stringify(label)});
  if (!b) return null; const r = b.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()`);
const out = {};

// 1. Handed over before the app is up: held, then opened straight into the untouched scene.
await goto(`${HOST}?open=${encodeURIComponent(FILE)}`);
await sleep(1500);
out.held = await state().catch((e) => ({ error: String(e) }));
await shot("open-0-opening");
out.first = await settled();
out.firstDisk = (({ rev, by, objects }) => ({ rev, by, objects: Object.keys(objects).sort() }))(await disk());
await sleep(600);
await shot("open-1-opened");

// 2. The same file again, said to be the one that's open: only a word.
await evalHost(`__open(${JSON.stringify(FILE)}, true)`);
await sleep(300);
out.same = await state();

// 3. A scene that's someone's now: asked. Escape leaves it; Add brings the file in beside it.
await evalHost(`__open(${JSON.stringify(FILE)})`);
await sleep(300);
out.asked = await state();
await shot("open-2-asked");
const title = await evalApp(`(() => { const r = document.querySelector(".dialog b").getBoundingClientRect(); return [r.left + 4, r.top + 4]; })()`);
await click(title[0], title[1]);                     // the keys go to the frame; a click inside the question leaves it up
await sleep(100);
out.stillAsked = !!(await state()).opening;
await key("Escape");
await sleep(200);
out.escaped = (await state()).opening;
await evalHost(`__open(${JSON.stringify(FILE)})`);
await sleep(300);
const add = await button("Add to the scene");
await click(add[0], add[1]);
await sleep(300);
out.adding = await state();
await shot("open-2b-adding");
out.added = await settled();
await sleep(600);
await shot("open-3-added");

// 4. Open, from the question: in place of the scene. Undo brings the last one back.
await evalHost(`__open(${JSON.stringify(FILE)})`);
await sleep(300);
const open = await button("Open");
await click(open[0], open[1]);
out.replaced = await settled();
await evalApp("__studio.actions.undo()");
await sleep(300);
out.undone = (await state()).objects;
out.console = console_.filter((l) => /exception|error/i.test(l)).slice(-5);
return out;
