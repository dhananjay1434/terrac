#ifndef DMRV_AGGREGATE_H
#define DMRV_AGGREGATE_H

#include <stddef.h>

/* Channel kind decides the bucket reducer: temperatures average, load takes the
 * last reading (weight is a level, not a rate). */
typedef enum { AGG_MEAN, AGG_LAST } agg_kind_t;

/* Reduce `n` 1 Hz samples in one 10 s bucket to a single value, ROUNDED TO 1
 * DECIMAL PLACE so canonical.c's "%.1f" is exact (the FLOAT PRECISION INVARIANT).
 * n must be >= 1. */
double aggregate_bucket(const double *samples, size_t n, agg_kind_t kind);

/* Round to exactly 1 decimal place (exposed for reuse/testing). */
double round_1dp(double x);

#endif /* DMRV_AGGREGATE_H */
