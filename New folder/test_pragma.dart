import 'package:sqlite3/sqlite3.dart';
void main() {
  final db = sqlite3.openInMemory();
  try {
    db.execute("PRAGMA key = ?", ['my_passphrase']);
    print("Success");
  } catch (e) {
    print("Error: $e");
  }
}
