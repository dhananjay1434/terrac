import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/upload_progress_stream.dart';

/// V8 Part 4 (H) — pure test of the byte-counting progress wrapper: no HTTP,
/// no file I/O, just a fake chunked stream and a known total.
void main() {
  group('trackUploadProgress', () {
    test('reports monotonically increasing fractions ending at 1.0', () async {
      final chunks = [
        List.filled(25, 0),
        List.filled(25, 0),
        List.filled(25, 0),
        List.filled(25, 0),
      ];
      final reported = <double>[];
      final source = Stream.fromIterable(chunks);
      await trackUploadProgress(source, 100, reported.add).drain();
      expect(reported, [0.25, 0.5, 0.75, 1.0]);
    });

    test('passes chunks through unmodified', () async {
      final chunks = [
        [1, 2, 3],
        [4, 5],
      ];
      final source = Stream.fromIterable(chunks);
      final out = await trackUploadProgress(
        source,
        5,
        (_) {},
      ).toList();
      expect(out, chunks);
    });

    test('totalBytes <= 0 passes the stream through with no progress calls', () async {
      var calls = 0;
      final source = Stream.fromIterable([
        [1, 2],
      ]);
      final out = await trackUploadProgress(source, 0, (_) => calls++).toList();
      expect(calls, 0);
      expect(out, [
        [1, 2],
      ]);
    });

    test('clamps a stray fraction to at most 1.0 (more bytes than declared)', () async {
      final reported = <double>[];
      final source = Stream.fromIterable([
        List.filled(50, 0),
        List.filled(50, 0),
      ]);
      await trackUploadProgress(source, 60, reported.add).drain();
      expect(reported.last, 1.0);
    });
  });
}
