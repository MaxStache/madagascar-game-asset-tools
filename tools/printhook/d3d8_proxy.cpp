// d3d8.dll proxy that re-enables Madagascar (Game.exe) logging.
//
// Drop the built d3d8.dll next to Game.exe. Game.exe statically imports
// Direct3DCreate8, so Windows loads THIS dll from the game folder first. We:
//   1. forward all d3d8 exports to the real C:\Windows\System32\d3d8.dll, and
//   2. patch Game.exe's stubbed logger so all output becomes visible.
//
// Every engine log AND every script `print::op-code` funnels through one
// variadic logger the retail build stubbed to `return 0`:
//     0043e6f0   33 C0   xor eax, eax
//     0043e6f2   C3      ret        ; int __cdecl log(const char* fmt, ...)
// We overwrite its entry with `push &LogHook ; ret`. The stub takes no
// registers (cdecl, args on the stack), so entering our function with the same
// frame is safe; push/ret is position-independent and clobbers no registers.
//
// Output -> OutputDebugStringA (watch with Sysinternals DebugView) and
// Game_prints.log in the working directory.
//
// Build (32-bit, static CRT): see build.bat.

#include <windows.h>
#include <cstdio>
#include <cstdarg>
#include <cstring>
#include <cstdint>

// ---------------------------------------------------------------------------
// Logger hook
// ---------------------------------------------------------------------------
static const uintptr_t LOGGER_RVA = 0x3e6f0;   // VA 0x0043e6f0 - base 0x00400000
static FILE*            g_log = nullptr;
static CRITICAL_SECTION g_cs;

// CAUTION: 0x0043e6f0 is BOTH the real variadic logger AND the shared no-op
// stub the compiler folded into dozens of vtable slots (every `{return 0;}`
// became this one address). Those vtable calls pass a `this`/int as the first
// arg, NOT a format string. So we must verify the first arg is a readable,
// printable C-string before touching it, and guard everything with SEH — a
// non-logging call must do nothing and never fault.

// SEH probe: is p a readable, printable, NUL-terminated string? (no C++ objects)
static bool ProbeCStr(const char* p) {
    __try {
        if ((uintptr_t)p < 0x10000) return false;          // null / low ints
        for (int i = 0; i < 2048; ++i) {
            unsigned char c = ((const unsigned char*)p)[i];
            if (c == 0) return i > 0;                       // terminator, non-empty
            if (c != '\t' && c != '\n' && c != '\r' && (c < 0x20 || c > 0x7E))
                return false;                               // not text -> not a fmt
        }
        return false;                                       // unterminated / too long
    } __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
}

// Reject junk that survives ProbeCStr: garbage pointers from the no-op vtable
// calls sometimes land on a couple of printable bytes ("p", "]", "/", "p/]").
// Real log lines / script prints are wordy, so require a minimum length and a
// couple of letters. Tune these two if noise or dropped lines appear.
static const int MIN_MSG_LEN   = 3;
static const int MIN_MSG_ALPHA = 2;

static bool LooksLikeMessage(const char* s) {
    int len = 0, alpha = 0;
    for (; s[len] && len < 4096; ++len) {
        unsigned char c = (unsigned char)s[len];
        if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z')) ++alpha;
    }
    return len >= MIN_MSG_LEN && alpha >= MIN_MSG_ALPHA;
}

static int SafeVsnprintf(char* out, size_t n, const char* fmt, va_list ap) {
    __try { return _vsnprintf(out, n, fmt, ap); }
    __except (EXCEPTION_EXECUTE_HANDLER) { return -1; }
}

static void Emit(const char* buf, int n) {
    EnterCriticalSection(&g_cs);
    OutputDebugStringA(buf);
    if (g_log) {
        fwrite(buf, 1, (size_t)n, g_log);
        if (n == 0 || buf[n - 1] != '\n') fputc('\n', g_log);
        fflush(g_log);
    }
    LeaveCriticalSection(&g_cs);
}

static int __cdecl LogHook(const char* fmt, ...) {
    if (!ProbeCStr(fmt)) return 0;                          // not a logging call -> no-op
    if (!LooksLikeMessage(fmt)) return 0;                   // printable garbage ("p/]") -> drop

    char buf[4096];
    int  n;
    if (strchr(fmt, '%') == nullptr) {
        // plain message (typical script print) — copy verbatim, never parse as
        // a format (script text may legitimately contain '%').
        n = (int)strlen(fmt);
        if (n > (int)sizeof(buf) - 2) n = (int)sizeof(buf) - 2;
        memcpy(buf, fmt, (size_t)n);
        buf[n] = 0;
    } else {
        va_list ap;
        va_start(ap, fmt);
        n = SafeVsnprintf(buf, sizeof(buf) - 2, fmt, ap);
        va_end(ap);
        if (n < 0 || n > (int)sizeof(buf) - 2) { buf[sizeof(buf) - 2] = 0; n = (int)strlen(buf); }
    }
    Emit(buf, n);
    return 0;
}

