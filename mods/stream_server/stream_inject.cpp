// windows.h pulls in the legacy Winsock 1.1 header (winsock.h) unless this
// is defined first, which then collides with winsock2.h below.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "stream_inject.h"

#pragma comment(lib, "Ws2_32.lib")

// -------------------------------------------------------------------------
// Game-internal function addresses, recovered via Ghidra static analysis of
// Game.exe (LoadStreamFile @ 0x4627e0 and its callees). The image base at
// analysis time was 0x00400000; addresses are computed relative to the
// running module here (base + RVA) so relocation, if any, doesn't matter.
// -------------------------------------------------------------------------
static const uintptr_t RVA_CreateAndLoadStreamResource = 0x0EFD00; // 0x004efd00
static const uintptr_t RVA_WaitForStreamResourceReady  = 0x152F70; // 0x00552f70
static const uintptr_t RVA_FinalizeStreamResource      = 0x0EFBF0; // 0x004efbf0

// undefined4 __cdecl CreateAndLoadStreamResource(resourceType, mode, pathOrBuffer)
typedef void*    (__cdecl* CreateAndLoadStreamResource_t)(uint32_t resourceType, uint32_t mode, void* pathOrBuffer);
// undefined4 __cdecl WaitForStreamResourceReady(hResource) -- only the low byte is meaningful (bool)
typedef uint32_t (__cdecl* WaitForStreamResourceReady_t)(void* hResource);
// uint __cdecl FinalizeStreamResource(hResource, pOutResult)
typedef uint32_t (__cdecl* FinalizeStreamResource_t)(void* hResource, void* pOutResult);

struct StreamResultBuffer { void* data; uint32_t size; };

static CreateAndLoadStreamResource_t g_CreateAndLoadStreamResource = nullptr;
static WaitForStreamResourceReady_t  g_WaitForStreamResourceReady  = nullptr;
static FinalizeStreamResource_t      g_FinalizeStreamResource      = nullptr;

// resourceType=3 ("WrapMemoryBufferAsStreamResource") looked like the obvious
// choice for a pure in-memory load, but it starts the resource already
// marked ready -- which specifically SKIPS the pump loop inside
// WaitForStreamResourceReady that does the real work for resourceType=2
// (RwStreamReadChunkHeader -> look up the chunk's type in the global
// handler registry populated at startup by calls like
// FUN_00552f00(0x704, CreateEntity_ChunkHandler) -> invoke it). Type 3
// structurally cannot reach that dispatcher, so nothing ever gets spawned
// into the world. Going through a real temp file with resourceType=2
// reuses that exact, already-correct pipeline instead of trying to
// reimplement the device abstraction underneath it (pooled "file slot"
// objects behind a vtable -- Open/Exists/poll/signal are mapped, Read/Seek/
// Close are not, and getting the struct layout even slightly wrong there
// risks corrupting engine state rather than just failing to load).
static uint32_t g_TempFileCounter = 0;

static void ResolveGameFunctions() {
    uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleA(nullptr));
    g_CreateAndLoadStreamResource = reinterpret_cast<CreateAndLoadStreamResource_t>(base + RVA_CreateAndLoadStreamResource);
    g_WaitForStreamResourceReady  = reinterpret_cast<WaitForStreamResourceReady_t>(base + RVA_WaitForStreamResourceReady);
    g_FinalizeStreamResource      = reinterpret_cast<FinalizeStreamResource_t>(base + RVA_FinalizeStreamResource);
}

// -------------------------------------------------------------------------
// Queue of stream buffers received over HTTP, waiting to be handed to the
// game on the main thread.
// -------------------------------------------------------------------------
struct PendingStream { void* data; uint32_t size; };

static CRITICAL_SECTION           g_QueueLock;
static std::vector<PendingStream> g_PendingStreams;
static bool                       g_QueueLockReady = false;

static void QueuePendingStream(void* data, uint32_t size) {
    EnterCriticalSection(&g_QueueLock);
    g_PendingStreams.push_back({ data, size });
    LeaveCriticalSection(&g_QueueLock);
}

