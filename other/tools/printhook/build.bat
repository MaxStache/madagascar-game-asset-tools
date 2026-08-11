@echo off
REM Build the d3d8.dll logging proxy (32-bit).
REM Run this from the "x86 Native Tools Command Prompt for VS" so cl targets x86.
setlocal

where cl >nul 2>nul
if %errorlevel%==0 (
    echo [build] using MSVC cl ...
    cl /nologo /LD /O2 /MT /DNDEBUG d3d8_proxy.cpp /link /DEF:d3d8.def /OUT:d3d8.dll
    del /q d3d8.obj d3d8.exp d3d8.lib 2>nul
    goto :done
)

where i686-w64-mingw32-g++ >nul 2>nul
if %errorlevel%==0 (
    echo [build] using MinGW i686-w64-mingw32-g++ ...
    i686-w64-mingw32-g++ -shared -O2 -m32 -static -static-libgcc -static-libstdc++ ^
        -o d3d8.dll d3d8_proxy.cpp d3d8.def
    goto :done
)

echo [build] ERROR: no 32-bit compiler found.
echo         Open "x86 Native Tools Command Prompt for VS" (MSVC Build Tools),
echo         or install MinGW-w64 (i686). Then re-run build.bat.
exit /b 1

:done
if exist d3d8.dll ( echo [build] OK -^> d3d8.dll ) else ( echo [build] FAILED & exit /b 1 )
