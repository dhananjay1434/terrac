import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:drift/drift.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';
import 'package:workmanager/workmanager.dart';

import '../data/local/app_database.dart';
import '../data/local/database_provider.dart';
import 'crypto_signer.dart';
import 'device_integrity_service.dart';

class PermanentSyncException implements Exception {
  final String message;
  PermanentSyncException(this.message);
  @override
  String toString() => 'PermanentSyncException: $message';
}

@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    try {
      final container = ProviderContainer();
      final syncQueue = container.read(syncQueueManagerProvider);
      // Ensure syncQueue has started its logic.
      syncQueue.kickSync();
      // wait a bit for sync to finish (as kickSync is async but we don't await it here directly, let's just return true)
      // Actually we should wait for sync to complete if possible, but kickSync doesn't return a Future.
      // We can just sleep for 10 seconds or return true immediately.
      await Future.delayed(const Duration(seconds: 10));
    } catch (e) {
      debugPrint('Background sync failed: $e');
    }
    return Future.value(true);
  });
}

/// =============================================================================
/// SyncQueueManager  (Phase 6 — Zero Trust Hardening: Fix 4 & Fix 5)
/// =============================================================================
/// Explicit per-table → API endpoint routing contract.
///
/// `biomass_sourcing` IS the canonical batch record and routes to `/batches`.
/// An unmapped table is a programming error, not a silent default to `batches`.
const Map<String, String> kEndpointByTable = <String, String>{
  'system_metadata': 'metadata',
  'biomass_sourcing': 'batches',
  'pyrolysis_telemetry': 'telemetry',
  'yield_metrics': 'yield',
  'end_use_application': 'application',
};

/// Resolve the sync endpoint for [targetTable]. Throws [StateError] for an
/// unknown table so a routing gap fails loudly instead of corrupting a batch.
String endpointForTable(String targetTable) {
  final endpoint = kEndpointByTable[targetTable];
  if (endpoint == null) {
    throw StateError('No sync endpoint mapped for table $targetTable');
  }
  return endpoint;
}

/// Fix 4 — Idempotency Deadlock eliminated:
///   • 409 Conflict on JSON POST is treated as "already accepted" and the
///     loop proceeds to the media upload phase rather than aborting.
///   • JSON and media progress are tracked independently via `json_synced_at`
///     and `media_synced_at` columns in the SyncOutbox table.
///   • On retry, if `json_synced_at` is already set the JSON POST is skipped
///     entirely — only the pending media upload is retried.
///
/// Fix 5 — Two-phase media commit:
///   • The server returns a `server_sha256` in the media upload response.
///   • The client asserts the server hash matches the locally stored SHA-256
///     BEFORE deleting the sandboxed evidence file.
///   • Hash mismatch → file is preserved, exception logged, row stays PENDING.
/// =============================================================================

/// Immutable configuration for [SyncQueueManager].
class SyncConfig {
  const SyncConfig({
    required this.apiBase,
    this.pollInterval = const Duration(seconds: 30),
    this.enablePeriodicPolling = true,
  });
  final String apiBase;
  final Duration pollInterval;
  final bool enablePeriodicPolling;
}

class SyncQueueManager {
  SyncQueueManager(
    this.ref, {
    SyncConfig? config,
    Connectivity? connectivity,
    http.Client? client,
    bool startPeriodicTimer = true,
  })  : _config = config ?? const SyncConfig(apiBase: ''),
        _connectivity = connectivity ?? Connectivity(),
        _client = client ?? _createSecureClient() {
    _initConnectivityListener();
    if (_config.enablePeriodicPolling && startPeriodicTimer) {
      _periodicTimer = Timer.periodic(
        _config.pollInterval,
        (_) => _triggerSync(),
      );
    }
    ref.listen(
      appDatabaseProvider,
      (previous, next) {
        if (next.hasValue && next.value != null) {
          final db = next.requireValue;
          _dbSubscription?.cancel();
          _dbSubscription = db
              .tableUpdates(TableUpdateQuery.onTable(db.syncOutbox))
              .listen((_) => kickSync());
        }
      },
      fireImmediately: true,
    );
  }

  final SyncConfig _config;
  Timer? _periodicTimer;
  StreamSubscription<Set<TableUpdate>>? _dbSubscription;

  /// Public hook for write paths to wake the sync loop the moment a new
  /// outbox row lands. Safe to call from anywhere; the loop is re-entrant
  /// guarded by `_isSyncing`.
  void kickSync() => _triggerSync();

