#include "d3d8_min.h"
#include "hooks.h"

static HMODULE g_hRealD3D8 = nullptr;
static Direct3DCreate8_t g_RealCreate = nullptr;

static bool LoadRealD3D8() {
    if (g_hRealD3D8) return true;

    // The real system d3d8.dll -- loaded by absolute path so our same-named
    // proxy sitting next to Game.exe doesn't recursively load itself. Works
    // for a 32-bit process on 64-bit Windows too: WOW64 file-system
    // redirection transparently maps this System32 path to SysWOW64.
    char sysDir[MAX_PATH];
    GetSystemDirectoryA(sysDir, MAX_PATH);
    char path[MAX_PATH];
    wsprintfA(path, "%s\\d3d8.dll", sysDir);

    g_hRealD3D8 = LoadLibraryA(path);
    if (!g_hRealD3D8) return false;

    g_RealCreate = reinterpret_cast<Direct3DCreate8_t>(GetProcAddress(g_hRealD3D8, "Direct3DCreate8"));
    return g_RealCreate != nullptr;
}

extern "C" __declspec(dllexport) void* WINAPI Direct3DCreate8(UINT SDKVersion) {
    if (!LoadRealD3D8()) return nullptr;

    void* pD3D8 = g_RealCreate(SDKVersion);
    if (pD3D8) InstallD3D8Hooks(pD3D8);
    return pD3D8;
}

BOOL WINAPI DllMain(HMODULE hModule, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hModule);

        // Game.exe statically imports Direct3DCreate8, so this proxy DLL is
        // loaded by the Windows loader before the game's own entry point runs
        // -- early enough that declaring DPI awareness here still takes
        // effect. Without this, an old DPI-unaware game gets bitmap-stretched
        // by Windows on any display running above 100% scaling, which shows
        // up as the whole window (game and overlay alike) looking blurry/
        // pixelated rather than rendering at native resolution.
        SetProcessDPIAware();
    } else if (reason == DLL_PROCESS_DETACH) {
        if (g_hRealD3D8) FreeLibrary(g_hRealD3D8);
    }
    return TRUE;
}
