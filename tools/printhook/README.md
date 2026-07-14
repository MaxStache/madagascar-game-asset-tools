# TFB print hook — see Madagascar's hidden log output

Every engine diagnostic **and** every script `print::op-code` in *Madagascar*
(`Game.exe`) is routed through a single `printf`-style logger:

```
0043e6f0   xor eax, eax
0043e6f2   ret          ; int __cdecl log(const char* fmt, ...)
```

The retail build compiled it down to `return 0`, so nothing is ever emitted.
This tool re-enables it. All output is sent to **`OutputDebugStringA`** (view
live with [Sysinternals DebugView](https://learn.microsoft.com/sysinternals/downloads/debugview))
and written to **`Game_prints.log`** next to the game.

## Option A — `d3d8.dll` proxy (recommended, standalone)

A drop-in DLL. `Game.exe` imports `Direct3DCreate8`, so Windows loads our
`d3d8.dll` from the game folder first; it forwards all four real d3d8 exports to
`C:\Windows\System32\d3d8.dll` and patches the logger on load. No external
loader needed.

**Build** (32-bit):
```
build.bat        REM from "x86 Native Tools Command Prompt for VS", or with MinGW i686
```
Produces `d3d8.dll`.

**Install:**
1. Copy `d3d8.dll` into the game folder, next to `Game.exe`
   (`C:\Users\maxst\Desktop\Madagascar\Game\`).
2. Launch DebugView (Run as admin; Capture → Capture Win32 + Capture Global Win32).
3. Run the game. Prints stream into DebugView and into `Game_prints.log`.

To uninstall: delete `d3d8.dll`.

> Safety: the hook verifies the exact stub bytes (`33 C0 C3`) at `+0x3e6f0`
> before patching, so it no-ops on any other or already-patched binary.

## Option B — x64dbg, zero build

For a quick look without compiling anything, see `capture_prints_x64dbg.txt`.
Sets a non-pausing log breakpoint on the logger. Fastest, but does not expand
`%d`/`%s` arguments (script `print` strings have none, so they show fine).

## Files
| file | purpose |
|------|---------|
| `d3d8_proxy.cpp` | proxy DLL + logger hook (Option A) |
| `d3d8.def` | exports mapping real d3d8 names to the forwarders |
| `build.bat` | 32-bit build (MSVC or MinGW) |
| `capture_prints_x64dbg.txt` | Option B recipe |
| `tfb_printhook.cpp` | same hook as a bare Ultimate-ASI-Loader `.asi` plugin (no forwarders) |

## How it works
The hook overwrites the stub's entry with `push &LogHook ; ret`. The logger is
`__cdecl` variadic with all arguments on the stack, so entering `LogHook` with
the identical frame is safe; `push/ret` is position-independent and clobbers no
registers. `LogHook` runs `_vsnprintf` over the varargs and emits the result.