// Writes `data` out to a fresh temp file and returns its full path, or an
// empty string on failure. Each call gets a unique name (counter + tick
// count) so concurrent requests can't collide.
static std::string WriteTempStreamFile(const void* data, uint32_t size) {
    char tempDir[MAX_PATH];
    if (!GetTempPathA(MAX_PATH, tempDir)) return std::string();

    char path[MAX_PATH];
    wsprintfA(path, "%sstream_inject_%08x_%04x.stream", tempDir, GetTickCount(),
        InterlockedIncrement(reinterpret_cast<LONG*>(&g_TempFileCounter)));

    HANDLE hFile = CreateFileA(path, GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (hFile == INVALID_HANDLE_VALUE) return std::string();

    DWORD written = 0;
    BOOL ok = WriteFile(hFile, data, size, &written, nullptr);
    CloseHandle(hFile);
    if (!ok || written != size) {
        DeleteFileA(path);
        return std::string();
    }
    return std::string(path);
}

// Calls into the game's own resource manager, wrapped in SEH: the
// resource-manager singleton (DAT_0062ac18 in the Ghidra listing) might not
// be initialized yet if a request lands before the game's finished
// booting, and a dropped request beats a crashed game.
static void InjectOneStream(const std::string& path) {
    __try {
        void* hResource = g_CreateAndLoadStreamResource(/*resourceType=*/2, /*mode=*/1, (void*)path.c_str());
        if (!hResource) {
            OutputDebugStringA("[stream_inject] CreateAndLoadStreamResource returned null\n");
            return;
        }
        g_WaitForStreamResourceReady(hResource); // runs the real chunk-dispatch pump loop
        StreamResultBuffer result{};
        g_FinalizeStreamResource(hResource, &result);

        char msg[MAX_PATH + 64];
        wsprintfA(msg, "[stream_inject] injected %s -> handle %p\n", path.c_str(), hResource);
        OutputDebugStringA(msg);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        OutputDebugStringA("[stream_inject] exception while injecting stream, dropped\n");
    }
}

void StreamInject_Pump() {
    if (!g_QueueLockReady) return;

    std::vector<PendingStream> local;
    EnterCriticalSection(&g_QueueLock);
    local.swap(g_PendingStreams);
    LeaveCriticalSection(&g_QueueLock);

    for (PendingStream& req : local) {
        std::string path = WriteTempStreamFile(req.data, req.size);
        free(req.data); // copied to disk (or the write failed) -- no longer needed either way

        if (path.empty()) {
            OutputDebugStringA("[stream_inject] failed to write temp stream file\n");
            continue;
        }
        InjectOneStream(path);
        // Not deleting the temp file here: WaitForStreamResourceReady blocks
        // until the resource is fully loaded, so by the time we get here the
        // game should be done reading it -- but if that assumption is wrong
        // for some resource type, deleting a still-open file is a worse
        // failure mode than leaving a harmless file in %TEMP%.
    }
}

// -------------------------------------------------------------------------
// Minimal blocking HTTP/1.1 server: POST /stream, raw body = stream bytes.
// Single-threaded accept loop -- this is a local dev tool, not a real
// server, and every request is small and short-lived.
// -------------------------------------------------------------------------
static void HandleClient(SOCKET client) {
    std::string headerBuf;
    char chunk[4096];

    size_t headerEnd = std::string::npos;
    while (headerEnd == std::string::npos) {
        int n = recv(client, chunk, sizeof(chunk), 0);
        if (n <= 0) { closesocket(client); return; }
        headerBuf.append(chunk, n);
        headerEnd = headerBuf.find("\r\n\r\n");
        if (headerBuf.size() > 64 * 1024) { closesocket(client); return; } // runaway header guard
    }

    std::string headers = headerBuf.substr(0, headerEnd);
    std::string body = headerBuf.substr(headerEnd + 4);

    bool isPostStream = headers.compare(0, 12, "POST /stream") == 0;

    long contentLength = 0;
    size_t pos = headers.find("Content-Length:");
    if (pos == std::string::npos) pos = headers.find("content-length:");
    if (pos != std::string::npos) {
        pos += strlen("Content-Length:");
        while (pos < headers.size() && headers[pos] == ' ') pos++;
        contentLength = atol(headers.c_str() + pos);
    }

    if (contentLength > 0) {
        body.reserve(contentLength);
        while ((long)body.size() < contentLength) {
            long remaining = contentLength - (long)body.size();
            int want = remaining < (long)sizeof(chunk) ? (int)remaining : (int)sizeof(chunk);
            int n = recv(client, chunk, want, 0);
            if (n <= 0) break;
            body.append(chunk, n);
        }
    }

    const char* resp = "HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n";
    if (isPostStream) {
        if (!body.empty()) {
            void* copy = malloc(body.size());
            if (copy) {
                memcpy(copy, body.data(), body.size());
                QueuePendingStream(copy, (uint32_t)body.size());
                resp = "HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK";
            } else {
                resp = "HTTP/1.1 500 Internal Server Error\r\nContent-Length: 0\r\nConnection: close\r\n\r\n";
            }
        } else {
            resp = "HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\nConnection: close\r\n\r\n";
        }
    }

    send(client, resp, (int)strlen(resp), 0);
    closesocket(client);
}

static DWORD WINAPI HttpServerThread(LPVOID) {
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) return 1;

    SOCKET listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listener == INVALID_SOCKET) { WSACleanup(); return 1; }

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK); // 127.0.0.1 only -- never exposed to the network
    addr.sin_port = htons(6742);

    if (bind(listener, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) == SOCKET_ERROR) {
        OutputDebugStringA("[stream_inject] bind() failed on 127.0.0.1:6742 (already in use?)\n");
        closesocket(listener);
        WSACleanup();
        return 1;
    }
    listen(listener, 8);
    OutputDebugStringA("[stream_inject] listening on 127.0.0.1:6742 (POST /stream)\n");

    for (;;) {
        sockaddr_in clientAddr{};
        int clientAddrLen = sizeof(clientAddr);
        SOCKET client = accept(listener, reinterpret_cast<sockaddr*>(&clientAddr), &clientAddrLen);
        if (client == INVALID_SOCKET) continue;
        HandleClient(client);
    }
}

void StreamInject_Init() {
    ResolveGameFunctions();
    InitializeCriticalSection(&g_QueueLock);
    g_QueueLockReady = true;
    CreateThread(nullptr, 0, HttpServerThread, nullptr, 0, nullptr);
}
