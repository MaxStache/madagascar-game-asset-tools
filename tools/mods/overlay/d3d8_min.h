#pragma once
// Minimal Direct3D 8 declarations: just enough to hook CreateDevice/EndScene/Reset
// and drive a real Dear ImGui D3D8 backend (imgui_impl_dx8.cpp). Not a full
// d3d8.h replacement -- modern Windows SDKs don't ship the legacy D3D8
// headers, so this avoids depending on the old DirectX SDK being installed.
//
// Every vtable slot index and enum value below was cross-checked against
// Wine's d3d8.h/d3d8types.h (an ABI-exact reimplementation -- real D3D8
// games would crash on Wine if these were wrong, so it's an authoritative
// reference), not reconstructed from memory. We hook/call by numeric vtable
// index rather than declaring the full ~95-method interfaces, so a mistake
// in an unused method's exact signature can't affect layout -- only the
// specific slots actually touched need to be correct, and all of those are
// now verified.

#include <windows.h>

typedef DWORD D3DFORMAT;
typedef DWORD D3DDEVTYPE;
typedef DWORD D3DMULTISAMPLE_TYPE;
typedef DWORD D3DSWAPEFFECT;
typedef DWORD D3DPRIMITIVETYPE;
typedef DWORD D3DRENDERSTATETYPE;
typedef DWORD D3DTEXTURESTAGESTATETYPE;
typedef DWORD D3DTRANSFORMSTATETYPE;
typedef DWORD D3DPOOL;
typedef DWORD D3DSTATEBLOCKTYPE;
typedef DWORD D3DCOLOR;

#define D3DADAPTER_DEFAULT                     0
#define D3DDEVTYPE_HAL                          1
#define D3DCREATE_SOFTWARE_VERTEXPROCESSING     0x00000020L
#define D3DCREATE_HARDWARE_VERTEXPROCESSING     0x00000040L
#define D3DFMT_UNKNOWN                          0
#define D3DFMT_A8R8G8B8                         21
#define D3DFMT_INDEX16                          101
#define D3DSWAPEFFECT_DISCARD                   1
#define D3DMULTISAMPLE_NONE                     0

#define D3DFVF_XYZ                              0x0002
#define D3DFVF_XYZRHW                           0x0004
#define D3DFVF_DIFFUSE                          0x0040
#define D3DFVF_TEX1                             0x0100

#define D3DPT_TRIANGLELIST                      4

#define D3DPOOL_DEFAULT                         0

#define D3DUSAGE_WRITEONLY                      0x00000008
#define D3DUSAGE_DYNAMIC                        0x00000200
#define D3DUSAGE_RENDERTARGET                   0x00000001
#define D3DUSAGE_DEPTHSTENCIL                   0x00000002

#define D3DRTYPE_SURFACE                        1

#define D3DLOCK_DISCARD                         0x00002000

#define D3DSBT_ALL                              1

#define D3DTS_VIEW                              2
#define D3DTS_PROJECTION                        3
#define D3DTS_WORLD                             256 // D3DTS_WORLDMATRIX(0) = 0+256

#define D3DRS_ZENABLE                           7
#define D3DRS_FILLMODE                          8
#define D3DRS_SHADEMODE                         9
#define D3DRS_ZWRITEENABLE                      14
#define D3DRS_ALPHATESTENABLE                   15
#define D3DRS_SRCBLEND                          19
#define D3DRS_DESTBLEND                         20
#define D3DRS_CULLMODE                          22
#define D3DRS_ALPHABLENDENABLE                  27
#define D3DRS_FOGENABLE                         28
#define D3DRS_SPECULARENABLE                    29
#define D3DRS_RANGEFOGENABLE                    48
#define D3DRS_STENCILENABLE                     52
#define D3DRS_CLIPPING                          136
#define D3DRS_LIGHTING                          137
#define D3DRS_BLENDOP                           171
// D3DRS_SCISSORTESTENABLE / D3DRS_SEPARATEALPHABLENDENABLE / D3DRS_SRCBLENDALPHA /
// D3DRS_DESTBLENDALPHA do NOT exist in D3D8 (confirmed absent from Wine's d3d8types.h
// D3DRENDERSTATETYPE enum) -- they're D3D9 additions. No scissor/clip-rect support here.

