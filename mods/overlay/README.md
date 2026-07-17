# Game.exe overlay

A proxy `d3d8.dll` that injects itself into `Game.exe` and renders a real
Dear ImGui overlay on top of the game (demo window + a small test window,
mouse/keyboard interactive, toggled with INSERT).

## How it works

`Game.exe` only imports one function from `d3d8.dll`: `Direct3DCreate8`
(confirmed via Ghidra's import list). So the proxy just needs to:

1. Export `Direct3DCreate8` itself, forward the call to the *real*
   `%SystemRoot%\System32\d3d8.dll` (loaded by absolute path so it doesn't
   recursively load our own same-named DLL).
2. Patch the returned `IDirect3D8` interface's `CreateDevice` vtable slot.
3. When the game calls `CreateDevice`, call through to the real
   implementation, then patch the resulting `IDirect3DDevice8`'s `EndScene`
   and `Reset` vtable slots too, and initialize ImGui + subclass the game's
   window (`WndProc`) for input.
4. In our `EndScene` hook, run an ImGui frame and render its draw data, then
   call the real `EndScene`.

Vtable slots are patched by numeric index (`d3d8_min.h`) rather than by
declaring the full ~95-method D3D8 interface, since modern Windows SDKs don't
ship the legacy D3D8 headers. Every index and enum value in `d3d8_min.h` was
cross-checked against Wine's `d3d8.h`/`d3d8types.h` (kept in `reference/` --
an ABI-exact reimplementation of D3D8, since real D3D8 games would crash on
Wine if these were wrong) rather than reconstructed from memory.

## Dear ImGui integration

`imgui/` vendors real Dear ImGui **1.91.9b** (core + the official Win32
platform backend, used unmodified) plus a **hand-written D3D8 renderer
backend** (`imgui_impl_dx8.cpp/h`) -- there is no official ImGui backend for
D3D8 (support starts at D3D9), so this was ported from the official
`imgui_impl_dx9.cpp` of the same release. The differences it accounts for
(all documented in `imgui_impl_dx8.cpp`'s header comment):

- D3D8's state-block API is token-based (`CreateStateBlock`/`ApplyStateBlock`/
  `DeleteStateBlock(DWORD)` directly on the device) rather than the
  `IDirect3DStateBlock9` object D3D9 introduced.
- No `SetFVF` -- D3D8's `SetVertexShader(DWORD)` does double duty as FVF code
  or shader handle.
- No sampler states -- texture filtering/addressing goes through
  `SetTextureStageState` with `D3DTSS_MINFILTER`/`MAGFILTER`/`ADDRESSU`/`ADDRESSV`.
- **No scissor test** (`SetScissorRect`/`D3DRS_SCISSORTESTENABLE` were added in
  D3D9). Known limitation: ImGui draw commands aren't clipped to their
  window's clip rect. Most normal usage won't show it; a widget that
  overflows its window (e.g. an open combo box near a screen edge) may render
  outside its parent's bounds.
- `CreateTexture`/`CreateVertexBuffer`/`CreateIndexBuffer` lack the trailing
  shared-handle parameter D3D9 added.
- Always converts to `D3DFMT_A8R8G8B8` (skipped the D3D9 backend's
  native-RGBA-format detection dance).
- 16-bit indices only.

## Build

Open `d3d8_proxy.sln` in Visual Studio, **make sure the platform selector
says `Win32` (not x64)** -- `Game.exe` is a 32-bit process, a 64-bit DLL
cannot be loaded into it -- and build. If VS asks to retarget the Windows SDK
version, let it.

Output: `bin\Win32\Release\d3d8.dll` (or `Debug\` for the debug build).

## Install / run

1. Copy the built `d3d8.dll` into the same folder as `Game.exe`.
2. Launch the game normally.
3. Press **INSERT** to toggle the overlay on/off. While visible, mouse and
   keyboard input goes to ImGui first; the game only sees input ImGui isn't
   using (`io.WantCaptureMouse`/`WantCaptureKeyboard`).

To remove it, just delete the `d3d8.dll` you copied next to `Game.exe` --
nothing else on disk is touched.

## Next steps

- Replace the demo window / test window in `overlay.cpp` with real content.
- Feed it real data: `formats/lib/entityAtributeDocs/CProtoActor.py`'s field
  offsets (see project memory `ghidra_cprotoactor_field_offsets`) are exactly
  what you'd want to read out of a live `CProtoActor` instance's memory for
  an in-game actor inspector -- offsets there are object-relative and were
  verified against Game.exe's own getter code.
- If the missing scissor/clip-rect support ever becomes a visible problem,
  the classic D3D8-era workaround is stencil-buffer-based clipping (render a
  mask per clip rect, stencil-test subsequent draws against it) -- more work,
  and needs the device's swapchain to actually have a stencil buffer, which
  isn't guaranteed by `Game.exe`'s own `D3DPRESENT_PARAMETERS`.
