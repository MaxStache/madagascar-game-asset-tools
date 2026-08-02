#pragma once
#include <windows.h>

// Called once, right after the game's D3D8 device is created.
void Overlay_Init(void* pDevice, HWND hWnd);

// Called every frame, just before the real EndScene runs.
void Overlay_Render(void* pDevice);

// Called around a device Reset() (e.g. alt-tab in fullscreen, resolution change).
void Overlay_OnLostDevice();
void Overlay_OnResetDevice();
