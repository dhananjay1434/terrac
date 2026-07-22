import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/pincode_lookup_service.dart';

/// V8 Part 4 (J) — pure-parser tests for the pincode auto-fill response
/// shape. The live network call to api.postalpincode.in cannot be verified
/// in this environment; these tests cover the part that matters — parsing
/// the real shape correctly and degrading to null on anything unexpected.
void main() {
  group('PincodeLookupService.parseResponse', () {
    test('parses a successful real-shaped response', () {
      final body = [
        {
          'Message': 'Number of pincode(s) found:1',
          'Status': 'Success',
          'PostOffice': [
            {
              'Name': 'Connaught Place',
              'District': 'New Delhi',
              'State': 'Delhi',
            },
          ],
        },
      ];
      final result = PincodeLookupService.parseResponse(body);
      expect(result, isNotNull);
      expect(result!.district, 'New Delhi');
      expect(result.state, 'Delhi');
    });

    test('returns null for Status != Success (invalid pincode)', () {
      final body = [
        {'Message': 'No records found', 'Status': 'Error', 'PostOffice': null},
      ];
      expect(PincodeLookupService.parseResponse(body), isNull);
    });

    test('returns null for an empty list', () {
      expect(PincodeLookupService.parseResponse(<dynamic>[]), isNull);
    });

    test('returns null when PostOffice is empty', () {
      final body = [
        {'Status': 'Success', 'PostOffice': <dynamic>[]},
      ];
      expect(PincodeLookupService.parseResponse(body), isNull);
    });

    test('returns null for a completely different shape (never throws)', () {
      expect(PincodeLookupService.parseResponse({'unexpected': true}), isNull);
      expect(PincodeLookupService.parseResponse('a string'), isNull);
      expect(PincodeLookupService.parseResponse(null), isNull);
      expect(PincodeLookupService.parseResponse(42), isNull);
    });

    test('returns null when District/State are missing or non-string', () {
      final body = [
        {
          'Status': 'Success',
          'PostOffice': [
            {'Name': 'X'},
          ],
        },
      ];
      expect(PincodeLookupService.parseResponse(body), isNull);
    });
  });
}