static void InstallHook() {
    uintptr_t base   = (uintptr_t)GetModuleHandleA(NULL);   // Game.exe
    BYTE*     target = (BYTE*)(base + LOGGER_RVA);

    // Only patch if we see the exact stub, so we never corrupt a wrong binary.
    if (!(target[0] == 0x33 && target[1] == 0xC0 && target[2] == 0xC3)) {
        char m[160];
        _snprintf(m, sizeof m,
                  "[tfbhook] unexpected bytes at %p (%02X %02X %02X); not this Game.exe? aborting\n",
                  (void*)target, target[0], target[1], target[2]);
        OutputDebugStringA(m);
        return;
    }
    DWORD old;
    VirtualProtect(target, 6, PAGE_EXECUTE_READWRITE, &old);
    target[0] = 0x68;                                        // push imm32
    *(uint32_t*)(target + 1) = (uint32_t)(uintptr_t)&LogHook;
    target[5] = 0xC3;                                        // ret
    VirtualProtect(target, 6, old, &old);
    FlushInstructionCache(GetCurrentProcess(), target, 6);
    OutputDebugStringA("[tfbhook] Game.exe logger re-enabled (+0x3e6f0)\n");
}

// ---------------------------------------------------------------------------
// Transparent d3d8.dll forwarding
// ---------------------------------------------------------------------------
// d3d8.dll exports exactly these four. We resolve them from the real system
// DLL and jump to them with naked thunks, so signatures/arg counts don't matter.
static FARPROC g_Direct3DCreate8       = nullptr;
static FARPROC g_ValidatePixelShader   = nullptr;
static FARPROC g_ValidateVertexShader  = nullptr;
static FARPROC g_DebugSetMute          = nullptr;

static __declspec(naked) void SafeRet()  { __asm { ret } }   // fallback if unresolved

static void LoadRealD3D8() {
    char path[MAX_PATH];
    UINT n = GetSystemDirectoryA(path, MAX_PATH);
    strcpy_s(path + n, MAX_PATH - n, "\\d3d8.dll");
    HMODULE real = LoadLibraryA(path);
    if (!real) { OutputDebugStringA("[tfbhook] FATAL: cannot load real d3d8.dll\n"); return; }

    g_Direct3DCreate8      = GetProcAddress(real, "Direct3DCreate8");
    g_ValidatePixelShader  = GetProcAddress(real, "ValidatePixelShader");
    g_ValidateVertexShader = GetProcAddress(real, "ValidateVertexShader");
    g_DebugSetMute         = GetProcAddress(real, "DebugSetMute");

    FARPROC fb = (FARPROC)&SafeRet;
    if (!g_Direct3DCreate8)      g_Direct3DCreate8      = fb;
    if (!g_ValidatePixelShader)  g_ValidatePixelShader  = fb;
    if (!g_ValidateVertexShader) g_ValidateVertexShader = fb;
    if (!g_DebugSetMute)         g_DebugSetMute         = fb;
}

// Exported by name via d3d8.def -> these thunks. Naked jmp preserves the exact
// caller frame regardless of the real function's signature/stdcall cleanup.
extern "C" __declspec(naked) void Fwd_Direct3DCreate8()      { __asm { jmp g_Direct3DCreate8 } }
extern "C" __declspec(naked) void Fwd_ValidatePixelShader()  { __asm { jmp g_ValidatePixelShader } }
extern "C" __declspec(naked) void Fwd_ValidateVertexShader() { __asm { jmp g_ValidateVertexShader } }
extern "C" __declspec(naked) void Fwd_DebugSetMute()         { __asm { jmp g_DebugSetMute } }

// ---------------------------------------------------------------------------
BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(h);
        InitializeCriticalSection(&g_cs);
        LoadRealD3D8();                       // resolve forwards BEFORE the game uses d3d8
        g_log = fopen("Game_prints.log", "w");
        InstallHook();
    } else if (reason == DLL_PROCESS_DETACH) {
        if (g_log) { fclose(g_log); g_log = nullptr; }
    }
    return TRUE;
}
