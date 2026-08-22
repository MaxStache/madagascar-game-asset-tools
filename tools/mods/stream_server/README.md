# Game.exe stream injection server

A proxy `d3d8.dll` that injects itself into `Game.exe` and runs a tiny local
HTTP server (`127.0.0.1:6742`). `POST /stream` with the raw stream bytes as
the request body, and those bytes get written to a temp file and fed into
the game's own resource manager exactly the way a real disk-backed
`LoadStreamFile` call would.

## How it works

`Game.exe` only imports one function from `d3d8.dll`: `Direct3DCreate8`
(confirmed via Ghidra's import list). So the proxy:

1. Exports `Direct3DCreate8` itself, forwards the call to the *real*
   `%SystemRoot%\System32\d3d8.dll` (loaded by absolute path so it doesn't
   recursively load our own same-named DLL).
2. Patches the returned `IDirect3D8` interface's `CreateDevice` vtable slot,
   and once a device exists, its `EndScene` vtable slot too -- purely to get
   a safe, once-per-frame callback on the game's own main thread. No
   rendering happens here.
3. On `DLL_PROCESS_ATTACH`, starts a background thread running a minimal
   blocking HTTP/1.1 server on `127.0.0.1:6742`. It understands exactly one
   route: `POST /stream`, body = raw stream bytes. Everything else gets a
   404. Each accepted request's body is heap-copied and pushed onto a
   mutex-guarded queue -- **not** acted on immediately, since none of the
   game's resource-manager code takes its own locks and calling into it from
   an arbitrary thread while the main thread is also using it would race.
4. Every `EndScene` (i.e. once per rendered frame, on the main thread), the
   queue is drained. Each buffered stream is written to a uniquely-named
   temp file (`%TEMP%\stream_inject_<tick>_<counter>.stream`), then handed
   to the game via three internal (unexported, Ghidra-recovered) functions
   in `Game.exe` itself:

   ```
   CreateAndLoadStreamResource(resourceType=2, mode=1, tempFilePath)
   WaitForStreamResourceReady(handle)   // runs the real chunk-dispatch pump loop
   FinalizeStreamResource(handle, &outResult)
   ```

### Why a temp file, not a pure in-memory buffer

`CreateAndLoadStreamResource` dispatches on `resourceType`. Type 3
("WrapMemoryBufferAsStreamResource") looks like the obvious pure-in-memory
route -- it wraps a raw `{dataPtr,size}` pair directly, no disk I/O -- but it
marks the resource ready *immediately*. That specifically skips the pump
loop inside `WaitForStreamResourceReady` that does the actual work for
`resourceType=2`: read a chunk header (`RwStreamReadChunkHeader`), look up
that chunk's type in a global handler registry populated once at startup
(e.g. `FUN_00552f00(0x704, CreateEntity_ChunkHandler)` -- `0x704` is
`MAKECHUNKID(vendorID=7 "CRITERIONRM", chunkID=4 "strfunc_CreateEntity")`,
matching the enum in `stream_nettest_pyport.py`), and invoke it. Type 3
structurally cannot reach that dispatcher.

This was confirmed empirically, not just by reading the code: a real
`.stream` file POSTed through the type-3 path produced a valid resource
handle (`CreateAndLoadStreamResource` succeeded, logged in DebugView) but no
visible in-game effect whatsoever -- because nothing ever ran
`RwStreamReadChunkHeader` against it.

Reproducing the same effect purely in memory would mean faking the device
abstraction underneath `resourceType=2` (pooled "file slot" objects behind a
vtable -- `Open`/`Exists`/poll/signal methods are mapped from Ghidra,
`Read`/`Seek`/`Close` are not), which risks corrupting engine state on a
struct-layout mistake rather than just failing to load. Going through a real
temp file reuses the exact, already-correct code path instead.

Temp files are **not deleted** after injection: `WaitForStreamResourceReady`
blocks until the resource is fully loaded, so by the time control returns to
us the game should be done reading it -- but if that assumption turns out to
be wrong for some resource type, deleting a still-open file is a worse
failure mode than leaving a harmless file in `%TEMP%`.

## Build

Open `stream_server.sln` in Visual Studio, **make sure the platform selector
says `Win32` (not x64)** -- `Game.exe` is a 32-bit process, a 64-bit DLL
cannot be loaded into it -- and build. Output: `bin\Win32\Release\d3d8.dll`
(or `Debug\` for the debug build).

## Install / run

1. Copy the built `d3d8.dll` into the same folder as `Game.exe`.
2. Launch the game normally. Once it's rendering (i.e. past the point
   `CreateDevice`/`EndScene` start getting called), the server is live.
3. From anywhere on the same machine (PowerShell's `curl` alias doesn't
   support `--data-binary @file`, use `curl.exe` explicitly, or
   `post_stream.ps1` in this folder):

   ```
   curl.exe --data-binary @some_asset.stream http://127.0.0.1:6742/stream
   ```

   A `200 OK` means the bytes were queued; actual injection happens on the
   next frame. Check `Game.exe`'s debug output (e.g. via DebugView, run as
   Administrator, Capture Win32 enabled) for
   `[stream_inject] injected <path> -> handle 0x...` to confirm it landed,
   or `CreateAndLoadStreamResource returned null` / the SEH-caught exception
   message if it didn't.

To remove it, delete the `d3d8.dll` you copied next to `Game.exe` -- nothing
else on disk is touched (aside from temp files under `%TEMP%`).

## Next steps

- No authentication/validation on the HTTP endpoint -- it's bound to
  `127.0.0.1` only, but any local process (or anything that can reach
  localhost, e.g. through port-forwarding software) can POST to it while the
  game is running.
- If the temp-file approach turns out to be too slow or visible for some
  use case, the next step toward a true in-memory path is filling in the
  remaining device vtable slots (`Read`/`Seek`/`Close`) and the pooled
  "file slot" struct layout referenced in `stream_inject.h`'s comments.
