// Renderer Backend for DirectX8, based on the official DirectX9 Backend from Dear ImGui
// This needs to be used along with a Platform Backend (e.g. Win32)

#pragma once
#include <imgui.h>      // IMGUI_IMPL_API

struct IDirect3DDevice8;

IMGUI_IMPL_API bool     ImGui_ImplDX8_Init(IDirect3DDevice8* device);
IMGUI_IMPL_API void     ImGui_ImplDX8_Shutdown();
IMGUI_IMPL_API void     ImGui_ImplDX8_NewFrame();
IMGUI_IMPL_API void     ImGui_ImplDX8_RenderDrawData(ImDrawData* draw_data);

// Use if you want to reset your rendering device without losing Dear ImGui state.
IMGUI_IMPL_API bool     ImGui_ImplDX8_CreateDeviceObjects();
IMGUI_IMPL_API void     ImGui_ImplDX8_InvalidateDeviceObjects();

// Real back-buffer size (what SetupRenderState's viewport/projection actually
// use -- see the comment there). Tools that intercept CreateDevice/Reset to
// force their own resolution/aspect ratio (e.g. DXWnd) can make this differ
// from the window's client rect; callers should reconcile io.DisplaySize and
// io.MousePos against this every frame if so. Writes 0,0 if unavailable.
IMGUI_IMPL_API void     ImGui_ImplDX8_GetBackBufferSize(float* width, float* height);