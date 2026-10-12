import { describe, expect, it } from "vitest";
import { bufferGeometry } from "../src/primitives.js";

// A big multi-material mesh: Safari's JavaScriptCore refuses more than 65,536
// spread arguments ("Maximum call stack size exceeded"), V8 somewhere past
// ~125,000. 200,000 triangles fails both if anything spreads `triMat`.
function bigMesh(tris, slots) {
  const positions = new Float32Array(tris * 9);
  const index = new Uint32Array(tris * 3);
  const triMat = new Uint32Array(tris);
  for (let t = 0; t < tris; t++) {
    for (let k = 0; k < 3; k++) {
      index[t * 3 + k] = t * 3 + k;
      positions[(t * 3 + k) * 3] = t + k;
    }
    triMat[t] = t % slots;
  }
  return { positions, index, triMat };
}

describe("bufferGeometry", () => {
  it("groups a 200,000-triangle mesh by material slot without spreading it", () => {
    const g = bufferGeometry(bigMesh(200_000, 3));
    expect(g.userData.slots).toBe(3);
    expect(g.groups.map((x) => [x.count, x.materialIndex])).toEqual(
      [[66_667 * 3, 0], [66_667 * 3, 1], [66_666 * 3, 2]]);
  });

  it("keeps a single-material mesh ungrouped", () => {
    const g = bufferGeometry(bigMesh(10, 1));
    expect(g.groups.length).toBe(0);
    expect(g.userData.slots).toBeUndefined();
  });
});
