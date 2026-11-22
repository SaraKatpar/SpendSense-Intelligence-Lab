from pathlib import Path
import ast,os,sys,unittest
root=Path(__file__).resolve().parents[1]
for p in (root/'spendsense').rglob('*.py'):
    if '__pycache__' not in p.parts:ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
os.chdir(root/'spendsense');sys.path.insert(0,str(root/'spendsense'));sys.path.insert(0,str(root/'spendsense/tests'))
suite=unittest.TestSuite()
for pattern in ('test_core.py','test_advice_guard.py','test_accounting_p0.py'):
    suite.addTests(unittest.defaultTestLoader.discover(str(root/'spendsense/tests'),pattern=pattern))
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