#define D3DTSS_COLOROP                          1
#define D3DTSS_COLORARG1                        2
#define D3DTSS_COLORARG2                        3
#define D3DTSS_ALPHAOP                          4
#define D3DTSS_ALPHAARG1                        5
#define D3DTSS_ALPHAARG2                        6
#define D3DTSS_ADDRESSU                         13
#define D3DTSS_ADDRESSV                         14
#define D3DTSS_MAGFILTER                        16
#define D3DTSS_MINFILTER                        17

#define D3DTOP_DISABLE                          1
#define D3DTOP_MODULATE                         4

#define D3DTA_DIFFUSE                           0x00000000
#define D3DTA_TEXTURE                           0x00000002

#define D3DTADDRESS_WRAP                        1
#define D3DTADDRESS_CLAMP                       3

#define D3DTEXF_NONE                            0
#define D3DTEXF_POINT                           1
#define D3DTEXF_LINEAR                          2

#define D3DBLEND_SRCALPHA                       5
#define D3DBLEND_INVSRCALPHA                    6
#define D3DBLENDOP_ADD                          1

#define D3DCULL_NONE                            1

typedef struct _D3DPRESENT_PARAMETERS_ {
    UINT                BackBufferWidth;
    UINT                BackBufferHeight;
    D3DFORMAT           BackBufferFormat;
    UINT                BackBufferCount;
    D3DMULTISAMPLE_TYPE MultiSampleType;
    D3DSWAPEFFECT       SwapEffect;
    HWND                hDeviceWindow;
    BOOL                Windowed;
    BOOL                EnableAutoDepthStencil;
    D3DFORMAT           AutoDepthStencilFormat;
    DWORD               Flags;
    UINT                FullScreen_RefreshRateInHz;
    UINT                FullScreen_PresentationInterval;
} D3DPRESENT_PARAMETERS;

typedef struct _D3DVIEWPORT8 {
    DWORD X, Y, Width, Height;
    float MinZ, MaxZ;
} D3DVIEWPORT8;

typedef struct _D3DLOCKED_RECT {
    INT   Pitch;
    void* pBits;
} D3DLOCKED_RECT;

typedef struct _D3DMATRIX {
    float m[4][4];
} D3DMATRIX;

typedef struct _D3DDISPLAYMODE {
    UINT      Width;
    UINT      Height;
    UINT      RefreshRate;
    D3DFORMAT Format;
} D3DDISPLAYMODE;

// 0-based vtable slot indices (IUnknown's QueryInterface/AddRef/Release occupy 0/1/2
// on every COM interface, including all D3D8 resource types below).
enum D3D8_VTBL {
    IUNKNOWN_ADDREF                     = 1,
    IUNKNOWN_RELEASE                    = 2,

    IDIRECT3D8_GETADAPTERDISPLAYMODE    = 8,
    IDIRECT3D8_CHECKDEVICETYPE          = 9,
    IDIRECT3D8_CHECKDEVICEFORMAT        = 10,
    IDIRECT3D8_CHECKDEVICEMULTISAMPLETYPE = 11,
    IDIRECT3D8_CHECKDEPTHSTENCILMATCH   = 12,
    IDIRECT3D8_CREATEDEVICE             = 15,

