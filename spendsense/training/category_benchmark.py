"""Common newly model-untouched categorizer comparison; no Berka inputs.

All candidates rebuild from the same development rows. Hyperparameters are fixed
before fitting. Test opens only after model/configuration hashes lock. Exclusive
evaluation ledger prevents reruns; reports can read saved predictions instead.
"""
import gc,hashlib,json,sys,time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import joblib,numpy as np,pandas as pd,torch
from sklearn.metrics import accuracy_score,classification_report,confusion_matrix,f1_score
from transformers import AutoTokenizer,AutoModelForSequenceClassification
from storage import CATEGORIES
from training.category_baseline import build
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'eval/category_benchmark_v1'
CACHE=ROOT.parent/'work/category_benchmark_v1'
MODELS=ROOT/'models/category_benchmark_v1'
BASE=ROOT/'models/base-distilbert'
SEED=20261120
torch.set_num_threads(3)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False),encoding='utf-8')
def now():return datetime.now(ZoneInfo('Asia/Karachi')).isoformat()


def fresh_model():
    torch.manual_seed(SEED)
    return AutoModelForSequenceClassification.from_pretrained(BASE,local_files_only=True,
        num_labels=len(CATEGORIES),id2label=dict(enumerate(CATEGORIES)),label2id={c:i for i,c in enumerate(CATEGORIES)})


def class_weights(labels):
    counts=np.bincount(labels,minlength=len(CATEGORIES))
    values=np.sqrt(len(labels)/np.maximum(counts,1))
    return torch.tensor(values/values.mean(),dtype=torch.float32)


def fit_distil(name,frame,tokenizer,spec):
    folder=MODELS/name;folder.mkdir(parents=True,exist_ok=True)
    model=fresh_model()
    for parameter in model.distilbert.parameters():parameter.requires_grad=False
    if spec['last_blocks']:
        for layer in model.distilbert.transformer.layer[-spec['last_blocks']:]:
            for parameter in layer.parameters():parameter.requires_grad=True
    labels=torch.tensor([CATEGORIES.index(c) for c in frame.category],dtype=torch.long)
    encoded=tokenizer(frame.normalized.tolist(),padding=True,truncation=True,max_length=48,return_tensors='pt')
    loss_fn=torch.nn.CrossEntropyLoss(weight=class_weights(labels.numpy()))
    optimizer=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=spec['lr'])
    losses=[]
    if spec['last_blocks']==0:
        model.eval();features=[]
        with torch.no_grad():
            for start in range(0,len(frame),16):
                features.append(model.distilbert(**{k:v[start:start+16] for k,v in encoded.items()}).last_hidden_state[:,0].detach())
        features=torch.cat(features)
        for epoch in range(spec['epochs']):
            model.train();values=[]
            generator=torch.Generator().manual_seed(SEED+epoch)
            for indexes in torch.randperm(len(frame),generator=generator).split(spec['batch']):
                hidden=torch.relu(model.pre_classifier(features[indexes]))
                logits=model.classifier(model.dropout(hidden))
                loss=loss_fn(logits,labels[indexes]);optimizer.zero_grad();loss.backward();optimizer.step()
                values.append(float(loss.detach()))
            losses.append(float(np.mean(values)));print(name,'epoch',epoch+1,'loss',losses[-1],flush=True)
    else:
        for epoch in range(spec['epochs']):
            model.train();values=[]
            generator=torch.Generator().manual_seed(SEED+epoch)
            for indexes in torch.randperm(len(frame),generator=generator).split(spec['batch']):
                logits=model(**{k:v[indexes] for k,v in encoded.items()}).logits
                loss=loss_fn(logits,labels[indexes]);optimizer.zero_grad();loss.backward()
                torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],1.)
                optimizer.step();values.append(float(loss.detach()))
            losses.append(float(np.mean(values)));print(name,'epoch',epoch+1,'loss',losses[-1],flush=True)
    model.eval();model.save_pretrained(folder);tokenizer.save_pretrained(folder)
    write(folder/'training.json',{'spec':spec,'training_rows':len(frame),'training_loss':losses,
        'training_row_ids_sha256':hashlib.sha256('\n'.join(frame.row_id).encode()).hexdigest(),
        'test_rows_seen':0,'pretrained_backbone':str(BASE),'research_only':True})
    del model,optimizer;gc.collect()


