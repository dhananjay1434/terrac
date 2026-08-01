#include "aggregate.h"
#include <math.h>

double round_1dp(double x) {
    /* round-half-away-from-zero at 1 decimal */
    return (x < 0.0 ? -1.0 : 1.0) * floor(fabs(x) * 10.0 + 0.5) / 10.0;
}

double aggregate_bucket(const double *samples, size_t n, agg_kind_t kind) {
    if (n == 0) return 0.0;             /* caller guarantees n>=1; defensive */
    if (kind == AGG_LAST) return round_1dp(samples[n - 1]);
    double sum = 0.0;
    for (size_t i = 0; i < n; i++) sum += samples[i];
    return round_1dp(sum / (double)n);
}
