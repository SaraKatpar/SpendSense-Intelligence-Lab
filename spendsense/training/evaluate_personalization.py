"""Real chronological correction curves; never opens the sealed benchmark."""
import hashlib,json,sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import joblib,numpy as np,pandas as pd
from app.personalization import corrected_prediction,SIMILARITY_THRESHOLD
from training.category_baseline import build
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'eval/personalization_v1'
CACHE=ROOT.parent/'work/category_benchmark_v1'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    lock=json.loads((ROOT/'eval/category_benchmark_v1/split_lock.json').read_text())
    path=CACHE/'development.csv'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==lock['development_sha256']
    plan={'timestamp':datetime.now(ZoneInfo('Asia/Karachi')).isoformat(),'similarity_threshold':SIMILARITY_THRESHOLD,
        'budgets_per_history':[0,5,10,20,40,80,160],
        'protocol':'Global TF-IDF+LR fits earliest train partition only. First N global errors from chronological correction partition are supplied as publisher-label corrections. Evaluate identical later development rows at every N; no later evaluation labels enter memory. Budgets cap at available feedback. Sealed benchmark is never read.',
        'selection':'Fixed baseline and personal similarity gate before measuring curves; no selection by curve accuracy.',
        'label_limit':'Publisher categories and existing mapping are reference labels, not independently verified user corrections. Two histories, no claim of a student cohort.'}
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    frame=pd.read_csv(path,keep_default_na=False).sort_values(['date','source','row_id'])
    train=frame.loc[frame.partition.eq('train')]
    model=build().fit(train.normalized,train.category)
    joblib.dump(model,OUT/'global_development_baseline.joblib')
    results=[];predictions=[];correction_rows=[]
    for source,rows in frame.groupby('source'):
        feedback=rows.loc[rows.partition.eq('correction')].copy()
        evaluation=rows.loc[rows.partition.eq('curve_evaluation')].copy()
        feedback['global_prediction']=model.predict(feedback.normalized)
        errors=feedback.loc[feedback.category.ne(feedback.global_prediction)].copy()
        correction_rows.extend(errors.to_dict('records'))
        global_pred=model.predict(evaluation.normalized)
        for budget in plan['budgets_per_history']:
            selected=errors.head(budget)
            memory=selected[['description','category']].to_dict('records')
            personal=[corrected_prediction(text,(pred,0.),memory)[0] for text,pred in zip(evaluation.description,global_pred)]
            actual=evaluation.category.to_numpy()
            results.append({'source':source,'requested_corrections':budget,'actual_corrections':len(selected),
                'evaluation_rows':len(evaluation),'global_accuracy':float(np.mean(global_pred==actual)),
                'personalized_accuracy':float(np.mean(np.array(personal)==actual)),
                'overrides':int(np.sum(np.array(personal)!=global_pred)),
                'global_correct':int(np.sum(global_pred==actual)),'personalized_correct':int(np.sum(np.array(personal)==actual))})
            for row,g,p in zip(evaluation.to_dict('records'),global_pred,personal):
                predictions.append({'row_id':row['row_id'],'source':source,'date':row['date'],'truth':row['category'],
                    'budget':budget,'global_prediction':g,'personalized_prediction':p})
    metrics=pd.DataFrame(results);metrics.to_csv(OUT/'learning_curve.csv',index=False)
    pd.DataFrame(predictions).to_csv(OUT/'predictions.csv',index=False)
    pd.DataFrame(correction_rows).to_csv(OUT/'chronological_correction_pool.csv',index=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for ax,(source,rows) in zip(axes,metrics.groupby('source')):
        rows=rows.drop_duplicates('actual_corrections')
        ax.plot(rows.actual_corrections,rows.global_accuracy,'--',label='Global TF-IDF + LR')
        ax.plot(rows.actual_corrections,rows.personalized_accuracy,'o-',label='Per-user corrections')
        ax.set(title=source,xlabel='Earlier real-label corrections',ylabel='Later accuracy',ylim=(0,1));ax.legend()
    fig.savefig(OUT/'learning_curve.png',dpi=160)
    (OUT/'metrics.json').write_text(json.dumps({'results':results,'sealed_benchmark_read':False,
        'distinct_reference_histories':2,'global_training_rows':len(train),'similarity_threshold':SIMILARITY_THRESHOLD},indent=2),encoding='utf-8')
    print(metrics.to_string(index=False))


if __name__=='__main__':main()
