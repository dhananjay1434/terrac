import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/data/field_walk_link.dart';

/// V8 Part 5 (A phase-2) — pure parser tests for the field-walk QR link,
/// mirroring enrollment_qr_test.dart's coverage shape.
void main() {
  group('parseFieldWalkLink', () {
    test('parses a well-formed link', () {
      final raw = 'dmrv-fieldwalk:v1:'
          '{"payload":"{\\"parcel_uuid\\":\\"p-1\\",\\"nonce\\":\\"n1\\",'
          '\\"issued_at\\":\\"2026-07-22T00:00:00+00:00\\",'
          '\\"expires_at\\":\\"2026-07-23T00:00:00+00:00\\"}",'
          '"kid":"sk1","signature":"sig-abc"}';
      final link = parseFieldWalkLink(raw);
      expect(link, isNotNull);
      expect(link!.parcelUuid, 'p-1');
      expect(link.kid, 'sk1');
      expect(link.signature, 'sig-abc');
      expect(link.expiresAt.year, 2026);
    });

    test('isExpired reflects the parsed expires_at', () {
      final expired = 'dmrv-fieldwalk:v1:'
          '{"payload":"{\\"parcel_uuid\\":\\"p-1\\",\\"nonce\\":\\"n1\\",'
          '\\"issued_at\\":\\"2000-01-01T00:00:00+00:00\\",'
          '\\"expires_at\\":\\"2000-01-02T00:00:00+00:00\\"}",'
          '"kid":"sk1","signature":"sig-abc"}';
      final link = parseFieldWalkLink(expired);
      expect(link, isNotNull);
      expect(link!.isExpired, isTrue);
    });

    test('wrong version prefix returns null', () {
      expect(parseFieldWalkLink('dmrv-fieldwalk:v2:{}'), isNull);
    });

    test('missing prefix entirely returns null', () {
      expect(parseFieldWalkLink('{"payload":"x"}'), isNull);
    });

    test('malformed outer JSON returns null, never throws', () {
      expect(parseFieldWalkLink('dmrv-fieldwalk:v1:not json'), isNull);
    });

    test('missing kid/signature/payload returns null', () {
      expect(
        parseFieldWalkLink('dmrv-fieldwalk:v1:{"payload":"{}"}'),
        isNull,
      );
    });

    test('malformed inner payload JSON returns null', () {
      expect(
        parseFieldWalkLink(
          'dmrv-fieldwalk:v1:{"payload":"not json","kid":"sk1","signature":"s"}',
        ),
        isNull,
      );
    });

    test('inner payload missing parcel_uuid returns null', () {
      final raw = 'dmrv-fieldwalk:v1:'
          '{"payload":"{\\"nonce\\":\\"n1\\",\\"expires_at\\":\\"2026-07-23T00:00:00+00:00\\"}",'
          '"kid":"sk1","signature":"s"}';
      expect(parseFieldWalkLink(raw), isNull);
    });

    test('inner payload with unparsable expires_at returns null', () {
      final raw = 'dmrv-fieldwalk:v1:'
          '{"payload":"{\\"parcel_uuid\\":\\"p-1\\",\\"nonce\\":\\"n1\\",'
          '\\"expires_at\\":\\"not-a-date\\"}",'
          '"kid":"sk1","signature":"s"}';
      expect(parseFieldWalkLink(raw), isNull);
    });

    test('empty string returns null', () {
      expect(parseFieldWalkLink(''), isNull);
    });
  });
}
