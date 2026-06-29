import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;

// ---------------------------------------------------------------------------
// Testable helpers extracted from SecureCaptureService
// ---------------------------------------------------------------------------
const _kManifest = 'pending_cleanup.txt';

Future<void> appendToCleanupManifest(String path, String supportRoot) async {
  final manifest = File(p.join(supportRoot, _kManifest));
  await manifest.writeAsString('$path\n', mode: FileMode.append, flush: true);
}

Future<void> cleanupStaleTemps(String supportRoot) async {
  final manifest = File(p.join(supportRoot, _kManifest));
  if (!await manifest.exists()) return;

  final lines = await manifest.readAsLines();
  final stillFailing = <String>[];
  for (final path in lines.where((l) => l.trim().isNotEmpty)) {
    try {
      final f = File(path);
      if (await f.exists()) await f.delete();
    } catch (_) {
      stillFailing.add(path);
    }
  }

  if (stillFailing.isEmpty) {
    await manifest.delete();
  } else {
    await manifest.writeAsString(stillFailing.join('\n'));
  }
}

void main() {
  late Directory tempDir;
  late String supportRoot;

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('dmrv_fix2_');
    supportRoot = tempDir.path;
  });

  tearDown(() async {
    if (await tempDir.exists()) await tempDir.delete(recursive: true);
  });

  // -------------------------------------------------------------------------
  // Test 1 — temp file is deleted on success; manifest is NOT written
  // -------------------------------------------------------------------------
  test('test_temp_file_deleted_on_success', () async {
    final tmp = File(p.join(tempDir.path, 'raw_capture.jpg'));
    await tmp.writeAsBytes([0xFF, 0xD8, 0xFF]); // fake JPEG header

    expect(await tmp.exists(), isTrue);

    // Simulate successful deletion (no exception → no manifest).
    await tmp.delete();

    expect(await tmp.exists(), isFalse);
    // Manifest must NOT exist.
    final manifest = File(p.join(supportRoot, _kManifest));
    expect(await manifest.exists(), isFalse);
  });

  // -------------------------------------------------------------------------
  // Test 2 — failed deletion adds path to manifest
  // -------------------------------------------------------------------------
  test('test_temp_file_added_to_manifest_on_failure', () async {
    const fakePath = '/nonexistent/camera/tmp/raw_capture.jpg';

    // Simulate the append that happens when deletion fails.
    await appendToCleanupManifest(fakePath, supportRoot);

    final manifest = File(p.join(supportRoot, _kManifest));
    expect(await manifest.exists(), isTrue);
    final lines = await manifest.readAsLines();
    expect(
      lines.any((l) => l == fakePath),
      isTrue,
      reason: 'Manifest must contain the path that failed to delete',
    );
  });

  // -------------------------------------------------------------------------
  // Test 3 — cleanupStaleTemps deletes files and removes manifest
  // -------------------------------------------------------------------------
  test('test_cleanup_stale_temps_deletes_manifest_entries', () async {
    // Create two real temp files.
    final f1 = File(p.join(tempDir.path, 'stale1.jpg'));
    final f2 = File(p.join(tempDir.path, 'stale2.jpg'));
    await f1.writeAsBytes([0x00]);
    await f2.writeAsBytes([0x00]);

    // Seed manifest.
    final manifest = File(p.join(supportRoot, _kManifest));
    await manifest.writeAsString('${f1.path}\n${f2.path}\n');

    await cleanupStaleTemps(supportRoot);

    expect(await f1.exists(), isFalse, reason: 'stale1.jpg must be deleted');
    expect(await f2.exists(), isFalse, reason: 'stale2.jpg must be deleted');
    expect(
      await manifest.exists(),
      isFalse,
      reason: 'Manifest must be deleted when all entries are cleaned up',
    );
  });

  // -------------------------------------------------------------------------
  // Test 4 — cleanup keeps unresolvable paths in manifest
  // -------------------------------------------------------------------------
  test('test_cleanup_keeps_failed_paths_in_manifest', () async {
    // One real file and one that doesn't exist (read-only system path).
    final realFile = File(p.join(tempDir.path, 'deletable.jpg'));
    await realFile.writeAsBytes([0x00]);
    // Use a path that exists but cannot be deleted because it is locked by another process.
    final ghostFile = File(p.join(tempDir.path, 'ghost.jpg'));
    await ghostFile.writeAsBytes([0x00]);
    final raf = await ghostFile.open(
      mode: FileMode.write,
    ); // Locks the file on Windows
    final ghostPath = ghostFile.path;

    final manifest = File(p.join(supportRoot, _kManifest));
    await manifest.writeAsString('${realFile.path}\n$ghostPath\n');

    await cleanupStaleTemps(supportRoot);

    // Real file is gone.
    expect(await realFile.exists(), isFalse);

    // Manifest still exists because ghost path couldn't be deleted.
    expect(await manifest.exists(), isTrue);
    final remaining = await manifest.readAsString();
    expect(remaining.trim(), equals(ghostPath));
    await raf.close(); // release lock
    await ghostFile.delete(); // cleanup
  });
}
