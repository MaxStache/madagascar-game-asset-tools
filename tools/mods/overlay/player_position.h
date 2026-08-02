#pragma once

// Draws the player-position viewer/editor window. Ported from a standalone
// pymem+tkinter script into the overlay: since this code runs inside
// Game.exe's own process, reading/writing the pointer chain is direct
// pointer dereferencing rather than cross-process ReadProcessMemory/
// WriteProcessMemory, wrapped in SEH so a stale pointer chain (e.g. before
// a level has loaded) shows an error in the overlay instead of crashing
// the game.
void PlayerPosition_Draw();
