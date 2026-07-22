import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// V8 Part 4 (J) — IFSC → bank/branch auto-fill (field-UX pack), for the
/// farmer payment screen. Public third-party API (ifsc.razorpay.com), no
/// auth. Same pure-core/thin-edge split as PincodeLookupService — this is a
/// DISPLAY-ONLY confirmation ("Bank: X, Branch: Y") so the operator can catch
/// a mistyped code; it never blocks or overrides the typed IFSC value.
class IfscLookupResult {
  const IfscLookupResult({required this.bankName, required this.branch});
  final String bankName;
  final String branch;
}

class IfscLookupService {
  static final RegExp _validIfsc = RegExp(r'^[A-Z]{4}0[A-Z0-9]{6}$');

  static Future<IfscLookupResult?> lookup(
    String ifscCode, {
    http.Client? client,
  }) async {
    final code = ifscCode.trim().toUpperCase();
    if (!_validIfsc.hasMatch(code)) return null;
    final c = client ?? http.Client();
    try {
      final resp = await c
          .get(Uri.parse('https://ifsc.razorpay.com/$code'))
          .timeout(const Duration(seconds: 8));
      if (resp.statusCode != 200) return null;
      return parseResponse(jsonDecode(resp.body));
    } catch (e) {
      debugPrint('[IfscLookupService] lookup failed: $e');
      return null;
    } finally {
      if (client == null) c.close();
    }
  }

  /// Pure parse of the ifsc.razorpay.com response shape:
  /// `{"BANK":"...","BRANCH":"...", ...}`. Returns null for any unexpected
  /// shape rather than throwing.
  @visibleForTesting
  static IfscLookupResult? parseResponse(dynamic body) {
    if (body is! Map) return null;
    final bank = body['BANK'];
    final branch = body['BRANCH'];
    if (bank is! String || branch is! String) return null;
    if (bank.isEmpty || branch.isEmpty) return null;
    return IfscLookupResult(bankName: bank, branch: branch);
  }
}
