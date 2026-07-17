#include <cfloat>
#include <windowsx.h> // GET_X_LPARAM, GET_Y_LPARAM

#include "d3d8_min.h"
#include "overlay.h"

#include "imgui/imgui.h"
#include "imgui/imgui_impl_win32.h"
#include "imgui/imgui_impl_dx8.h"
#include "player_position.h"

// Per imgui_impl_win32.h's instructions: this is declared but not exported
// from the header (to avoid dragging <windows.h> into it), so we forward
// declare it ourselves.
extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);

static HWND    g_hWnd = nullptr;
static WNDPROC g_originalWndProc = nullptr;
static bool    g_imguiReady = false;
static bool    g_visible = true;
static bool    g_insertWasDown = false;
static int     g_cursorForceCount = 0; // net extra ShowCursor(TRUE) calls we've applied

// Win32's cursor visibility is a display counter, not a bool: ShowCursor(TRUE)
// increments it, ShowCursor(FALSE) decrements it, and the cursor only renders
// while the counter is >= 0. Most games hide the cursor by calling
// ShowCursor(FALSE) once per frame, so a single counter call here every frame
// isn't enough to win the fight -- we drive the counter up until it's
// non-negative, and undo exactly that many increments once the overlay is
// hidden again so we don't leave the game's own cursor state altered.
static void Overlay_ForceCursorVisible(bool visible) {
    if (visible) {
        // do/while, not while: the call that finally satisfies the exit
        // condition (brings the counter to >= 0) still happens and still
        // increments the real Windows counter -- it must be counted too, or
        // g_cursorForceCount silently falls behind the real counter every
        // steady-state frame (see the comment above this function) and we
        // can never fully give back what we took.
        int result;
        do {
            result = ::ShowCursor(TRUE);
            g_cursorForceCount++;
        } while (result < 0);
    } else {
        while (g_cursorForceCount > 0) {
            ::ShowCursor(FALSE);
            g_cursorForceCount--;
        }
    }
}

// Cursor *confinement* is separate from cursor *visibility* above. Many
// games call ClipCursor once to lock the mouse to the window so it can't
// wander onto another monitor; we never touched that, so once you'd moved
// the mouse for ImGui it stayed free even after hiding the overlay again.
// Release the clip while the overlay's up (ImGui needs free movement) and
// re-lock it to the window's bounds once it's hidden, restoring what a
// game with this behavior would normally have.
static void Overlay_ApplyCursorLock(bool visible, HWND hWnd) {
    if (visible) {
        ::ClipCursor(nullptr);
        return;
    }
    RECT rect;
    if (!::GetClientRect(hWnd, &rect))
        return;
    POINT topLeft{ rect.left, rect.top };
    POINT bottomRight{ rect.right, rect.bottom };
    ::ClientToScreen(hWnd, &topLeft);
    ::ClientToScreen(hWnd, &bottomRight);
    RECT screenRect{ topLeft.x, topLeft.y, bottomRight.x, bottomRight.y };
    ::ClipCursor(&screenRect);
}

// True for the messages that carry a client-rect (x,y) position in lParam's
// low/high words (LOWORD/HIWORD via GET_X_LPARAM/GET_Y_LPARAM) -- everything
// except WM_MOUSEWHEEL/WM_MOUSEHWHEEL, which carry *screen* coordinates
// instead (the Win32 backend converts those itself; rescaling here would be
// wrong for them, and they don't need positional accuracy anyway).
static bool IsClientCoordMouseMsg(UINT msg) {
    switch (msg) {
    case WM_MOUSEMOVE:
    case WM_LBUTTONDOWN: case WM_LBUTTONUP: case WM_LBUTTONDBLCLK:
    case WM_RBUTTONDOWN: case WM_RBUTTONUP: case WM_RBUTTONDBLCLK:
    case WM_MBUTTONDOWN: case WM_MBUTTONUP: case WM_MBUTTONDBLCLK:
    case WM_XBUTTONDOWN: case WM_XBUTTONUP: case WM_XBUTTONDBLCLK:
        return true;
    default:
        return false;
    }
}

