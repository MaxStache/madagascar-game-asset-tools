#pragma once

// Runs a tiny local HTTP server (127.0.0.1:6742) that accepts
// `POST /stream` with the raw stream bytes as the request body, writes them
// to a temp file, and feeds that file into Game.exe's own resource-manager
// stream loader exactly the way a real disk-backed LoadStreamFile call
// would.
//
// Ghidra notes: CreateAndLoadStreamResource (0x004efd00) dispatches on its
// `resourceType` argument. resourceType=3 ("WrapMemoryBufferAsStreamResource")
// looks like the obvious pure-in-memory route -- it wraps a raw
// {dataPtr,size} pair directly -- but it marks the resource ready
// immediately, which specifically skips the pump loop inside
// WaitForStreamResourceReady that does the real work for resourceType=2:
// RwStreamReadChunkHeader -> look up the chunk's type in the global handler
// registry populated at startup (e.g. FUN_00552f00(0x704,
// CreateEntity_ChunkHandler)) -> invoke it. Type 3 structurally cannot reach
// that dispatcher, so nothing ever gets spawned into the world -- confirmed
// by testing (a real stream POSTed via type 3 produced a valid resource
// handle but no visible in-game effect). Routing through a real temp file
// with resourceType=2 reuses that exact, already-correct pipeline instead
// of reimplementing the device abstraction underneath it.

// Starts the HTTP server thread. Safe to call from DllMain -- the actual
// socket work happens on the spawned thread, not inline.
void StreamInject_Init();

// Drains any streams received since the last call and feeds them into the
// game's resource manager. Must be called from the main thread, once per
// frame -- none of the resource-manager code this reaches takes its own
// locks, so it isn't safe to call from the HTTP server's own thread.
void StreamInject_Pump();
