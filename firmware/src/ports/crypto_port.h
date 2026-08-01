#ifndef DMRV_CRYPTO_PORT_H
#define DMRV_CRYPTO_PORT_H

#include <stddef.h>
#include <stdint.h>

/* Producer identity + hashing. Adapter (E4/A4 decision) backs this with the
 * ESP32-S3 flash-encrypted NVS Ed25519 key (default) or a secure element.
 * The domain NEVER sees key material — only these calls. */

/* SHA-256 of `in` -> 32-byte `out`. Returns 0 on success. */
int crypto_sha256(const uint8_t *in, size_t len, uint8_t out[32]);

/* Ed25519-sign `msg` with the device's private key -> 64-byte `sig`.
 * Returns 0 on success. */
int crypto_ed25519_sign(const uint8_t *msg, size_t len, uint8_t sig[64]);

/* Copy the device's 32-byte Ed25519 public key -> `out`. Returns 0 on success. */
int crypto_public_key(uint8_t out[32]);

#endif /* DMRV_CRYPTO_PORT_H */
