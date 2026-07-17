#include "d3d8_min.h"
#include "hooks.h"
#include "overlay.h"

static CreateDevice_t oCreateDevice = nullptr;
static EndScene_t     oEndScene = nullptr;
static Reset_t        oReset = nullptr;
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
    Overlay_Render(This);
    return oEndScene(This);
}

static HRESULT STDMETHODCALLTYPE Hook_Reset(void* This, D3DPRESENT_PARAMETERS* pp) {
    Overlay_OnLostDevice();
    HRESULT hr = oReset(This, pp);
    Overlay_OnResetDevice();
    return hr;
}

static HRESULT STDMETHODCALLTYPE Hook_CreateDevice(
    void* This, UINT Adapter, D3DDEVTYPE DeviceType, HWND hFocusWindow,
    DWORD BehaviorFlags, D3DPRESENT_PARAMETERS* pp, void** ppReturnedDeviceInterface)
{
    HRESULT hr = oCreateDevice(This, Adapter, DeviceType, hFocusWindow, BehaviorFlags, pp, ppReturnedDeviceInterface);

    if (SUCCEEDED(hr) && ppReturnedDeviceInterface && *ppReturnedDeviceInterface) {
        void* pDevice = *ppReturnedDeviceInterface;
        HWND hwnd = hFocusWindow ? hFocusWindow : pp->hDeviceWindow;

        // The vtable is per-class, not per-instance, so patching once covers
        // every device the game creates afterwards too.
        if (!g_deviceHooksInstalled) {
            PatchVTableSlot(pDevice, IDIRECT3DDEVICE8_ENDSCENE, (void*)Hook_EndScene, (void**)&oEndScene);
            PatchVTableSlot(pDevice, IDIRECT3DDEVICE8_RESET, (void*)Hook_Reset, (void**)&oReset);
            g_deviceHooksInstalled = true;
        }

        Overlay_Init(pDevice, hwnd);
    }

    return hr;
}

void InstallD3D8Hooks(void* pDirect3D8) {
    PatchVTableSlot(pDirect3D8, IDIRECT3D8_CREATEDEVICE, (void*)Hook_CreateDevice, (void**)&oCreateDevice);
}
