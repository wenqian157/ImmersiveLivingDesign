# Immersive Living Design — Rebuild Notes

Placeholder for rebuilding the unfinished project from scratch. Sections marked _TBD_ are filled in as information arrives.

_Started: 2026-10-01 · Folder wiped for a fresh start: 2026-10-30_

## 1. Goal

Generate a VR room in the Quest 3 headset from physically tracked markers: a few dozen OptiTrack rigid bodies are tracked, each rigid-body ID stands for a room element (bed, table, wall, door, window, …), and the room geometry is generated from where those IDs are in space.

## 2. What was unfinished / why rebuild

_TBD — what worked, what didn't, what to keep vs. discard._

## 3. Target platform & hardware

- **Headset:** Meta Quest 3 (standalone Android build). Starting point of the rebuild.
- **Room:** 7 m (X) × 5.5 m (Z), origin at a corner, Y up (Motive default).
- **Tracking:** OptiTrack motion capture (Motive), dozens of rigid bodies, one per room element.
- Other external devices (lights, BLE, …): _TBD_

## 4. Features

| # | Feature | Status in old project | Plan for rebuild |
|---|---------|----------------------|------------------|
| 1 | VR project running on Quest 3 | existed (Unity 2022.3, URP, Oculus XR) | Unity 6 + URP, see §5 |
| 2 | Receive OptiTrack rigid-body poses in the headset | _TBD_ (old repo had Firebase + `LocateFurniture`) | _TBD — NatNet direct vs PC relay_ |
| 3 | Map rigid-body ID → room element (bed, table, wall, door, window…) | _TBD_ | config table, ID → prefab/generator |
| 4 | Generate room geometry from element poses | _TBD_ | procedural meshes |
| 5 | Walls with door/window openings (needs geometry boolean) | _TBD_ | 2D clip + extrude, not 3D CSG — see §5 |

## 5. Architecture / tech decisions

The project is built in **steps, not linearly** — each step is a self-contained piece; order of work is decided as we go.

- **Rendering (proposed 2026-10-30):** Unity 6 LTS + URP, Vulkan, Forward renderer (not Forward+/Deferred), Multiview (single-pass instanced), MSAA 4x, HDR off, post-processing off, Fixed Foveated Rendering on, IL2CPP ARM64, linear colour. _Awaiting confirmation._
- **XR plugin / SDK (2026-10-30):** Build profile **Meta Quest** (Platform Browser), which installs the Unity OpenXR plugin; add **Unity OpenXR: Meta** (`com.unity.xr.meta-openxr`) for Quest features, XR Interaction Toolkit for controllers. Not Android XR (that is Google/Samsung). Meta XR Core SDK only if a Meta-only feature is needed.
- **Wall openings (proposed 2026-10-30):** treat walls as planar: wall = 2D rectangle in its own plane, door/window = 2D rectangles subtracted from it, triangulate, extrude to thickness. Runs fast on Quest, no fragile 3D mesh CSG. Candidate libs: Clipper2 (C# port) for polygon clipping, LibTessDotNet / ear-clipping for triangulation. Fallback if real 3D CSG is ever needed: pb_CSG (Parabox, MIT, runtime). _Awaiting confirmation._
- **Pose transport (2026-10-30):** UDP, one JSON datagram per frame: `{"frame","t","bodies":[{"id","name","pos":[x,y,z],"rot":[qx,qy,qz,qw]}]}`, default port 9000. `dummy.py` stands in for Motive until a real NatNet bridge exists.
- **Where generation runs:** _TBD — on the Quest directly, or on a PC (next to Motive) that streams poses/meshes to the headset._
- **Space alignment:** _TBD — how OptiTrack world space is aligned with the Quest tracking space (e.g. rigid body on the headset)._

## 6. Open questions

- Does the room get generated once (static layout) or continuously while people move the markers?
- Can the Quest receive NatNet directly on the lab Wi-Fi, or is a PC relay needed/preferred?
- Door and window: are they tracked as their own rigid bodies, placed relative to the wall's rigid body, or both?

## 7. Log

Information received, in order.

- 2026-10-01 — Placeholder created.
- 2026-10-30 — Old project files and `.git` removed.
- 2026-10-30 — Project is composed of steps, worked non-linearly. Step 1: VR project on Quest 3. Discussed render pipeline choice (see §5).
- 2026-10-30 — Overall workflow: OptiTrack tracks dozens of rigid bodies; each ID is a room element; room is generated from their positions; walls/doors/windows need boolean geometry. Discussed doing it on Quest with custom scripts (see §5).
- 2026-10-30 — Folders arrived: `IDL_Oculus` (Unity 6000.6.3f1, URP 17.6, no XR packages yet), `NatNetSDK`, `UR3D_sample`, `rigidbody_design`. Room is **7 m × 5.5 m**. Added `NatNetSDK/dummy.py` (3 dummy walls over UDP/JSON, port 9000) and `IDL_Oculus/Assets/Scripts/WallUdpReceiver.cs` (receives + logs). No boolean yet.

---

## Appendix: the old project (for reference)

Still available at https://github.com/wenqian157/ImmersiveLivingDesign (last commit "add light control").

- Unity 2022.3.62f1, URP 14.0.12
- XR Interaction Toolkit 2.6.4, Oculus XR 4.5.1, OpenXR 1.14.3
- Third-party: Firebase, Shatalmic (Bluetooth LE), Hessburg SunLight, JsonDotNet, Oculus
- Scripts: `BLEController`, `FirebaseServer`, `LightController`, `LocateFurniture`, `Logs`, `OculusControllerActions`, `OVRController`, `SimpleCameraController`, `TempController`
- Models: chair, klippansofa, lamp (`.fbx`)

## Appendix: repo layout (2026-10-30)

- `IDL_Oculus/` — the VR Unity project (6000.6.3f1, URP 17.6). Scripts in `Assets/Scripts/`.
- `NatNetSDK/` — OptiTrack NatNet SDK (C++ headers/libs, samples incl. `Samples/PythonClient`), plus our `dummy.py`.
- `UR3D_sample/` — a second Unity project (sample), purpose _TBD_.
- `rigidbody_design/` — photos + `combination.csv` of the rigid-body marker designs.
