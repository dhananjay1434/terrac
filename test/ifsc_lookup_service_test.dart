import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/ifsc_lookup_service.dart';

/// V8 Part 4 (J) — pure-parser tests for the IFSC bank/branch lookup response
/// shape. The live network call to ifsc.razorpay.com cannot be verified in
/// this environment; these tests cover the part that matters.
void main() {
  group('IfscLookupService.parseResponse', () {
    test('parses a real-shaped response', () {
      final body = {
        'BANK': 'HDFC Bank',
        'IFSC': 'HDFC0001234',
        'BRANCH': 'Connaught Place',
        'STATE': 'Delhi',
      };
      final result = IfscLookupService.parseResponse(body);
      expect(result, isNotNull);
      expect(result!.bankName, 'HDFC Bank');
      expect(result.branch, 'Connaught Place');
    });

    test('returns null when BANK or BRANCH missing', () {
      expect(IfscLookupService.parseResponse({'BANK': 'HDFC Bank'}), isNull);
      expect(IfscLookupService.parseResponse({'BRANCH': 'CP'}), isNull);
    });

    test('returns null for a non-map body (never throws)', () {
      expect(IfscLookupService.parseResponse('not a map'), isNull);
      expect(IfscLookupService.parseResponse(null), isNull);
      expect(IfscLookupService.parseResponse(<dynamic>[]), isNull);
    });

    test('returns null when BANK/BRANCH are non-string or empty', () {
      expect(
        IfscLookupService.parseResponse({'BANK': 1, 'BRANCH': 'CP'}),
        isNull,
      );
      expect(
        IfscLookupService.parseResponse({'BANK': '', 'BRANCH': 'CP'}),
        isNull,
      );
    });
  });
}
