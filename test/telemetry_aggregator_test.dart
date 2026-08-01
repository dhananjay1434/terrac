import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/telemetry_aggregator.dart';
void main() {
  test('mean 1dp', () => expect(aggregateBucket([412.4, 412.6, 412.5], AggKind.mean), closeTo(412.5, 1e-9)));
  test('load last', () => expect(aggregateBucket([120.0, 120.5, 121.6], AggKind.last), closeTo(121.6, 1e-9)));
  test('round half away', () { expect(round1dp(421.23), closeTo(421.2, 1e-9)); expect(round1dp(421.25), closeTo(421.3, 1e-9)); expect(round1dp(418.0), closeTo(418.0, 1e-9)); });
}
