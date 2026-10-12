// A stand-in for the chat host: the real shim + the real bridge, the real Studio
// bundle, and a tiny server for files + the real studio_router.
import { injectShim } from "@client/components/app-shim";
import { attachBridge, sendAppCommand } from "@client/components/app-bridge";

declare global { interface Window { __log: unknown[]; __appData: Record<string, unknown>; __push: (c: unknown) => void; __open: (path: string, same?: boolean) => void; __asks: string[] } }
const APP = "apps/studio/index.html";
window.__log = [];
window.__appData = {};
window.__asks = [];
const log = (...a: unknown[]) => { window.__log.push(a); if (window.__log.length > 500) window.__log.shift(); };

async function main() {
  const html = await (await fetch("/studio.html")).text();
  const frame = document.getElementById("app") as HTMLIFrameElement;
  attachBridge({
    frame,
    appPath: APP,
    readFile: async (p) => {
      const r = await fetch(`/files/${p}`);
      log("read", p, r.status);
      if (!r.ok) throw Object.assign(new Error(`HTTP ${r.status}`), { status: r.status });
      return r.text();
    },
    writeFile: async (p, text) => {
      const r = await fetch(`/files/${p}`, { method: "PUT", body: text });
      log("write", p, text.length, r.status);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
    },
    appData: async (slug, op) => {
      log("data", slug, op);
      const key = `${op.who || "me"}:${op.key}`;
      if (op.op === "put") { window.__appData[key] = op.value; return { ok: true }; }
      return window.__appData[key] ?? null;
    },
    callEngine: async (slug, op, payload) => {
      const t0 = performance.now();
      const res = await fetch(`/apps/${slug}/engine`, {
        method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ ...payload, op }),
      });
      log("engine", op, res.status, Math.round(performance.now() - t0));
      if (!res.ok) {
        let detail = "";
        try { detail = (await res.json()).detail ?? ""; } catch { /* not JSON */ }
        throw Object.assign(new Error(detail || `HTTP ${res.status}`), { status: res.status });
      }
      return res.json();
    },
    onAsk: (t) => { window.__asks.push(t); },
    onError: (m) => log("crash", m),
    context: { theme: "dark", locale: "en" },
  });
  const late = new URLSearchParams(location.search).get("late");
  if (late) { frame.style.width = "0px"; frame.style.height = "0px"; setTimeout(() => { frame.style.width = ""; frame.style.height = ""; }, +late); }
  // A file opened from Files, as the chat hands it over: held for an app that isn't up yet.
  // `?open=<path>` sends it before the frame exists, as a click that also opens the Studio does.
  window.__open = (path, same = false) =>
    sendAppCommand(APP, { type: "open_file", path, name: path.split("/").pop(), same }, { hold: true });
  const open = new URLSearchParams(location.search).get("open");
  if (open) window.__open(open);
  frame.srcdoc = injectShim(html);
  window.__push = (command) => sendAppCommand(APP, command);
}
main();
