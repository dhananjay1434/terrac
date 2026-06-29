import 'package:sqlite3/sqlite3.dart';

void main() {
  final db = sqlite3.openInMemory();
  try {
    final result = db.select('SELECT quote(?);', ['my_passphrase']);
    final quotedPassphrase = result.first[0] as String;
    print('Quoted: $quotedPassphrase');
    db.execute('PRAGMA key = $quotedPassphrase;');
    print('Success');
  } catch (e) {
    print('Error: $e');
  }
}
