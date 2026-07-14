// tfb_printhook — re-enables Madagascar (Game.exe) logging.
//
// Every engine log AND every script `print::op-code` funnels through one
// variadic logger that the retail build stubbed out to `return 0`:
//
//     0043e6f0   33 C0   xor eax, eax
//     0043e6f2   C3      ret          ; int __cdecl log(const char* fmt, ...)
//
// We overwrite its entry with `push &LogHook ; ret`, so every call lands in
// our implementation instead. The stub takes no registers (cdecl, all args on
// the stack), so jumping in with the identical frame is safe, and push/ret is
// position-independent (no rel32 range worries) and clobbers no registers.
//
// Output goes to OutputDebugStringA (watch with Sysinternals DebugView) and to
// Game_prints.log in the working directory.
//
// Build: 32-bit DLL, static CRT. See build.bat. Rename output to .asi and load
// with Ultimate ASI Loader (see README.md).

#include <windows.h>
#include <cstdio>
#include <cstdarg>
#include <cstring>
#include <cstdint>

// VA 0x0043e6f0 - preferred image base 0x00400000
static const uintptr_t LOGGER_RVA = 0x3e6f0;

static FILE*            g_log = nullptr;
static CRITICAL_SECTION g_cs;

// Replacement for the stubbed logger. Same signature & calling convention.
static int __cdecl LogHook(const char* fmt, ...) {
    if (!fmt) return 0;
    char buf[4096];
    va_list ap;
    va_start(ap, fmt);
    int n = _vsnprintf(buf, sizeof(buf) - 2, fmt, ap);
    va_end(ap);
    if (n < 0 || n > (int)sizeof(buf) - 2) { buf[sizeof(buf) - 2] = 0; n = (int)strlen(buf); }

    EnterCriticalSection(&g_cs);
    OutputDebugStringA(buf);
    if (g_log) {
        fwrite(buf, 1, (size_t)n, g_log);
        if (n == 0 || buf[n - 1] != '\n') fputc('\n', g_log);
        fflush(g_log);
    }
    LeaveCriticalSection(&g_cs);
    return 0;
}

static void InstallHook() {
    uintptr_t base   = (uintptr_t)GetModuleHandleA(NULL); // Game.exe base
    BYTE*     target = (BYTE*)(base + LOGGER_RVA);

    // Verify we're patching the expected stub (xor eax,eax; ret) so we never
    // corrupt a different build/binary by accident.
    if (!(target[0] == 0x33 && target[1] == 0xC0 && target[2] == 0xC3)) {
        char m[160];
        _snprintf(m, sizeof m,
                  "[tfbhook] unexpected bytes at %p (%02X %02X %02X); not Game.exe? aborting\n",
                  (void*)target, target[0], target[1], target[2]);
        OutputDebugStringA(m);
        return;
    }

    DWORD old;
    VirtualProtect(target, 6, PAGE_EXECUTE_READWRITE, &old);
    target[0] = 0x68;                                     // push imm32
    *(uint32_t*)(target + 1) = (uint32_t)(uintptr_t)&LogHook;
    target[5] = 0xC3;                                     // ret
    VirtualProtect(target, 6, old, &old);
    FlushInstructionCache(GetCurrentProcess(), target, 6);

    OutputDebugStringA("[tfbhook] Game.exe logger re-enabled (+0x3e6f0)\n");
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(h);
        InitializeCriticalSection(&g_cs);
        g_log = fopen("Game_prints.log", "w");
        InstallHook();
    } else if (reason == DLL_PROCESS_DETACH) {
        if (g_log) { fclose(g_log); g_log = nullptr; }
    }
    return TRUE;
}
