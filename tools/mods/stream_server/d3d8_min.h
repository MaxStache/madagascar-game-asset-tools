#pragma once
// Just enough Direct3D 8 to proxy Direct3DCreate8 and hook
// IDirect3D8::CreateDevice -> IDirect3DDevice8::EndScene for a safe,
// once-per-frame callback on the game's main thread. Not a real d3d8.h --
// modern Windows SDKs don't ship the legacy DirectX 8 headers, and this
// tool never touches D3D state, so an opaque `void*` for
// D3DPRESENT_PARAMETERS is enough; we never dereference it.
//
// Vtable slot indices cross-checked against Wine's d3d8.h (an ABI-exact
// reimplementation -- real D3D8 games would crash on Wine if these were
// wrong, so it's an authoritative reference).

#include <windows.h>

enum D3D8_VTBL {
    IDIRECT3D8_CREATEDEVICE   = 15,
    IDIRECT3DDEVICE8_ENDSCENE = 35,
};

typedef void* (WINAPI* Direct3DCreate8_t)(UINT SDKVersion);

typedef HRESULT(STDMETHODCALLTYPE* CreateDevice_t)(
    void* This, UINT Adapter, DWORD DeviceType, HWND hFocusWindow,
    DWORD BehaviorFlags, void* pPresentationParameters,
    void** ppReturnedDeviceInterface);

typedef HRESULT(STDMETHODCALLTYPE* EndScene_t)(void* This);