// Rescale a client-coordinate mouse message's position into D3D8 back-buffer
// space before ImGui ever sees it. Doing this here -- rather than patching
// io.MousePos after ImGui_ImplWin32_NewFrame() -- matters because modern
// ImGui doesn't set io.MousePos synchronously in NewFrame(); Win32's message
// handler queues it as an event (io.AddMousePosEvent) that gets applied
// *inside* ImGui::NewFrame(). Patching io.MousePos in between raced against
// that queued event and produced a visible jump every other frame. Adjusting
// the message itself avoids the race entirely: there's only one write.
static LPARAM RescaleMouseLParam(HWND hWnd, LPARAM lParam) {
    float bbWidth = 0.0f, bbHeight = 0.0f;
    ImGui_ImplDX8_GetBackBufferSize(&bbWidth, &bbHeight);

    RECT clientRect;
    GetClientRect(hWnd, &clientRect);
    float clientWidth = (float)(clientRect.right - clientRect.left);
    float clientHeight = (float)(clientRect.bottom - clientRect.top);

    if (bbWidth <= 0.0f || bbHeight <= 0.0f || clientWidth <= 0.0f || clientHeight <= 0.0f ||
        (bbWidth == clientWidth && bbHeight == clientHeight))
        return lParam;

    int x = (int)(GET_X_LPARAM(lParam) * (bbWidth / clientWidth));
    int y = (int)(GET_Y_LPARAM(lParam) * (bbHeight / clientHeight));
    return MAKELPARAM(x, y);
}

static LRESULT CALLBACK Overlay_WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    if (g_imguiReady && g_visible) {
        LPARAM adjustedLParam = IsClientCoordMouseMsg(msg) ? RescaleMouseLParam(hWnd, lParam) : lParam;
        ImGui_ImplWin32_WndProcHandler(hWnd, msg, wParam, adjustedLParam);
        ImGuiIO& io = ImGui::GetIO();

        bool isMouseMsg = (msg >= WM_MOUSEFIRST && msg <= WM_MOUSELAST) || msg == WM_MOUSEWHEEL;
        bool isKeyMsg = (msg >= WM_KEYFIRST && msg <= WM_KEYLAST);
        if ((isMouseMsg && io.WantCaptureMouse) || (isKeyMsg && io.WantCaptureKeyboard))
            return TRUE; // swallow -- don't let the game also see this input
    }
    return CallWindowProc(g_originalWndProc, hWnd, msg, wParam, lParam);
}

void Overlay_Init(void* pDevice, HWND hWnd) {
    if (g_imguiReady) return;
    g_hWnd = hWnd;

    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    ImGui::StyleColorsDark();

    ImGui_ImplWin32_Init(hWnd);
    ImGui_ImplDX8_Init((IDirect3DDevice8*)pDevice);

    g_originalWndProc = (WNDPROC)SetWindowLongPtr(hWnd, GWLP_WNDPROC, (LONG_PTR)Overlay_WndProc);

    g_imguiReady = true;
}

void Overlay_OnLostDevice() {
    if (g_imguiReady) ImGui_ImplDX8_InvalidateDeviceObjects();
}

void Overlay_OnResetDevice() {
    if (g_imguiReady) ImGui_ImplDX8_CreateDeviceObjects();
}

void Overlay_Render(void* pDevice) {
    if (!g_imguiReady) return;

    // toggle with INSERT, edge-triggered so holding it doesn't flicker
    bool insertDown = (GetAsyncKeyState(VK_INSERT) & 0x8000) != 0;
    if (insertDown && !g_insertWasDown) g_visible = !g_visible;
    g_insertWasDown = insertDown;

    Overlay_ForceCursorVisible(g_visible);
    Overlay_ApplyCursorLock(g_visible, g_hWnd);
    if (!g_visible) return;

    ImGui_ImplDX8_NewFrame();
    ImGui_ImplWin32_NewFrame();

    // ImGui_ImplWin32_NewFrame() just set io.DisplaySize from the window's
    // client rect (GetClientRect). SetupRenderState (in imgui_impl_dx8.cpp)
    // renders/projects using the *actual* D3D8 back buffer size instead,
    // because D3D8 rejects/mishandles a viewport bigger than the render
    // target. Normally those two sizes match; a tool like DXWnd that
    // intercepts CreateDevice/Reset to force its own resolution/aspect ratio
    // can make them differ. Override DisplaySize to the real back-buffer
    // size so ImGui's own widget layout matches what actually gets rendered.
    // (Mouse position is handled separately, in Overlay_WndProc -- rescaling
    // it here raced against ImGui's input-event queue and caused visible
    // jumps; see RescaleMouseLParam's comment.)
    {
        ImGuiIO& io = ImGui::GetIO();
        float bbWidth = 0.0f, bbHeight = 0.0f;
        ImGui_ImplDX8_GetBackBufferSize(&bbWidth, &bbHeight);
        if (bbWidth > 0.0f && bbHeight > 0.0f)
            io.DisplaySize = ImVec2(bbWidth, bbHeight);
    }

    ImGui::NewFrame();

    PlayerPosition_Draw();

    ImGui::Render();
    ImGui_ImplDX8_RenderDrawData(ImGui::GetDrawData());
}
