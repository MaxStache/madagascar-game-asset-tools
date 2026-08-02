#pragma once

// Patches IDirect3D8::CreateDevice on the given interface so we can catch
// the resulting IDirect3DDevice8 and hook EndScene on it in turn -- our
// only use for that hook is a reliable once-per-frame callback on the
// game's main thread (see stream_inject.h).
void InstallD3D8Hooks(void* pDirect3D8);