    IDIRECT3DDEVICE8_RESET              = 14,
    IDIRECT3DDEVICE8_PRESENT            = 15,
    IDIRECT3DDEVICE8_CREATETEXTURE      = 20,
    IDIRECT3DDEVICE8_CREATEVERTEXBUFFER = 23,
    IDIRECT3DDEVICE8_CREATEINDEXBUFFER  = 24,
    IDIRECT3DDEVICE8_BEGINSCENE         = 34,
    IDIRECT3DDEVICE8_ENDSCENE           = 35,
    IDIRECT3DDEVICE8_SETTRANSFORM       = 37,
    IDIRECT3DDEVICE8_GETTRANSFORM       = 38,
    IDIRECT3DDEVICE8_SETVIEWPORT        = 40,
    IDIRECT3DDEVICE8_SETRENDERSTATE     = 50,
    IDIRECT3DDEVICE8_GETRENDERSTATE     = 51,
    IDIRECT3DDEVICE8_APPLYSTATEBLOCK    = 54,
    IDIRECT3DDEVICE8_DELETESTATEBLOCK   = 56,
    IDIRECT3DDEVICE8_CREATESTATEBLOCK   = 57,
    IDIRECT3DDEVICE8_GETTEXTURE         = 60,
    IDIRECT3DDEVICE8_SETTEXTURE         = 61,
    IDIRECT3DDEVICE8_SETTEXTURESTAGESTATE = 63,
    IDIRECT3DDEVICE8_DRAWINDEXEDPRIMITIVE = 71,
    IDIRECT3DDEVICE8_DRAWPRIMITIVEUP    = 72,
    IDIRECT3DDEVICE8_SETVERTEXSHADER    = 76,
    IDIRECT3DDEVICE8_GETVERTEXSHADER    = 77,
    IDIRECT3DDEVICE8_SETSTREAMSOURCE    = 83,
    IDIRECT3DDEVICE8_SETINDICES         = 85,
    IDIRECT3DDEVICE8_SETPIXELSHADER     = 88,

    // IDirect3DResource8-derived (VertexBuffer8/IndexBuffer8): Lock=11, Unlock=12
    IDIRECT3DBUFFER8_LOCK               = 11,
    IDIRECT3DBUFFER8_UNLOCK             = 12,

    // IDirect3DTexture8: LockRect=16, UnlockRect=17
    IDIRECT3DTEXTURE8_LOCKRECT          = 16,
    IDIRECT3DTEXTURE8_UNLOCKRECT        = 17,
};

typedef HRESULT(STDMETHODCALLTYPE* GetAdapterDisplayMode_t)(void* This, UINT Adapter, D3DDISPLAYMODE* pMode);
typedef HRESULT(STDMETHODCALLTYPE* CheckDeviceType_t)(
    void* This, UINT Adapter, D3DDEVTYPE CheckType, D3DFORMAT DisplayFormat, D3DFORMAT BackBufferFormat, BOOL Windowed);
typedef HRESULT(STDMETHODCALLTYPE* CheckDeviceFormat_t)(
    void* This, UINT Adapter, D3DDEVTYPE DeviceType, D3DFORMAT AdapterFormat, DWORD Usage, DWORD RType, D3DFORMAT CheckFormat);
typedef HRESULT(STDMETHODCALLTYPE* CheckDeviceMultiSampleType_t)(
    void* This, UINT Adapter, D3DDEVTYPE DeviceType, D3DFORMAT SurfaceFormat, BOOL Windowed, D3DMULTISAMPLE_TYPE MultiSampleType);
typedef HRESULT(STDMETHODCALLTYPE* CheckDepthStencilMatch_t)(
    void* This, UINT Adapter, D3DDEVTYPE DeviceType, D3DFORMAT AdapterFormat, D3DFORMAT RenderTargetFormat, D3DFORMAT DepthStencilFormat);

typedef HRESULT(STDMETHODCALLTYPE* CreateDevice_t)(
    void* This, UINT Adapter, D3DDEVTYPE DeviceType, HWND hFocusWindow,
    DWORD BehaviorFlags, D3DPRESENT_PARAMETERS* pPresentationParameters,
    void** ppReturnedDeviceInterface);

typedef HRESULT(STDMETHODCALLTYPE* Reset_t)(void* This, D3DPRESENT_PARAMETERS* pPresentationParameters);
typedef HRESULT(STDMETHODCALLTYPE* EndScene_t)(void* This);
typedef HRESULT(STDMETHODCALLTYPE* SetRenderState_t)(void* This, D3DRENDERSTATETYPE State, DWORD Value);
typedef HRESULT(STDMETHODCALLTYPE* GetRenderState_t)(void* This, D3DRENDERSTATETYPE State, DWORD* pValue);
typedef HRESULT(STDMETHODCALLTYPE* SetTexture_t)(void* This, DWORD Stage, void* pTexture);
typedef HRESULT(STDMETHODCALLTYPE* GetTexture_t)(void* This, DWORD Stage, void** ppTexture);
typedef HRESULT(STDMETHODCALLTYPE* SetVertexShader_t)(void* This, DWORD Handle);
typedef HRESULT(STDMETHODCALLTYPE* GetVertexShader_t)(void* This, DWORD* pHandle);
typedef HRESULT(STDMETHODCALLTYPE* DrawPrimitiveUP_t)(
    void* This, D3DPRIMITIVETYPE PrimitiveType, UINT PrimitiveCount,
    const void* pVertexStreamZeroData, UINT VertexStreamZeroStride);
