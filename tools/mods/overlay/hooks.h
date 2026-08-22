#pragma once

// Patches IDirect3D8::CreateDevice on the given interface so we can catch the
// resulting IDirect3DDevice8 and hook EndScene/Reset on it in turn.
void InstallD3D8Hooks(void* pDirect3D8);
