#ifndef DMRV_TELEMETRY_ENVELOPE_H
#define DMRV_TELEMETRY_ENVELOPE_H

#include <stddef.h>

/* One telemetry chunk, exactly the fields the backend signs (TelemetryChunkIn).
 * producer_signature is intentionally ABSENT: it is never part of the signed bytes.
 * NULL for batch_uuid / prev_hash serializes as JSON null. */
typedef struct {
    const char   *device_id;
    const char   *session_uuid;
    const char   *batch_uuid;   /* NULL -> null */
    const char   *channel;
    const char   *t_start;      /* ISO-8601 UTC, e.g. "2026-07-23T09:00:00Z" */
    double        sample_period_s;
    const double *values;
    size_t        values_len;
    long          seq;
    const char   *prev_hash;    /* NULL -> null; "GENESIS" for seq 0 */
} telemetry_envelope_t;

#endif /* DMRV_TELEMETRY_ENVELOPE_H */