def train():
    OUT.mkdir(parents=True,exist_ok=True);MODELS.mkdir(parents=True,exist_ok=True)
    if (OUT/'test_evaluation_ledger.json').exists():raise RuntimeError('Benchmark already scored. Do not retrain/retune on its result.')
    split=json.loads((OUT/'split_lock.json').read_text())
    assert sha(CACHE/'development.csv')==split['development_sha256']
    specs={'distilbert_head':{'last_blocks':0,'epochs':8,'batch':32,'lr':.001},
           'distilbert_last2':{'last_blocks':2,'epochs':3,'batch':8,'lr':.00002}}
    plan={'seed':SEED,'candidates':specs,'baseline':'Fixed training/category_baseline.py TF-IDF word1–2 + char3–5 + balanced LR C=1; all development rows.',
        'input':'Same normalized description and source rows for every model; labels fixed nine categories.',
        'selection':'No tuning or early stopping. Predetermined configs; train every candidate on all development rows.',
        'weighting':'DistilBERT square-root inverse train class frequency; LR balanced class weights.',
        'max_tokens':48,'base_weights_sha256':sha(BASE/'model.safetensors'),
        'split_lock_sha256':sha(OUT/'split_lock.json'),'development_sha256':split['development_sha256'],
        'untouched_claim':'Only newly rebuilt models are test-untouched. Public sources and old models were previously inspected; old weights cannot be used as independent candidates.',
        'deployment':False}
    if (OUT/'model_plan.json').exists():assert json.loads((OUT/'model_plan.json').read_text())==plan
    else:write(OUT/'model_plan.json',plan)
    frame=pd.read_csv(CACHE/'development.csv',keep_default_na=False).sort_values(['date','source','row_id']).reset_index(drop=True)
    started=time.time()
    if not (MODELS/'tfidf_lr.joblib').exists():
        baseline=build().fit(frame.normalized,frame.category)
        joblib.dump(baseline,MODELS/'tfidf_lr.joblib')
    tokenizer=AutoTokenizer.from_pretrained(BASE,local_files_only=True)
    for name,spec in specs.items():
        if (MODELS/name/'training.json').exists():
            assert json.loads((MODELS/name/'training.json').read_text())['spec']==spec
            print('Reuse completed development fit',name,flush=True)
        else:fit_distil(name,frame,tokenizer,spec)
    artifacts={str(p.relative_to(MODELS)):sha(p) for p in sorted(MODELS.rglob('*')) if p.is_file()}
    write(OUT/'configuration_lock.json',{'timestamp':now(),'model_plan_sha256':sha(OUT/'model_plan.json'),
        'artifacts':artifacts,'training_rows':len(frame),'training_seconds':time.time()-started,
        'test_predictions_generated':False,'candidate_names':['tfidf_lr',*specs],
        'development_training_row_ids':frame.row_id.tolist()})
    print('All models/configurations locked before test.',flush=True)


def score_once():
    lock=json.loads((OUT/'configuration_lock.json').read_text())
    assert sha(OUT/'model_plan.json')==lock['model_plan_sha256']
    for name,digest in lock['artifacts'].items():assert sha(MODELS/name)==digest
    split=json.loads((OUT/'split_lock.json').read_text())
    assert sha(CACHE/'sealed_test.csv')==split['sealed_test_sha256']
    ledger=OUT/'test_evaluation_ledger.json'
    with ledger.open('x',encoding='utf-8') as f:
        json.dump({'status':'started','timestamp':now(),'passes':1,'configuration_lock_sha256':sha(OUT/'configuration_lock.json')},f,indent=2)
    test=pd.read_csv(CACHE/'sealed_test.csv',keep_default_na=False)
    assert not set(test.row_id)&set(lock['development_training_row_ids'])
    predictions=test[['row_id','source','date','description','normalized','category']].copy()
    baseline=joblib.load(MODELS/'tfidf_lr.joblib')
    predictions['tfidf_lr']=baseline.predict(test.normalized)
    for name in ('distilbert_head','distilbert_last2'):
        tokenizer=AutoTokenizer.from_pretrained(MODELS/name,local_files_only=True)
        model=AutoModelForSequenceClassification.from_pretrained(MODELS/name,local_files_only=True).eval()
        result=[]
        with torch.no_grad():
            for start in range(0,len(test),16):
                encoded=tokenizer(test.normalized.iloc[start:start+16].tolist(),padding=True,truncation=True,max_length=48,return_tensors='pt')
                result.extend(CATEGORIES[int(i)] for i in model(**encoded).logits.argmax(-1))
        predictions[name]=result
        del model;gc.collect()
    predictions.to_csv(OUT/'test_predictions_ONCE.csv',index=False)
    write(ledger,{'status':'complete','timestamp':now(),'passes':1,
        'configuration_lock_sha256':sha(OUT/'configuration_lock.json'),
        'predictions_sha256':sha(OUT/'test_predictions_ONCE.csv'),'test_rows':len(test),
        'dataset_prediction_passes':{n:1 for n in lock['candidate_names']},
        'rule':'Do not refit/retune from test outcomes. Metrics read cached predictions.'})
    print('Shared benchmark predicted once for each locked model.',flush=True)