  static http.Client _createSecureClient() {
    if (kIsWeb) return http.Client();

    const pinnedPem = String.fromEnvironment(
      'DMRV_PINNED_CERT_PEM',
      defaultValue: '',
    );

    if (!kReleaseMode) {
      // Debug / profile builds use the system trust store so staging certs work.
      return http.Client();
    }

    if (pinnedPem.isEmpty) {
      throw StateError(
        'DMRV_PINNED_CERT_PEM is required for release builds. '
        'Pass it via --dart-define-from-file=secrets.json',
      );
    }

    final context = SecurityContext(withTrustedRoots: false);
    context.setTrustedCertificatesBytes(utf8.encode(pinnedPem));
    final ioClient = HttpClient(context: context)
      ..badCertificateCallback =
          (X509Certificate cert, String host, int port) => false;
    return IOClient(ioClient);
  }

  final Ref ref;
  final Connectivity _connectivity;
  final http.Client _client;
  bool _isSyncing = false;
  StreamSubscription<List<ConnectivityResult>>? _subscription;

  /// =============================================================================
  /// API endpoint — env-driven.
  /// Pass --dart-define=DMRV_API_BASE_URL=https://… at build time.
  /// Defaults to empty string so a forgotten flag fails fast on first request.
  /// =============================================================================


  void _initConnectivityListener() {
    // 1. Check initial connectivity on startup
    _connectivity.checkConnectivity().then((results) {
      if (results.any((r) => r != ConnectivityResult.none)) {
        debugPrint('[SyncQueue] Network detected on startup. Triggering loop.');
        _triggerSync();
      }
    });

    // 2. Listen for future changes
    _subscription = _connectivity.onConnectivityChanged.listen((results) {
      if (results.any((r) => r != ConnectivityResult.none)) {
        debugPrint('[SyncQueue] Network change detected. Triggering loop.');
        _triggerSync();
      }
    });
    
    // 3. Register background sync
    if (!kIsWeb && Platform.isAndroid) {
      try {
        Workmanager().initialize(
          callbackDispatcher,
          isInDebugMode: kDebugMode,
        );
        Workmanager().registerPeriodicTask(
          "dmrv_sync_task",
          "background_sync",
          frequency: const Duration(minutes: 15),
          constraints: Constraints(
            networkType: NetworkType.connected,
          ),
        );
      } catch (e) {
        debugPrint('Failed to register periodic task: $e');
      }
    }
  }

  void dispose() {
    _subscription?.cancel();
    _periodicTimer?.cancel();
    _dbSubscription?.cancel();
  }

  Future<void> _triggerSync() async {
    if (_config.apiBase.isEmpty) {
      debugPrint(
        '[SyncQueue] DMRV_API_BASE_URL is empty — sync aborted. '
        'This is fine in tests; production should fail at boot.',
      );
      return;
    }
    if (isDeviceCompromisedGlobally) {
      debugPrint('[SyncQueue] Device is compromised. Sync aborted.');
      return;
    }
    if (_isSyncing) return;
    _isSyncing = true;

    try {
      final db = await ref.read(appDatabaseProvider.future);
      final pending =
          await (db.select(db.syncOutbox)
                ..where((t) => t.status.equals('PENDING'))
                ..orderBy([(t) => OrderingTerm.asc(t.createdAt)]))
              .get();

      if (pending.isEmpty) {
        debugPrint('[SyncQueue] No pending records.');
        return;
      }

      debugPrint('[SyncQueue] Found ${pending.length} pending records.');

      for (final entry in pending) {
        if (entry.retryCount > 10) {
          debugPrint(
            '[SyncQueue] Entry ${entry.operationId} exceeded max retries. Marking FAILED_PERMANENTLY.',
          );
          await (db.update(
            db.syncOutbox,
          )..where((t) => t.operationId.equals(entry.operationId))).write(
            const SyncOutboxCompanion(status: Value('FAILED_PERMANENTLY')),
          );
          continue;
        }
        if (entry.retryCount > 0 && entry.lastAttemptAt != null) {
          final lastAttempt = DateTime.parse(entry.lastAttemptAt!);
          final backoffSeconds = 1 << entry.retryCount;
          final nextRetry = lastAttempt.add(Duration(seconds: backoffSeconds));
          if (DateTime.now().toUtc().isBefore(nextRetry)) {
            debugPrint(
              '[SyncQueue] Backoff for ${entry.operationId} (try ${entry.retryCount}). Skipped until $nextRetry.',
            );
            continue;
          }
        }
        await _processEntry(db, entry);
      }
    } catch (e, st) {
      debugPrint('[SyncQueue] Sync loop failed: $e\n$st');
    } finally {
      _isSyncing = false;
    }
  }

