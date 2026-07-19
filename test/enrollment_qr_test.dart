import 'package:dmrv_app/data/enrollment_qr.dart';
import 'package:flutter_test/flutter_test.dart';

/// V6 Phase 1 — the pure parser for the portal enrollment payload
/// `dmrv-enroll:v1:{"url":..,"token":..}`. Never throws; returns null so the
/// caller can fall back to treating raw input as a bare token.
void main() {
  group('parseEnrollmentQr', () {
    test('valid payload → url + token', () {
      final p = parseEnrollmentQr(
        'dmrv-enroll:v1:{"url":"https://dmrv-api.onrender.com","token":"NCt_ABC123"}',
      );
      expect(p, isNotNull);
      expect(p!.url, 'https://dmrv-api.onrender.com');
      expect(p.token, 'NCt_ABC123');
    });

    test('empty url in payload → token set, url blank (operator keeps URL)', () {
      final p = parseEnrollmentQr('dmrv-enroll:v1:{"url":"","token":"tok_only"}');
      expect(p, isNotNull);
      expect(p!.url, '');
      expect(p.token, 'tok_only');
    });

    test('missing url key → token set, url blank', () {
      final p = parseEnrollmentQr('dmrv-enroll:v1:{"token":"tok_only"}');
      expect(p, isNotNull);
      expect(p!.url, '');
      expect(p.token, 'tok_only');
    });

    test('bare token (no prefix) → null (caller treats as plain token)', () {
      expect(parseEnrollmentQr('NCt_VLaTnV9oMnpk8gdelqWyhqA7aP2PNxVW7irq7S8'),
          isNull);
    });

    test('malformed JSON after prefix → null, no throw', () {
      expect(parseEnrollmentQr('dmrv-enroll:v1:{not json'), isNull);
    });

    test('missing token → null', () {
      expect(parseEnrollmentQr('dmrv-enroll:v1:{"url":"https://x"}'), isNull);
    });

    test('blank token → null', () {
      expect(
          parseEnrollmentQr('dmrv-enroll:v1:{"url":"https://x","token":"  "}'),
          isNull);
    });

    test('surrounding whitespace tolerated', () {
      final p = parseEnrollmentQr(
        '  dmrv-enroll:v1:{"url":"https://x","token":"t"}  ',
      );
      expect(p, isNotNull);
      expect(p!.token, 't');
      expect(p.url, 'https://x');
    });

    test('inner values are trimmed', () {
      final p = parseEnrollmentQr(
        'dmrv-enroll:v1:{"url":" https://x ","token":" t "}',
      );
      expect(p!.url, 'https://x');
      expect(p.token, 't');
    });

    test('wrong version prefix → null', () {
      expect(
          parseEnrollmentQr('dmrv-enroll:v2:{"url":"https://x","token":"t"}'),
          isNull);
    });

    test('JSON array (not object) after prefix → null', () {
      expect(parseEnrollmentQr('dmrv-enroll:v1:["a","b"]'), isNull);
    });

    test('empty string → null', () {
      expect(parseEnrollmentQr(''), isNull);
    });
  });
}
