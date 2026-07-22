import 'package:flutter_riverpod/flutter_riverpod.dart';

/// V8 Part 4 (H) — per-operation media upload progress (0.0–1.0), keyed by
/// sync-outbox operationId. [SyncQueueManager] reports into this during the
/// multipart upload byte-stream; `SyncHealthScreen` watches it to render a
/// progress bar on whichever row is currently in flight. Entries are removed
/// on completion/failure so the map only ever holds genuinely in-flight rows.
class UploadProgressNotifier extends StateNotifier<Map<String, double>> {
  UploadProgressNotifier() : super(const {});

  void report(String operationId, double fraction) {
    state = {...state, operationId: fraction.clamp(0.0, 1.0)};
  }

  void clear(String operationId) {
    if (!state.containsKey(operationId)) return;
    final next = {...state}..remove(operationId);
    state = next;
  }
}

final uploadProgressProvider =
    StateNotifierProvider<UploadProgressNotifier, Map<String, double>>(
      (ref) => UploadProgressNotifier(),
    );
