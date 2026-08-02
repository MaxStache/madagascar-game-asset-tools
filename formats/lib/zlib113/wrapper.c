/* Thin C shim exposing raw DEFLATE compression from vendored zlib 1.1.3.
 *
 * The original game assets were gzipped with zlib 1.1.3 (confirmed via the
 * "deflate 1.1.3" / "inflate 1.1.3" copyright strings embedded in the PS2
 * executable). Modern zlib produces different compressed bytes for
 * identical input due to internal match-finding changes across versions,
 * so byte-identical repacks require compressing with this exact version.
 */
#include "vendor/zlib.h"

/* Returns Z_OK/etc from deflateInit2 or deflate, or Z_STREAM_ERROR-style
 * failure. On success, *outlen is set to the compressed size written to out. */
int rw_deflate_113(const unsigned char *in, unsigned long inlen,
                    unsigned char *out, unsigned long outcap,
                    unsigned long *outlen, int level, int memLevel,
                    int strategy) {
    z_stream strm;
    int ret;

    strm.zalloc = Z_NULL;
    strm.zfree = Z_NULL;
    strm.opaque = Z_NULL;

    /* windowBits = -15 => raw deflate stream, no zlib/gzip wrapper */
    ret = deflateInit2(&strm, level, Z_DEFLATED, -15, memLevel, strategy);
    if (ret != Z_OK) {
        return ret;
    }

    strm.next_in = (Bytef *)in;
    strm.avail_in = (uInt)inlen;
    strm.next_out = (Bytef *)out;
    strm.avail_out = (uInt)outcap;

    ret = deflate(&strm, Z_FINISH);
    if (ret != Z_STREAM_END) {
        deflateEnd(&strm);
        return ret;
    }

    *outlen = strm.total_out;
    return deflateEnd(&strm);
}
