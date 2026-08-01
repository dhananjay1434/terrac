#ifndef DMRV_RTC_PORT_H
#define DMRV_RTC_PORT_H
#include <stdint.h>
/* Milliseconds since Unix epoch, UTC (DS3231-backed adapter). */
uint64_t rtc_now_utc_ms(void);
/* Set the clock from a trusted courier TimeSync (D5). Returns 0 on success. */
int rtc_set_utc_ms(uint64_t utc_ms);
#endif /* DMRV_RTC_PORT_H */
