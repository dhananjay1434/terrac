#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../src/domain/frame.h"

int main(void) {
    uint8_t payload[] = {0xDE, 0xAD, 0xBE, 0xEF};
    dmrv_frame_t f = { .msg_type = 2, .chunk_id = 0x01020304,
                       .packet_index = 1, .total_packets = 3,
                       .payload = payload, .payload_len = 4 };
    uint8_t buf[64];
    int n = dmrv_frame_encode(&f, buf, sizeof buf);
    assert(n == DMRV_FRAME_HEADER_LEN + 4);
    assert(buf[0] == 2);
    assert(buf[1] == 0x01 && buf[2] == 0x02 && buf[3] == 0x03 && buf[4] == 0x04);
    assert(buf[5] == 0 && buf[6] == 1);
    assert(buf[7] == 0 && buf[8] == 3);

    dmrv_frame_t g;
    assert(dmrv_frame_decode(buf, (size_t)n, &g) == 0);
    assert(g.msg_type == 2 && g.chunk_id == 0x01020304);
    assert(g.packet_index == 1 && g.total_packets == 3);
    assert(g.payload_len == 4 && memcmp(g.payload, payload, 4) == 0);

    assert(dmrv_frame_decode(buf, 3, &g) == -1);   /* short buffer */
    printf("frame ok\n");
    return 0;
}
