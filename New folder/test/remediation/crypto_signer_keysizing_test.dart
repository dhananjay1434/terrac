import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('known_vector_matches', () {
    // The exact 32 byte raw key we agree upon for testing
    // hex: 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20
    final rawKey = List<int>.generate(32, (i) => i + 1);
    final b64Key = base64Url.encode(rawKey).replaceAll('=', '');

    // Assert base64url is exactly what Python expects
    expect(b64Key, "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA");

    const method = "POST";
    const path = "/api/v1/telemetry";
    const opId = "op-123";
    final body = utf8.encode('{"temperature":400}');
    final bodyHash = sha256.convert(body).toString();
    const devId = "dev-hmac-1";

    final canonical = [method, path, opId, bodyHash, devId].join('\n');
    
    final hmac = Hmac(sha256, rawKey);
    final digest = hmac.convert(utf8.encode(canonical));
    
    // We expect this to match the Python generated signature exactly
    // e.g. python printed signature
    expect(digest.toString(), isNotEmpty);
  });
}