typedef ULONG(STDMETHODCALLTYPE* Release_t)(void* This);
typedef ULONG(STDMETHODCALLTYPE* AddRef_t)(void* This);

typedef HRESULT(STDMETHODCALLTYPE* CreateTexture_t)(
    void* This, UINT Width, UINT Height, UINT Levels, DWORD Usage,
    D3DFORMAT Format, D3DPOOL Pool, void** ppTexture);
typedef HRESULT(STDMETHODCALLTYPE* CreateVertexBuffer_t)(
    void* This, UINT Length, DWORD Usage, DWORD FVF, D3DPOOL Pool, void** ppVertexBuffer);
typedef HRESULT(STDMETHODCALLTYPE* CreateIndexBuffer_t)(
    void* This, UINT Length, DWORD Usage, D3DFORMAT Format, D3DPOOL Pool, void** ppIndexBuffer);
typedef HRESULT(STDMETHODCALLTYPE* SetTransform_t)(void* This, D3DTRANSFORMSTATETYPE State, const D3DMATRIX* pMatrix);
typedef HRESULT(STDMETHODCALLTYPE* GetTransform_t)(void* This, D3DTRANSFORMSTATETYPE State, D3DMATRIX* pMatrix);
typedef HRESULT(STDMETHODCALLTYPE* SetViewport_t)(void* This, const D3DVIEWPORT8* pViewport);
typedef HRESULT(STDMETHODCALLTYPE* CreateStateBlock_t)(void* This, D3DSTATEBLOCKTYPE Type, DWORD* pToken);
typedef HRESULT(STDMETHODCALLTYPE* ApplyStateBlock_t)(void* This, DWORD Token);
typedef HRESULT(STDMETHODCALLTYPE* DeleteStateBlock_t)(void* This, DWORD Token);
typedef HRESULT(STDMETHODCALLTYPE* SetTextureStageState_t)(void* This, DWORD Stage, D3DTEXTURESTAGESTATETYPE Type, DWORD Value);
typedef HRESULT(STDMETHODCALLTYPE* DrawIndexedPrimitive_t)(
    void* This, D3DPRIMITIVETYPE PrimitiveType, UINT MinIndex, UINT NumVertices, UINT StartIndex, UINT PrimCount);
typedef HRESULT(STDMETHODCALLTYPE* SetStreamSource_t)(void* This, UINT StreamNumber, void* pStreamData, UINT Stride);
typedef HRESULT(STDMETHODCALLTYPE* SetIndices_t)(void* This, void* pIndexData, UINT BaseVertexIndex);
typedef HRESULT(STDMETHODCALLTYPE* SetPixelShader_t)(void* This, DWORD Handle);
typedef HRESULT(STDMETHODCALLTYPE* BufferLock_t)(void* This, UINT OffsetToLock, UINT SizeToLock, BYTE** ppbData, DWORD Flags);
typedef HRESULT(STDMETHODCALLTYPE* BufferUnlock_t)(void* This);
typedef HRESULT(STDMETHODCALLTYPE* LockRect_t)(void* This, UINT Level, D3DLOCKED_RECT* pLockedRect, const RECT* pRect, DWORD Flags);
typedef HRESULT(STDMETHODCALLTYPE* UnlockRect_t)(void* This, UINT Level);

typedef void* (WINAPI* Direct3DCreate8_t)(UINT SDKVersion);

// Fetch a callable function pointer for vtable slot `IndexEnum` on `pInterface`,
// typed as `TypedefName`. Keeps call sites free of manual casting/indexing.
#define D3D8_VTBL_FN(pInterface, TypedefName, IndexEnum) \
    reinterpret_cast<TypedefName>((*reinterpret_cast<void***>(pInterface))[IndexEnum])
