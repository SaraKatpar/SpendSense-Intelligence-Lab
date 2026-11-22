"""Evaluate receipt extraction against SROIE-style company/date/total JSON files.

Usage: python training/evaluate_receipts.py --images data/sroie/images --labels data/sroie/entities
Images and JSON annotations must share a filename stem. Never use evaluation
labels to extract fields. Reports exact normalized field matches, not OCR accuracy.
"""
import argparse
import json
import re
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from receipt_ocr import scan,extract_fields

def norm(value):return re.sub(r'[^a-z0-9]','',str(value).lower())

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--images',required=True);parser.add_argument('--labels',required=True)
    parser.add_argument('--output',default='models/ocr_evaluation.json')
    args=parser.parse_args();cases=[]
    for path in sorted(Path(args.images).iterdir()):
        annotation=Path(args.labels)/(path.stem+'.json')
        if not annotation.exists():annotation=annotation.with_suffix('.txt')
        if path.suffix.lower() not in ['.jpg','.png','.jpeg'] or not annotation.exists():continue
        expected=json.loads(annotation.read_text(encoding='utf-8'))
        actual=scan(path.read_bytes())
        parsed_date=extract_fields(str(expected.get('date','')))['date']
        try:total=float(str(expected.get('total','')).replace(',',''))
        except ValueError:total=None
        cases.append({'file':path.name,'merchant_match':norm(actual['merchant'])==norm(expected.get('company','')),
                      'date_match':actual['date']==parsed_date if parsed_date else False,
                      'total_match':abs(actual['amount']-total)<.01 if total is not None else False,
                      'extracted':{**actual,'date':str(actual['date'])}})
    if not cases:raise ValueError('No matching receipt images and SROIE entity annotations found.')
    report={'receipts':len(cases),'evaluation_note':'Report sample size and split before any accuracy claim; a small sample is not the official benchmark protocol',
            'metrics':{k:sum(c[k] for c in cases)/len(cases) for k in ['merchant_match','date_match','total_match']},'cases':cases}
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2))
    print(report['metrics'])

if __name__=='__main__':main()