def report():
    frame=pd.read_csv(OUT/'test_predictions_ONCE.csv',keep_default_na=False)
    models=['tfidf_lr','distilbert_head','distilbert_last2']
    results={};rows=[]
    for name in models:
        results[name]={}
        for source,data in [('all',frame),*list(frame.groupby('source'))]:
            metrics={'rows':len(data),'accuracy':float(accuracy_score(data.category,data[name])),
                'macro_f1_fixed_9_classes':float(f1_score(data.category,data[name],labels=CATEGORIES,average='macro',zero_division=0)),
                'report':classification_report(data.category,data[name],labels=CATEGORIES,output_dict=True,zero_division=0)}
            results[name][source]=metrics
            rows.append({'model':name,'source':source,**{k:metrics[k] for k in ('rows','accuracy','macro_f1_fixed_9_classes')}})
        pd.DataFrame(confusion_matrix(frame.category,frame[name],labels=CATEGORIES),index=CATEGORIES,columns=CATEGORIES).to_csv(OUT/(name+'_confusion.csv'))
    write(OUT/'metrics.json',{'results':results,'same_test_rows_all_models':True,
        'test_rows':len(frame),'unique_test_descriptions':frame.normalized.nunique(),
        'test_label_counts':frame.category.value_counts().to_dict(),'deployment':False})
    pd.DataFrame(rows).to_csv(OUT/'metrics.csv',index=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    data=pd.DataFrame(rows).query("source=='all'")
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
    data.set_index('model')[['accuracy','macro_f1_fixed_9_classes']].plot.bar(ax=ax,rot=10)
    ax.set(ylim=(0,1),ylabel='Score',title=f'Same sealed future benchmark: {len(frame)} rows')
    fig.savefig(OUT/'shared_benchmark.png',dpi=160)
    text='# Step 5: shared categorizer benchmark\n\n'
    text+='All three candidates were rebuilt using the same 1,127 development rows and scored on the same sealed future rows. Older weights were excluded. Configurations locked before test; each model made one dataset prediction pass. These are newly model-untouched splits of previously inspected public sources, not newly collected data. No candidate is deployed.\n\n'
    text+='| Model | Source | Rows | Accuracy | Macro F1 (fixed 9 classes) |\n|---|---|---:|---:|---:|\n'
    for row in rows:text+=f"| {row['model']} | {row['source']} | {row['rows']} | {row['accuracy']:.4f} | {row['macro_f1_fixed_9_classes']:.4f} |\n"
    text+='\n![Shared benchmark](shared_benchmark.png)\n\n'
    text+='Split: per-source future final 20% of unique dates. Earlier rows sharing any held-out normalized description are purged, ensuring no normalized-description overlap. Training sees the remaining first 80%, including earlier correction/curve development partitions. The same preprocessing and rows apply to all models. Hyperparameters are predetermined; no test tuning, early stopping or automatic promotion. TF-IDF+LR is from scratch. DistilBERT uses the local original pretrained language backbone, with a fresh classification head: candidate A freezes its encoder, candidate B fine-tunes its last two blocks. This latest user-requested pretrained comparison supersedes the earlier blanket exclusion for this experiment only.\n\n'
    text+='Training configurations, source/split/model hashes and row IDs are saved. Per-source/per-class precision, recall, F1 and confusion matrices are included. Zero-support categories receive zero division=0 and are included in the fixed-nine-class macro average, making the convention explicit. No label is silently removed for low support. Repeated test transactions are not independent people; unique description count and source counts are reported in metrics.json.\n\n'
    text+='**Done:** common locked benchmark, identical row IDs, genuinely rebuilt candidate weights, baseline, per-source/per-class results and saved predictions. **Still unvalidated:** deployment benefit, local student language, many-user generalization, label correctness, complete logging, and a newly collected independent population. Description purging removes many recurring merchants and disproportionately shrinks the personal development data; this is a novelty-oriented benchmark with selection bias. Accuracy on common recurring text may differ. The test is now consumed and must not be used to tune another candidate or threshold. No superiority beyond these descriptive benchmark rows is established.\n\n'
    text+='See metrics.csv, metrics.json, *_confusion.csv, split_lock.json, model_plan.json, configuration_lock.json and test_evaluation_ledger.json. Regenerate reports only with `python training/category_benchmark.py report`. Never rerun its score command or the frozen Berka evaluator.\n'
    (OUT/'REPORT.md').write_text(text,encoding='utf-8')
    print(pd.DataFrame(rows).to_string(index=False),flush=True)


if __name__=='__main__':
    {'train':train,'score':score_once,'report':report}[sys.argv[1]]()
