#ifndef DMRV_BLE_PORT_H
#define DMRV_BLE_PORT_H
#include <stddef.h>
#include <stdint.h>
/* Transmit one already-framed packet (<= negotiated MTU) on the TX characteristic. */
int ble_tx(const uint8_t *packet, size_t len);
/* Register a callback for inbound RX packets; the domain parses them via frame.h. */
typedef void (*ble_rx_cb_t)(const uint8_t *packet, size_t len);
void ble_on_rx(ble_rx_cb_t cb);
/* Start/refresh advertising. has_data drives D2 (data present) vs D2a (idle beacon). */
int ble_advertise(const char *device_id, uint32_t unsynced_bytes, int has_data);
#endif /* DMRV_BLE_PORT_H */
