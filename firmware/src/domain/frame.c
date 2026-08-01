#include "frame.h"
#include <string.h>

int dmrv_frame_encode(const dmrv_frame_t *f, uint8_t *out, size_t out_size) {
    if (out_size < DMRV_FRAME_HEADER_LEN + f->payload_len) return -1;
    size_t o = 0;
    out[o++] = f->msg_type;
    out[o++] = (uint8_t)(f->chunk_id >> 24);
    out[o++] = (uint8_t)(f->chunk_id >> 16);
    out[o++] = (uint8_t)(f->chunk_id >> 8);
    out[o++] = (uint8_t)(f->chunk_id);
    out[o++] = (uint8_t)(f->packet_index >> 8);
    out[o++] = (uint8_t)(f->packet_index);
    out[o++] = (uint8_t)(f->total_packets >> 8);
    out[o++] = (uint8_t)(f->total_packets);
    if (f->payload_len) memcpy(out + o, f->payload, f->payload_len);
    return (int)(o + f->payload_len);
}

int dmrv_frame_decode(const uint8_t *buf, size_t len, dmrv_frame_t *f) {
    if (len < DMRV_FRAME_HEADER_LEN) return -1;
    f->msg_type      = buf[0];
    f->chunk_id      = ((uint32_t)buf[1] << 24) | ((uint32_t)buf[2] << 16)
                     | ((uint32_t)buf[3] << 8)  | (uint32_t)buf[4];
    f->packet_index  = (uint16_t)((buf[5] << 8) | buf[6]);
    f->total_packets = (uint16_t)((buf[7] << 8) | buf[8]);
    f->payload       = buf + DMRV_FRAME_HEADER_LEN;
    f->payload_len   = len - DMRV_FRAME_HEADER_LEN;
    return 0;
}