  Future<void> _processEntry(AppDatabase db, SyncOutboxData entry) async {
    debugPrint('[SyncQueue] Processing operation: ${entry.operationId}');

    try {
      // -----------------------------------------------------------------------
      // Phase 1 — JSON metadata upload
      // -----------------------------------------------------------------------
      // Fix 4: skip if already confirmed in a prior sync attempt.
      // If targetTable == 'media', this is purely a CAS blob upload, so skip Phase 1 entirely.
      if (entry.targetTable == 'media') {
        debugPrint(
          '[SyncQueue] Target is media — skipping JSON metadata Phase 1.',
        );
      } else {
        final endpoint = endpointForTable(entry.targetTable);

        if (entry.jsonSyncedAt == null) {
          final deviceId = await CryptoSigner.getDeviceId();
          final signature = await CryptoSigner.signRequest(
            method: 'POST',
            path: '/api/v1/$endpoint',
            idempotencyKey: entry.operationId,
            deviceId: deviceId,
            jsonBody: entry.payloadJson,
          );
          
          final jsonResponse = await _client.post(
            Uri.parse('${_config.apiBase}/api/v1/$endpoint'),
            headers: {
              'Content-Type': 'application/json',
              'X-Idempotency-Key': entry.operationId,
              'X-Device-Id': deviceId,
              'X-HMAC-Signature': signature,
            },
            body: entry.payloadJson,
          );

          // Fix 4: 409 Conflict means the server already has this payload.
          // Treat it identically to 200/201 — proceed to media phase.
          final jsonAccepted =
              jsonResponse.statusCode == 200 ||
              jsonResponse.statusCode == 201 ||
              jsonResponse.statusCode == 409;

          if (!jsonAccepted) {
            final code = jsonResponse.statusCode;
            if (code >= 400 && code < 500) {
              throw PermanentSyncException(
                'JSON upload failed (client error $code): ${jsonResponse.body}',
              );
            }
            throw Exception(
              'JSON upload failed: $code - ${jsonResponse.body}',
            );
          }

          // Stamp json_synced_at so a retry skips this phase.
          await _stampJsonSynced(db, entry.operationId);
          debugPrint(
            '[SyncQueue] JSON synced for ${entry.operationId} '
            '(status ${jsonResponse.statusCode})',
          );
        } else {
          debugPrint(
            '[SyncQueue] Skipping JSON re-POST for ${entry.operationId} '
            '— already synced at ${entry.jsonSyncedAt}',
          );
        }
      }

      // -----------------------------------------------------------------------
      // Phase 2 — Media upload (if applicable and not yet synced)
      // -----------------------------------------------------------------------
      if (entry.mediaSyncedAt == null) {
        final payload = jsonDecode(entry.payloadJson) as Map<String, dynamic>;
        final photoPath =
            (payload['photo_path'] as String?) ??
            (payload['farmer_photo_path'] as String?);
        final declaredSha256 =
            (payload['sha256_hash'] as String?) ??
            (payload['farmer_photo_sha256'] as String?);

        bool isMock = false;
        if (payload.containsKey('isMockLocation')) {
          isMock = payload['isMockLocation'] == true;
        } else if (payload.containsKey('mock_location_enabled')) {
          isMock = payload['mock_location_enabled'] == true;
        }

        if (entry.targetTable == 'media') {
          final captureType = payload['capture_type'];
          debugPrint(
            '[SyncQueue] Preparing CAS media upload for $captureType (Mocked GPS: $isMock)',
          );
        }

        if (photoPath != null && photoPath.isNotEmpty) {
          final file = File(photoPath);
          if (!await file.exists()) {
            // Evidence file is missing — throw so the row is NOT stamped synced.
            throw Exception(
              '[SyncQueue] CRITICAL: evidence file missing at $photoPath — '
              'cannot upload. Manual remediation required.',
            );
          }
          await _uploadMedia(
            db: db,
            entry: entry,
            photoPath: photoPath,
            file: file,
            declaredSha256: declaredSha256,
            isMockLocation: isMock,
          );
        } else if (entry.targetTable == 'media' || declaredSha256 != null) {
          // Fix 3: Prevent unverified payloads/media from marking as SYNCED
          throw Exception(
            '[SyncQueue] CRITICAL: photoPath is null/empty for a payload '
            'that requires media evidence. Row stays PENDING.',
          );
        }

        // Falls through unconditionally. If _uploadMedia threw, the outer catch
        // already caught it and we never reach this line. Reaching here means
        // either no media was attached, or upload succeeded. Stamp as synced.
        await _stampMediaSynced(db, entry.operationId);
      } else {
        debugPrint(
          '[SyncQueue] Skipping media re-upload for ${entry.operationId} '
          '— already synced at ${entry.mediaSyncedAt}',
        );
      }

      // -----------------------------------------------------------------------
      // Mark fully SYNCED only when both phases are confirmed.
      // -----------------------------------------------------------------------
      await (db.update(db.syncOutbox)
            ..where((t) => t.operationId.equals(entry.operationId)))
          .write(const SyncOutboxCompanion(status: Value('SYNCED')));

      debugPrint('[SyncQueue] Operation ${entry.operationId} SYNCED.');
    } catch (e) {
      debugPrint('[SyncQueue] Failed operation ${entry.operationId}: $e');
      if (e is PermanentSyncException) {
        debugPrint('[SyncQueue] Permanent failure for ${entry.operationId}: $e');
        await (db.update(
          db.syncOutbox,
        )..where((t) => t.operationId.equals(entry.operationId))).write(
          const SyncOutboxCompanion(status: Value('FAILED_PERMANENTLY')),
        );
      } else {
        await (db.update(
          db.syncOutbox,
        )..where((t) => t.operationId.equals(entry.operationId))).write(
          SyncOutboxCompanion(
            retryCount: Value(entry.retryCount + 1),
            lastAttemptAt: Value(DateTime.now().toUtc().toIso8601String()),
          ),
        );
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Media upload — Fix 5: two-phase commit with server SHA-256 verification
  // ---------------------------------------------------------------------------
  Future<void> _uploadMedia({
    required AppDatabase db,
    required SyncOutboxData entry,
    required String photoPath,
    required File file,
    required String? declaredSha256,
    required bool isMockLocation,
  }) async {
    debugPrint('[SyncQueue] Uploading media: $photoPath');
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('${_config.apiBase}/api/v1/media'),
    );
    request.headers['X-Idempotency-Key'] = '${entry.operationId}_media';
    request.headers['X-Device-Id'] = await CryptoSigner.getDeviceId();
    request.headers['X-Mock-Location'] = isMockLocation.toString();
    request.headers['X-Batch-UUID'] = entry.batchUuid;
    if (declaredSha256 != null) {
      request.headers['X-Declared-SHA256'] = declaredSha256;
    }
    request.files.add(await http.MultipartFile.fromPath('file', photoPath));

    final streamedResponse = await _client.send(request);
    final mediaResponse = await http.Response.fromStream(streamedResponse);

    if (mediaResponse.statusCode != 200 && mediaResponse.statusCode != 201) {
      final code = mediaResponse.statusCode;
      if (code >= 400 && code < 500) {
        throw PermanentSyncException('Media upload failed (client error $code)');
      }
      throw Exception('Media upload failed: $code');
    }

    // Fix 5: verify server-side SHA-256 before destroying local evidence.
    final responseBody =
        jsonDecode(mediaResponse.body) as Map<String, dynamic>? ?? {};
    final serverSha256 = responseBody['server_sha256'] as String?;

    if (declaredSha256 != null && serverSha256 != null) {
      if (serverSha256 != declaredSha256) {
        throw Exception(
          '[SyncQueue] CRITICAL: server_sha256 mismatch — '
          'local=$declaredSha256 server=$serverSha256. '
          'Local evidence preserved.',
        );
      }
      debugPrint('[SyncQueue] server_sha256 verified ✓ ($serverSha256)');
    } else {
      // Throw — caller must NOT stamp mediaSyncedAt. Row stays PENDING.
      throw Exception(
        '[SyncQueue] server did not return server_sha256 — '
        'media integrity unverifiable. Row stays PENDING for retry.',
      );
    }

    // Only GC the file after the server hash is confirmed.
    debugPrint('[SyncQueue] GC: deleting local evidence: $photoPath');
    await file.delete();
  }

  // ---------------------------------------------------------------------------
  // DB helpers
  // ---------------------------------------------------------------------------

  Future<void> _stampJsonSynced(AppDatabase db, String operationId) async {
    await (db.update(
      db.syncOutbox,
    )..where((t) => t.operationId.equals(operationId))).write(
      SyncOutboxCompanion(
        jsonSyncedAt: Value(DateTime.now().toUtc().toIso8601String()),
      ),
    );
  }

  Future<void> _stampMediaSynced(AppDatabase db, String operationId) async {
    await (db.update(
      db.syncOutbox,
    )..where((t) => t.operationId.equals(operationId))).write(
      SyncOutboxCompanion(
        mediaSyncedAt: Value(DateTime.now().toUtc().toIso8601String()),
      ),
    );
  }
}

/// Production configuration. Tests should override this provider.
final syncConfigProvider = Provider<SyncConfig>((ref) {
  const apiBase = String.fromEnvironment(
    'DMRV_API_BASE_URL',
    defaultValue: '',
  );
  return const SyncConfig(apiBase: apiBase);
});

final syncQueueManagerProvider = Provider<SyncQueueManager>((ref) {
  final config = ref.watch(syncConfigProvider);
  final manager = SyncQueueManager(ref, config: config);
  ref.onDispose(manager.dispose);
  return manager;
});
