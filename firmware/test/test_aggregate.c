#include <assert.h>
#include <math.h>
#include <stdio.h>
#include "../src/domain/aggregate.h"

static int close_to(double a, double b) { return fabs(a - b) < 1e-9; }

int main(void) {
    double t[] = {412.4, 412.6, 412.5};          /* mean 412.5 */
    assert(close_to(aggregate_bucket(t, 3, AGG_MEAN), 412.5));

    double load[] = {120.0, 120.5, 121.6};        /* last 121.6 */
    assert(close_to(aggregate_bucket(load, 3, AGG_LAST), 121.6));

    assert(close_to(round_1dp(421.23), 421.2));    /* rounds down */
    assert(close_to(round_1dp(421.25), 421.3));    /* half away from zero */
    assert(close_to(round_1dp(418.0), 418.0));

    printf("aggregate ok\n");
    return 0;
}
