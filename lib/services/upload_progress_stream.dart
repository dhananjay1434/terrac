/// V8 Part 4 (H) — wraps a byte stream so each chunk reports a running
/// fraction-complete via [onProgress]. Pure with respect to its inputs (a
/// stream + a known total + a callback), so it's unit-testable with a fake
/// stream — no HTTP or file I/O required. Used to drive the multipart
/// media-upload progress shown on `SyncHealthScreen`.
Stream<List<int>> trackUploadProgress(
  Stream<List<int>> source,
  int totalBytes,
  void Function(double fraction) onProgress,
) {
  if (totalBytes <= 0) return source;
  var sent = 0;
  return source.map((chunk) {
    sent += chunk.length;
    onProgress((sent / totalBytes).clamp(0.0, 1.0));
    return chunk;
  });
}
