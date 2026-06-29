import 'dart:convert';

void main() {
  String? serverSha256 = 'matching_sha256_hash';
  final body = jsonEncode({
    if (serverSha256 != null) 'server_sha256': serverSha256,
    'stored': true,
  });
  print(body);
}
