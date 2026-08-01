/* Host test: proves canonical_serialize reproduces the committed golden vectors
 * byte-for-byte. The two expected strings below ARE the canonical bytes in
 * backend/tools/golden_vectors.json (decode canonical_hex to see them). If that
 * file is regenerated with different envelopes, update these two literals. */
#include <assert.h>
#include <locale.h>
#include <stdio.h>
#include <string.h>
#include "../src/domain/canonical.h"

static int check(const char *label, const telemetry_envelope_t *e, const char *expect) {
    char buf[2048];
    int n = canonical_serialize(e, buf, sizeof buf);
    if (n < 0) { printf("[%s] OVERFLOW\n", label); return 1; }
    if (strcmp(buf, expect) != 0) {
        printf("[%s] MISMATCH\n got: %s\n exp: %s\n", label, buf, expect);
        return 1;
    }
    printf("[%s] ok (%d bytes)\n", label, n);
    return 0;
}

int main(void) {
    setlocale(LC_ALL, "C");
    int fails = 0;

    double v1[] = {412.5, 418.0, 421.2};
    telemetry_envelope_t e1 = {
        .device_id = "edge-001", .session_uuid = "sess-0001", .batch_uuid = NULL,
        .channel = "T1", .t_start = "2026-07-23T09:00:00Z", .sample_period_s = 10.0,
        .values = v1, .values_len = 3, .seq = 0, .prev_hash = "GENESIS",
    };
    fails += check("vector-1",  &e1,
        "{\"batch_uuid\":null,\"channel\":\"T1\",\"device_id\":\"edge-001\","
        "\"prev_hash\":\"GENESIS\",\"sample_period_s\":10.0,\"seq\":0,"
        "\"session_uuid\":\"sess-0001\",\"t_start\":\"2026-07-23T09:00:00Z\","
        "\"values\":[412.5,418.0,421.2]}");

    double v2[] = {120.0, 121.6};
    telemetry_envelope_t e2 = {
        .device_id = "edge-001", .session_uuid = "sess-0001", .batch_uuid = NULL,
        .channel = "LOAD", .t_start = "2026-07-23T09:00:00Z", .sample_period_s = 10.0,
        .values = v2, .values_len = 2, .seq = 1,
        .prev_hash = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    };
    fails += check("vector-2",  &e2,
        "{\"batch_uuid\":null,\"channel\":\"LOAD\",\"device_id\":\"edge-001\","
        "\"prev_hash\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\","
        "\"sample_period_s\":10.0,\"seq\":1,\"session_uuid\":\"sess-0001\","
        "\"t_start\":\"2026-07-23T09:00:00Z\",\"values\":[120.0,121.6]}");

    if (fails) { printf("FAILED: %d vector(s)\n", fails); return 1; }
    printf("all canonical vectors match\n");
    return 0;
}
