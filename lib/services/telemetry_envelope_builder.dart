import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'crypto_signer.dart';
import 'telemetry_canonical.dart';

class SignedChunk {
  final Map<String, dynamic> envelope; // includes producer_signature
  final String nextPrevHash;
  SignedChunk(this.envelope, this.nextPrevHash);
}
class TelemetryEnvelopeBuilder {
  static Future<SignedChunk> build({
    required String deviceId, required String sessionUuid, String? batchUuid,
    required String channel, required String tStartIso, required double samplePeriodS,
    required List<double> values, required int seq, required String prevHash,
  }) async {
    final envelope = <String, dynamic>{
      'device_id': deviceId, 'session_uuid': sessionUuid, 'batch_uuid': batchUuid,
      'channel': channel, 't_start': tStartIso, 'sample_period_s': samplePeriodS,
      'values': values, 'seq': seq, 'prev_hash': prevHash,
    };
    final canonical = utf8.encode(canonicalJson(envelope));
    final signature = await CryptoSigner.signBytesB64(canonical);
    final nextPrev = sha256.convert(canonical).toString();
    return SignedChunk({...envelope, 'producer_signature': signature}, nextPrev);
  }
}
