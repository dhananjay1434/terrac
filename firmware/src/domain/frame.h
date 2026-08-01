#ifndef DMRV_FRAME_H
#define DMRV_FRAME_H

#include <stddef.h>
#include <stdint.h>

#define DMRV_FRAME_HEADER_LEN 9  /* 1 + 4 + 2 + 2 */

typedef struct {
    uint8_t  msg_type;
    uint32_t chunk_id;
    uint16_t packet_index;
    uint16_t total_packets;
    const uint8_t *payload;
    size_t   payload_len;
} dmrv_frame_t;

/* Encode header+payload big-endian into out. Returns total bytes, or -1 on
 * overflow. */
int  dmrv_frame_encode(const dmrv_frame_t *f, uint8_t *out, size_t out_size);

/* Decode a buffer into f (f->payload points INTO buf, not copied). Returns 0 on
 * success, -1 if buf is shorter than the header. */
int  dmrv_frame_decode(const uint8_t *buf, size_t len, dmrv_frame_t *f);

#endif /* DMRV_FRAME_H */
