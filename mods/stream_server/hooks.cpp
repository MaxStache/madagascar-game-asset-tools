#include "d3d8_min.h"
#include "hooks.h"
#include "stream_inject.h"

static CreateDevice_t oCreateDevice = nullptr;
static EndScene_t     oEndScene = nullptr;
static bool           g_deviceHooksInstalled = false;

static void PatchVTableSlot(void* pInterface, int index, void* pNewFunc, void** ppOldFunc) {
    void** vtable = *reinterpret_cast<void***>(pInterface);
    DWORD oldProtect;
    VirtualProtect(&vtable[index], sizeof(void*), PAGE_EXECUTE_READWRITE, &oldProtect);
    if (ppOldFunc) *ppOldFunc = vtable[index];
    vtable[index] = pNewFunc;
    VirtualProtect(&vtable[index], sizeof(void*), oldProtect, &oldProtect);
}

static HRESULT STDMETHODCALLTYPE Hook_EndScene(void* This) {
    // Only safe point to touch the game's resource manager: see
    // stream_inject.h for why this can't run on the HTTP server's thread.
    StreamInject_Pump();
    return oEndScene(This);
}

static HRESULT STDMETHODCALLTYPE Hook_CreateDevice(
    void* This, UINT Adapter, DWORD DeviceType, HWND hFocusWindow,
    DWORD BehaviorFlags, void* pPresentationParameters, void** ppReturnedDeviceInterface)
{
    HRESULT hr = oCreateDevice(This, Adapter, DeviceType, hFocusWindow, BehaviorFlags,
        pPresentationParameters, ppReturnedDeviceInterface);

    if (SUCCEEDED(hr) && ppReturnedDeviceInterface && *ppReturnedDeviceInterface) {
        // The vtable is per-class, not per-instance, so patching once covers
        // every device the game creates afterwards too.
        if (!g_deviceHooksInstalled) {
            PatchVTableSlot(*ppReturnedDeviceInterface, IDIRECT3DDEVICE8_ENDSCENE, (void*)Hook_EndScene, (void**)&oEndScene);
            g_deviceHooksInstalled = true;
        }
    }

    return hr;
}

void InstallD3D8Hooks(void* pDirect3D8) {
    PatchVTableSlot(pDirect3D8, IDIRECT3D8_CREATEDEVICE, (void*)Hook_CreateDevice, (void**)&oCreateDevice);
}
