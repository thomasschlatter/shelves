"""
Generate a self-contained interactive viewer (viewer.html) with the model
geometry baked in. Opens by double-click (file://) — no server needed.

Features: orbit/zoom, an EXPLODE slider that pulls every board apart along its
direction from the assembly centre, per-part show/hide, isolate-on-click,
wireframe + auto-rotate toggles, and proper lighting.
"""
import json
import os

import numpy as np

import record_storage as m

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..")


def hexcolor(mesh):
    c = np.asarray(mesh.visual.face_colors)[0][:3]
    return "#%02x%02x%02x" % tuple(int(v) for v in c)


def part_payload(parts):
    """Vertices/indices in Y-up three.js space: (x, y, z)_model -> (x, z, -y)."""
    data = []
    for name, mesh in parts.items():
        v = mesh.vertices.astype(float)
        three_v = np.column_stack([v[:, 0], v[:, 2], -v[:, 1]])  # swap to Y-up
        data.append({
            "name": name,
            "color": hexcolor(mesh),
            "positions": three_v.flatten().round(4).tolist(),
            "indices": mesh.faces.astype(int).flatten().tolist(),
        })
    return data


HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vinyl Record Storage — Exploded Viewer</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; overflow: hidden;
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif; }
  #app { position: fixed; inset: 0; }
  canvas { display: block; }
  #panel {
    position: fixed; top: 14px; left: 14px; width: 268px; max-height: calc(100% - 28px);
    background: rgba(20,22,26,.82); backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,.09); border-radius: 14px;
    color: #e9edf2; padding: 16px 16px 12px; display: flex; flex-direction: column;
    box-shadow: 0 12px 40px rgba(0,0,0,.45);
  }
  #panel h1 { font-size: 14px; margin: 0 0 2px; letter-spacing: .2px; }
  #panel .sub { font-size: 11px; color: #97a1ad; margin-bottom: 14px; }
  .row { display: flex; align-items: center; gap: 8px; margin: 9px 0; font-size: 12px; }
  .row label { flex: 1; color: #c4ccd4; }
  input[type=range] { width: 100%; accent-color: #d9a066; }
  .val { font-variant-numeric: tabular-nums; color: #d9a066; width: 30px; text-align: right; }
  .btns { display: flex; gap: 6px; margin: 10px 0 4px; }
  button {
    flex: 1; font-size: 11px; padding: 6px 4px; cursor: pointer; color: #e9edf2;
    background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12);
    border-radius: 8px; transition: background .15s;
  }
  button:hover { background: rgba(255,255,255,.14); }
  button.active { background: #d9a066; color: #201a12; border-color: #d9a066; }
  .parts { margin-top: 8px; overflow-y: auto; border-top: 1px solid rgba(255,255,255,.09);
    padding-top: 8px; }
  .parts::-webkit-scrollbar { width: 7px; }
  .parts::-webkit-scrollbar-thumb { background: rgba(255,255,255,.16); border-radius: 4px; }
  .pitem { display: flex; align-items: center; gap: 7px; font-size: 11.5px; padding: 3px 4px;
    border-radius: 6px; cursor: pointer; color: #c4ccd4; }
  .pitem:hover { background: rgba(255,255,255,.07); color: #fff; }
  .pitem.off { opacity: .38; }
  .pitem .sw { width: 10px; height: 10px; border-radius: 3px; flex: none; }
  .pitem .nm { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .pitem .iso { font-size: 10px; color: #7f8a96; opacity: 0; }
  .pitem:hover .iso { opacity: 1; }
  #hint { position: fixed; bottom: 12px; left: 50%; transform: translateX(-50%);
    font-size: 11px; color: #8a94a0; background: rgba(20,22,26,.7); padding: 5px 12px;
    border-radius: 20px; border: 1px solid rgba(255,255,255,.08); }
  #tag { position: fixed; bottom: 12px; right: 14px; font-size: 10.5px; color: #6b7580; }
</style>
</head>
<body>
<div id="app"></div>
<div id="panel">
  <h1>Vinyl Record Storage</h1>
  <div class="sub">__SUBTITLE__ · __NPARTS__ parts</div>
  <div class="row">
    <label>Explode</label>
    <input id="explode" type="range" min="0" max="100" value="0">
    <span class="val" id="explodeVal">0</span>
  </div>
  <div class="btns">
    <button id="btnRotate">Auto-rotate</button>
    <button id="btnWire">Wireframe</button>
  </div>
  <div class="btns">
    <button id="btnRecords" class="active">Records</button>
    <button id="btnLegs">Toggle legs</button>
  </div>
  <div class="btns">
    <button id="btnAll">Show all</button>
    <button id="btnReset">Reset view</button>
  </div>
  <div class="parts" id="parts"></div>
</div>
<div id="hint">drag to orbit · scroll to zoom · right-drag to pan · click a part name to isolate</div>
<div id="tag">Jen Woodhouse plan · parametric reconstruction</div>

<script type="importmap">
{ "imports": {
  "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
  "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
}}
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const PARTS = __DATA__;

const app = document.getElementById('app');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
app.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0f1114);

const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

const camera = new THREE.PerspectiveCamera(42, innerWidth / innerHeight, 0.1, 5000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;

// Lights
const hemi = new THREE.HemisphereLight(0xffffff, 0x30343a, 0.55);
scene.add(hemi);
const key = new THREE.DirectionalLight(0xffffff, 2.4);
key.position.set(40, 70, 55);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
key.shadow.camera.near = 1; key.shadow.camera.far = 400;
const s = 60;
key.shadow.camera.left = -s; key.shadow.camera.right = s;
key.shadow.camera.top = s; key.shadow.camera.bottom = -s;
key.shadow.bias = -0.0004;
scene.add(key);
const fill = new THREE.DirectionalLight(0xbfd2ff, 0.5);
fill.position.set(-50, 30, -40);
scene.add(fill);

// Build meshes
const group = new THREE.Group();
scene.add(group);
const box = new THREE.Box3();
const meshes = [];

for (const p of PARTS) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(p.positions, 3));
  g.setIndex(p.indices);
  g.computeVertexNormals();
  const isSteel = p.name.startsWith('leg');
  const mat = new THREE.MeshStandardMaterial({
    color: new THREE.Color(p.color),
    roughness: isSteel ? 0.5 : 0.72,
    metalness: isSteel ? 0.85 : 0.0,
  });
  const mesh = new THREE.Mesh(g, mat);
  mesh.castShadow = true; mesh.receiveShadow = true;
  mesh.userData.name = p.name;
  g.computeBoundingBox();
  mesh.userData.home = g.boundingBox.getCenter(new THREE.Vector3());
  group.add(mesh);
  meshes.push(mesh);
  box.expandByObject(mesh);
}

const center = box.getCenter(new THREE.Vector3());
const size = box.getSize(new THREE.Vector3());
const radius = size.length() / 2;

// explode direction per part = from assembly centre to part centre
for (const mesh of meshes) {
  mesh.userData.dir = mesh.userData.home.clone().sub(center);
}

// Ground shadow catcher
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(2000, 2000),
  new THREE.ShadowMaterial({ opacity: 0.32 }));
ground.rotation.x = -Math.PI / 2;
ground.position.y = box.min.y - 0.2;
ground.receiveShadow = true;
scene.add(ground);
const grid = new THREE.GridHelper(400, 80, 0x2a2f36, 0x1c2026);
grid.position.y = box.min.y - 0.2;
scene.add(grid);

// Frame the model
function frameView() {
  const dist = radius / Math.sin((camera.fov * Math.PI / 180) / 2) * 0.62;
  camera.position.set(center.x + dist * 0.75, center.y + dist * 0.55, center.z + dist * 0.9);
  controls.target.copy(center);
  camera.near = dist / 100; camera.far = dist * 20;
  camera.updateProjectionMatrix();
  controls.update();
}
frameView();

// ---- Explode ----
let explodeAmt = 0;
function applyExplode() {
  for (const mesh of meshes) {
    mesh.position.copy(mesh.userData.dir).multiplyScalar(explodeAmt * 1.4);
  }
}
const explodeEl = document.getElementById('explode');
const explodeVal = document.getElementById('explodeVal');
explodeEl.addEventListener('input', () => {
  explodeAmt = explodeEl.value / 100;
  explodeVal.textContent = explodeEl.value;
  applyExplode();
});

// ---- Part list ----
const partsEl = document.getElementById('parts');
const rowByName = {};
for (const mesh of meshes) {
  const row = document.createElement('div');
  row.className = 'pitem';
  row.innerHTML = `<span class="sw" style="background:${
    '#' + mesh.material.color.getHexString()}"></span>` +
    `<span class="nm">${mesh.userData.name}</span><span class="iso">isolate</span>`;
  row.addEventListener('click', (e) => {
    if (e.target.classList.contains('sw')) { toggle(mesh, row); return; }
    isolate(mesh);
  });
  row.querySelector('.sw').addEventListener('click', (e) => {
    e.stopPropagation(); toggle(mesh, row);
  });
  partsEl.appendChild(row);
  rowByName[mesh.userData.name] = row;
}
function toggle(mesh, row) {
  mesh.visible = !mesh.visible;
  row.classList.toggle('off', !mesh.visible);
}
function isolate(target) {
  const soloing = meshes.some(m => m !== target && m.visible) ||
    meshes.every(m => m.visible);
  for (const mesh of meshes) {
    mesh.visible = soloing ? (mesh === target) : true;
    rowByName[mesh.userData.name].classList.toggle('off', !mesh.visible);
  }
}
function showAll() {
  for (const mesh of meshes) {
    mesh.visible = true;
    rowByName[mesh.userData.name].classList.remove('off');
  }
}

// ---- Buttons ----
let autorotate = false, wire = false;
const bR = document.getElementById('btnRotate');
const bW = document.getElementById('btnWire');
bR.onclick = () => { autorotate = !autorotate; bR.classList.toggle('active', autorotate); };
bW.onclick = () => {
  wire = !wire; bW.classList.toggle('active', wire);
  for (const mesh of meshes) mesh.material.wireframe = wire;
};
document.getElementById('btnAll').onclick = showAll;
document.getElementById('btnReset').onclick = frameView;
function toggleGroup(prefix) {
  for (const mesh of meshes) {
    if (mesh.userData.name.startsWith(prefix)) {
      mesh.visible = !mesh.visible;
      rowByName[mesh.userData.name].classList.toggle('off', !mesh.visible);
    }
  }
}
document.getElementById('btnLegs').onclick = () => toggleGroup('leg');
const bRec = document.getElementById('btnRecords');
bRec.onclick = () => {
  toggleGroup('records');
  const anyOn = meshes.some(m => m.userData.name.startsWith('records') && m.visible);
  bRec.classList.toggle('active', anyOn);
};

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

(function loop() {
  requestAnimationFrame(loop);
  if (autorotate) group.rotation.y += 0.0035;
  controls.update();
  renderer.render(scene, camera);
})();
</script>
</body>
</html>
"""


def write_viewer(parts, subtitle, filename):
    payload = part_payload(parts)
    html = (HTML
            .replace("__DATA__", json.dumps(payload))
            .replace("__NPARTS__", str(len(parts)))
            .replace("__SUBTITLE__", subtitle))
    path = os.path.join(OUT, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", path, f"({len(parts)} parts, {os.path.getsize(path)//1024} KB)")


def main():
    write_viewer(m.build_parts(m.ROW_DEPTH_STD, with_records=True),
                 "Standard · 55¼ × 26¼ × 18½ in", "viewer.html")
    write_viewer(m.build_parts(m.ROW_DEPTH_COMPACT, with_records=True),
                 "Compact · 55¼ × 18¼ × 18½ in", "viewer_compact.html")
    write_viewer(m.build_parts(m.ROW_DEPTH_STD, with_records=True,
                               seven_inch_cols={1, 2}),
                 "7\" middle sections · 46½ × 26¼ × 18½ in", "viewer_7inch.html")


if __name__ == "__main__":
    main()
