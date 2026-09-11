import 'package:flutter_test/flutter_test.dart';
import 'package:ratatosk/main.dart';

void main() {
  testWidgets('Ratatosk smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const RatatoskApp());
    expect(find.text('Ratatosk'), findsWidgets);
  });
}
