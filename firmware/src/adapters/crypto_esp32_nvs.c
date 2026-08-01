/* 🔵 HUMAN-GATED ADAPTER STUB — implements ports/crypto_port.h on ESP32-S3.
 *
 * DO NOT ship as-is: every function below returns -1 (not implemented) so the
 * build links but nothing silently pretends to sign. A hardware engineer wires
 * these to the real primitives per the A4 decision:
 *   crypto_sha256          -> mbedtls_sha256 (esp-idf mbedTLS component)
 *   crypto_ed25519_sign    -> Ed25519 over the key in flash-encrypted NVS
 *                             (or a secure element if A4 chose one)
 *   crypto_public_key      -> read the enrolled public key
 * The pure domain and its tests never change when this is filled in. */
#include "../ports/crypto_port.h"

int crypto_sha256(const uint8_t *in, size_t len, uint8_t out[32]) {
    (void)in; (void)len; (void)out;
    return -1; /* TODO(hardware): mbedtls_sha256 */
}

int crypto_ed25519_sign(const uint8_t *msg, size_t len, uint8_t sig[64]) {
    (void)msg; (void)len; (void)sig;
    return -1; /* TODO(hardware): Ed25519 over NVS/secure-element key (A4) */
}

int crypto_public_key(uint8_t out[32]) {
    (void)out;
    return -1; /* TODO(hardware): read enrolled Ed25519 public key */
}
