import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// V8 Part 4 (J) — India pincode → district/state auto-fill (field-UX pack).
/// Public third-party API (api.postalpincode.in), no auth. Pure-core/thin-edge
/// split: [parseResponse] is pure and unit-testable against a fixture JSON;
/// [lookup] is the thin network edge (unverifiable live in this environment).
/// Any failure (offline, malformed pincode, non-200, unexpected shape) returns
/// null — the operator always keeps typing the address by hand; auto-fill is
/// a convenience, never a requirement.
class PincodeLookupResult {
  const PincodeLookupResult({required this.district, required this.state});
  final String district;
  final String state;
}

class PincodeLookupService {
  static final RegExp _validPincode = RegExp(r'^[1-9][0-9]{5}$');

  static Future<PincodeLookupResult?> lookup(
    String pincode, {
    http.Client? client,
  }) async {
    if (!_validPincode.hasMatch(pincode.trim())) return null;
    final c = client ?? http.Client();
    try {
      final resp = await c
          .get(Uri.parse('https://api.postalpincode.in/pincode/${pincode.trim()}'))
          .timeout(const Duration(seconds: 8));
      if (resp.statusCode != 200) return null;
      return parseResponse(jsonDecode(resp.body));
    } catch (e) {
      debugPrint('[PincodeLookupService] lookup failed: $e');
      return null;
    } finally {
      if (client == null) c.close();
    }
  }

  /// Pure parse of the api.postalpincode.in response shape:
  /// `[{"Status":"Success","PostOffice":[{"District":"...","State":"..."}]}]`
  /// Returns null for ANY unexpected shape rather than throwing — a parsing
  /// surprise degrades to "no auto-fill", never a crash.
  @visibleForTesting
  static PincodeLookupResult? parseResponse(dynamic body) {
    if (body is! List || body.isEmpty) return null;
    final first = body[0];
    if (first is! Map || first['Status'] != 'Success') return null;
    final offices = first['PostOffice'];
    if (offices is! List || offices.isEmpty) return null;
    final office = offices[0];
    if (office is! Map) return null;
    final district = office['District'];
    final state = office['State'];
    if (district is! String || state is! String) return null;
    if (district.isEmpty || state.isEmpty) return null;
    return PincodeLookupResult(district: district, state: state);
  }
}
