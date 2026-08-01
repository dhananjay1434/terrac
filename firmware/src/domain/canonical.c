#include "canonical.h"
#include <stdio.h>
#include <string.h>

/* Append s at offset off; return new offset or -1 on overflow (sticky: once -1,
 * every later call returns -1, so the caller only needs to check the end). */
static int put(char *out, size_t size, int off, const char *s) {
    if (off < 0) return -1;
    size_t len = strlen(s);
    if ((size_t)off + len + 1 > size) return -1;
    memcpy(out + off, s, len);
    out[off + len] = '\0';
    return off + (int)len;
}

/* "key":"value"  or  "key":null  */
static int put_str(char *out, size_t size, int off, const char *key, const char *val) {
    off = put(out, size, off, "\"");
    off = put(out, size, off, key);
    off = put(out, size, off, "\":");
    if (val == NULL) return put(out, size, off, "null");
    off = put(out, size, off, "\"");
    off = put(out, size, off, val);
    return put(out, size, off, "\"");
}

int canonical_serialize(const telemetry_envelope_t *e, char *out, size_t out_size) {
    /* NOTE: uses "%.1f" — requires the C locale (decimal point '.'). Embedded
     * newlib defaults to C; on a host test call setlocale(LC_ALL,"C") if unsure. */
    char num[64];
    int off = put(out, out_size, 0, "{");
    /* sorted keys: batch_uuid, channel, device_id, prev_hash,
     *              sample_period_s, seq, session_uuid, t_start, values */
    off = put_str(out, out_size, off, "batch_uuid", e->batch_uuid);
    off = put(out, out_size, off, ",");
    off = put_str(out, out_size, off, "channel", e->channel);
    off = put(out, out_size, off, ",");
    off = put_str(out, out_size, off, "device_id", e->device_id);
    off = put(out, out_size, off, ",");
    off = put_str(out, out_size, off, "prev_hash", e->prev_hash);
    off = put(out, out_size, off, ",");
    snprintf(num, sizeof num, "%.1f", e->sample_period_s);
    off = put(out, out_size, off, "\"sample_period_s\":");
    off = put(out, out_size, off, num);
    off = put(out, out_size, off, ",");
    snprintf(num, sizeof num, "%ld", e->seq);
    off = put(out, out_size, off, "\"seq\":");
    off = put(out, out_size, off, num);
    off = put(out, out_size, off, ",");
    off = put_str(out, out_size, off, "session_uuid", e->session_uuid);
    off = put(out, out_size, off, ",");
    off = put_str(out, out_size, off, "t_start", e->t_start);
    off = put(out, out_size, off, ",");
    off = put(out, out_size, off, "\"values\":[");
    for (size_t i = 0; i < e->values_len; i++) {
        if (i > 0) off = put(out, out_size, off, ",");
        snprintf(num, sizeof num, "%.1f", e->values[i]);
        off = put(out, out_size, off, num);
    }
    return put(out, out_size, off, "]}");
}
