#ifndef DMRV_STORAGE_PORT_H
#define DMRV_STORAGE_PORT_H

#include <stddef.h>
#include <stdint.h>

/* Append-only signed-chunk log on the SD card. Adapter backs this with FATFS.
 * Eviction rule (E6 + D3a) lives in the adapter: evictable = confirmed-synced
 * AND older than the 90-day retention floor; never evict unsynced data; if full
 * with unsynced backlog, refuse writes and raise a health flag (see health_port
 * / Health message). */

/* Append one record (canonical bytes + 64-byte signature). Returns 0, or
 * negative on error (-1 I/O, -2 FULL-with-unsynced-backlog). */
int storage_append(const uint8_t *canonical, size_t canonical_len, const uint8_t sig[64]);

/* Read the record with (session,channel,seq) into caller buffers. Returns record
 * length, 0 if not present, negative on error. Used to stream oldest-first and to
 * recover the chain tail on boot (E3). */
int storage_read(const char *session_uuid, const char *channel, long seq,
                 uint8_t *out, size_t out_size);

/* Highest seq stored for (session,channel), or -1 if none (chain resume, E3). */
long storage_max_seq(const char *session_uuid, const char *channel);

/* Advance the confirmed-synced watermark for (session,channel) after a verified
 * SyncAck (D3). The 90-day floor is still enforced on top of this. */
int storage_mark_synced(const char *session_uuid, const char *channel, long through_seq);

#endif /* DMRV_STORAGE_PORT_H */
