import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

/// =============================================================================
/// BatchSessionNotifier (Addresses audit Gap 5.3)
/// =============================================================================
/// Single source of truth for the *active* batchUuid. Every downstream screen
/// (Sourcing, Moisture, Pyrolysis, Yield, EndUse) must attach its data to the
/// batchUuid held here. Without an active batch, no domain write is allowed
/// to reach the Outbox.
///
///   • `start()`  — generates a fresh UUID v4, replaces any prior session.
///   • `end()`    — clears the session (e.g. after final upload).
///   • `state`    — null when no batch is active, else the active UUID.
/// =============================================================================

const _uuid = Uuid();

class BatchSessionNotifier extends Notifier<String?> {
  @override
  String? build() => null;

  /// Begin a new batch. Returns the freshly minted batchUuid.
  String start() {
    final id = _uuid.v4();
    state = id;
    return id;
  }

  /// Tear down the active batch session.
  void end() {
    state = null;
  }

  /// Rehydrates the active batch session from the local database.
  /// Used in production when the app restarts with an incomplete batch.
  void restore(String? batchUuid) {
    state = batchUuid;
  }
}

final batchSessionProvider = NotifierProvider<BatchSessionNotifier, String?>(
  BatchSessionNotifier.new,
);

/// Convenience selector — throws if no batch is active. Use this from
/// downstream screens so an accidental write without a session fails loudly
/// rather than silently corrupting the Outbox.
final requiredBatchUuidProvider = Provider<String>((ref) {
  final id = ref.watch(batchSessionProvider);
  if (id == null) {
    throw StateError(
      'No active batch. Call BatchSessionNotifier.start() from the Dashboard '
      'before navigating into the sourcing workflow.',
    );
  }
  return id;
});
