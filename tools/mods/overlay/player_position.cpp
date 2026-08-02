#include <cstdint>
#include <cstdlib>
#include <windows.h>

#include "imgui/imgui.h"
#include "player_position.h"

// Pointer chain from Game.exe's base: base+BASE_OFFSET -> +0xA8 -> +0x230,
// then the position floats sit at +0x150/+0x154/+0x158 (X/Y/Z) off that.
static const uintptr_t BASE_OFFSET   = 0x0021818C;
static const uintptr_t OFFSET_1      = 0xA8;
static const uintptr_t OFFSET_2      = 0x230;
static const uintptr_t POS_X_OFFSET  = 0x150;
static const uintptr_t POS_Y_OFFSET  = 0x154;
static const uintptr_t POS_Z_OFFSET  = 0x158;

// In-process equivalent of pymem's ReadProcessMemory/WriteProcessMemory:
// those fail gracefully (an exception the Python script catches) when handed
// a bad address in another process. A raw pointer dereference in our own
// process has no such protection -- it's a hard access violation -- so these
// wrap each access in SEH and report failure instead of crashing the game.
static bool SafeReadUInt32(uintptr_t addr, uint32_t* out) {
    __try {
        *out = *reinterpret_cast<uint32_t*>(addr);
        return true;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static bool SafeReadFloat(uintptr_t addr, float* out) {
    __try {
        *out = *reinterpret_cast<float*>(addr);
        return true;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static bool SafeWriteFloat(uintptr_t addr, float value) {
    __try {
        *reinterpret_cast<float*>(addr) = value;
        return true;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

// Walks base+BASE_OFFSET -> +0xA8 -> +0x230, treating a null or unreadable
// pointer at any step as "not resolvable" (e.g. no level loaded yet) rather
// than crashing.
static bool ResolvePlayerBase(uintptr_t* outAddr) {
    HMODULE hGame = GetModuleHandleA(nullptr);
    if (!hGame)
        return false;
    uintptr_t addr = reinterpret_cast<uintptr_t>(hGame);

    uint32_t next;
    if (!SafeReadUInt32(addr + BASE_OFFSET, &next) || !next) return false;
    if (!SafeReadUInt32(next + OFFSET_1, &next) || !next) return false;
    if (!SafeReadUInt32(next + OFFSET_2, &next) || !next) return false;

    *outAddr = next;
    return true;
}

void PlayerPosition_Draw() {
    ImGui::Begin("Player Position");

    uintptr_t base;
    bool resolved = ResolvePlayerBase(&base);

    float x = 0.0f, y = 0.0f, z = 0.0f;
    bool readOk = resolved &&
        SafeReadFloat(base + POS_X_OFFSET, &x) &&
        SafeReadFloat(base + POS_Y_OFFSET, &y) &&
        SafeReadFloat(base + POS_Z_OFFSET, &z);

    if (readOk) {
        ImGui::Text("X %10.3f", x);
        ImGui::Text("Y %10.3f", y);
        ImGui::Text("Z %10.3f", z);
    } else {
        ImGui::TextColored(ImVec4(1.0f, 0.4f, 0.4f, 1.0f),
            resolved ? "Error reading position" : "Pointer chain unresolved (not in a level?)");
    }

    ImGui::Separator();

    static char xBuf[32] = "";
    static char yBuf[32] = "";
    static char zBuf[32] = "";
    ImGui::InputText("X##set", xBuf, sizeof(xBuf));
    ImGui::InputText("Y##set", yBuf, sizeof(yBuf));
    ImGui::InputText("Z##set", zBuf, sizeof(zBuf));

    if (ImGui::Button("Set Position")) {
        uintptr_t setBase;
        if (ResolvePlayerBase(&setBase)) {
            if (xBuf[0]) SafeWriteFloat(setBase + POS_X_OFFSET, (float)atof(xBuf));
            if (yBuf[0]) SafeWriteFloat(setBase + POS_Y_OFFSET, (float)atof(yBuf));
            if (zBuf[0]) SafeWriteFloat(setBase + POS_Z_OFFSET, (float)atof(zBuf));
        }
    }

    ImGui::End();
}
