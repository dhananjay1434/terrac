#ifndef DMRV_CANONICAL_H
#define DMRV_CANONICAL_H

#include <stddef.h>
#include "telemetry_envelope.h"

/* Serialize `e` into the CANONICAL JSON the backend verifies:
 *   - keys sorted alphabetically
 *   - compact separators (',' and ':'), no whitespace
 *   - producer_signature excluded
 *   - floats formatted at 1 decimal place (FLOAT PRECISION INVARIANT)
 *   - UTF-8 / ASCII
 * Writes a NUL-terminated string to `out`. Returns the byte length written
 * (excluding NUL), or -1 if it would overflow `out_size`.
 *
 * ASCII-SAFE ASSUMPTION: string fields contain no characters needing JSON
 * escaping (true for device ids, channels, uuids, ISO timestamps, hex hashes).
 * If a future field can contain '"' '\\' or control chars, extend the escaper
 * in canonical.c — that is the single place to change. */
int canonical_serialize(const telemetry_envelope_t *e, char *out, size_t out_size);

#endif /* DMRV_CANONICAL_H */
