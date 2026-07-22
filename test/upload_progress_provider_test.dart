import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/providers/upload_progress_provider.dart';

/// V8 Part 4 (H) — the in-flight-uploads map that drives the SyncHealthScreen
/// progress banner.
void main() {
  group('UploadProgressNotifier', () {
    test('starts empty', () {
      final n = UploadProgressNotifier();
      expect(n.state, isEmpty);
    });

    test('report adds/updates an entry, clamped to [0, 1]', () {
      final n = UploadProgressNotifier();
      n.report('op-1', 0.5);
      expect(n.state['op-1'], 0.5);
      n.report('op-1', 1.5);
      expect(n.state['op-1'], 1.0);
      n.report('op-1', -0.5);
      expect(n.state['op-1'], 0.0);
    });

    test('multiple operations are tracked independently', () {
      final n = UploadProgressNotifier();
      n.report('op-1', 0.3);
      n.report('op-2', 0.7);
      expect(n.state, {'op-1': 0.3, 'op-2': 0.7});
    });

    test('clear removes only the named entry', () {
      final n = UploadProgressNotifier();
      n.report('op-1', 0.3);
      n.report('op-2', 0.7);
      n.clear('op-1');
      expect(n.state, {'op-2': 0.7});
    });

    test('clear on an absent operationId is a no-op', () {
      final n = UploadProgressNotifier();
      n.report('op-1', 0.3);
      n.clear('nonexistent');
      expect(n.state, {'op-1': 0.3});
    });
  });
}
