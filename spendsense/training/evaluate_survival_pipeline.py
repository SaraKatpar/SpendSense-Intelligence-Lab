"""Real-history recursive totals + conditional balance errors; no invented cash.

This is explicitly partial validation: source records lack actual balances,
essential-cost budgets, scheduled commitments and exhaustion outcomes.
"""
import hashlib,json,sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np,pandas as pd,torch
from training.train import fit_network
from training.real_source_policy import require_real_csv
from ml import SpendingLSTM,daily_matrix,forecast_days
from survival import hybrid_daily_costs,OPTIONAL
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'eval/survival_pipeline_v1'
MODELS=ROOT/'models/survival_research_v1'
torch.set_num_threads(2)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')


def main():
    OUT.mkdir(parents=True,exist_ok=True);MODELS.mkdir(parents=True,exist_ok=True)
    if (OUT/'evaluation_ledger.json').exists():raise RuntimeError('Research evaluation already completed/started; use saved predictions, never retune from outcomes.')
    plan={'timestamp':datetime.now(ZoneInfo('Asia/Karachi')).isoformat(),'seed':20261120,
        'history_split':'First 80% of each source calendar span for fitting; final 20% for nonoverlapping complete 14-day rolling origins. Fixed model weights; no within-horizon future observations.',
        'model':'From-scratch 32-hidden-unit LSTM, lookback14, all9 category outputs, 10epochs Adam lr.003 batch64, train-only mean scaling with floor1; recursive nonnegative predictions as existing app.',
        'hybrid':'Same hybrid_daily_costs composition as app: essential input plus LSTM optional categories plus dated dues once. Research essential proxy is preceding30-calendar-day mean Food+Groceries+Transport; no observed future schedule is available, so dues are unspecified/omitted, not asserted absent.',
        'comparators':['7day_mean_all_categories','lstm_all_categories','hybrid_proxy_lstm','hybrid_proxy_7day'],
        'targets':'Recorded daily expense totals; cumulative expense error implies a CONDITIONAL final-balance error only if true initial cash and future income are shared. No initial cash or income is fabricated.',
        'exhaustion_date':'Not estimable: no verified opening balances or actual exhaustion outcomes. Berka cannot be substituted into a daily LSTM.',
        'missing_dates':'Calendar slots with no recorded expenses have recorded total0; this does not prove zero actual spending or complete capture.',
        'selection':'Fixed before fitting, no tuning or test-driven clipping; currencies never pooled; research-only artifacts.'}
    write(OUT/'plan.json',plan)
    models={};manifest={};frames={};matrices={}
    for i,(source,name) in enumerate([('household','data/household_clean.csv'),('personal','data/kaggle/personal_reference_clean.csv')]):
        path=require_real_csv(ROOT/name);frame=pd.read_csv(path,keep_default_na=False);frame.date=pd.to_datetime(frame.date)
        assert frame.currency.nunique()==1
        matrix=daily_matrix(frame);cut=int(len(matrix)*.8);values=matrix.to_numpy(dtype=np.float32)
        scale=np.maximum(values[:cut].mean(axis=0),1)
        x=np.array([values[j-14:j]/scale for j in range(14,cut)],dtype=np.float32)
        y=np.array([values[j]/scale for j in range(14,cut)],dtype=np.float32)
        torch.manual_seed(20261120+i)
        model=fit_network(SpendingLSTM(),x,y,10)
        folder=MODELS/source;folder.mkdir(parents=True,exist_ok=True)
        torch.save({'state':model.state_dict(),'scale':scale.tolist(),'lookback':14},folder/'forecast.pt')
        manifest[source]={'source':name,'source_sha256':sha(path),'unit':str(frame.currency.iloc[0]),
            'calendar_days':len(matrix),'training_days':cut,'training_end':str(matrix.index[cut-1].date()),
            'evaluation_start':str(matrix.index[cut].date()),'model_sha256':sha(folder/'forecast.pt'),
            'no_recorded_expense_calendar_days':int(matrix.sum(axis=1).eq(0).sum()),
            'model_path':str(folder.relative_to(ROOT)),'research_only':True}
        frames[source]=frame;matrices[source]=matrix;models[source]=folder
        print(source,'development-only model fitted',flush=True)
    write(OUT/'configuration_lock.json',manifest)
    write(OUT/'evaluation_ledger.json',{'status':'started','configuration_lock_sha256':sha(OUT/'configuration_lock.json'),'passes':1})
    records=[];windows=[]
    obligations=pd.DataFrame(columns=['paid','due','amount','category'])
    for source,matrix in matrices.items():
        frame=frames[source];cut=manifest[source]['training_days']
        for offset in range(cut,len(matrix)-13,14):
            origin=matrix.index[offset];actual=matrix.iloc[offset:offset+14].sum(axis=1).to_numpy()
            past=frame.loc[frame.date.lt(origin)].copy()
            predicted=forecast_days(past,origin,14,models[source])
            dates=predicted.index
            history=matrix.iloc[:offset]
            essential=float(history[['Food','Groceries','Transport']].tail(30).sum(axis=1).mean())
            optional_baseline=float(history[OPTIONAL].tail(7).sum(axis=1).mean())
            forecasts={'7day_mean_all_categories':np.repeat(float(history.tail(7).sum(axis=1).mean()),14),
                'lstm_all_categories':predicted.sum(axis=1).to_numpy(),
                'hybrid_proxy_lstm':hybrid_daily_costs(essential,dates,obligations,predicted[OPTIONAL].sum(axis=1)).to_numpy(),
                'hybrid_proxy_7day':hybrid_daily_costs(essential,dates,obligations,[optional_baseline]*14).to_numpy()}
            for model,forecast in forecasts.items():
                error=forecast-actual
                windows.append({'source':source,'unit':manifest[source]['unit'],'model':model,'origin':str(origin.date()),
                    'horizon':14,'actual_recorded_total':float(actual.sum()),'predicted_total':float(forecast.sum()),
                    'conditional_final_balance_error':float(-error.sum()),
                    'input_essential_proxy':essential,'known_future_dues':'unavailable','actual_exhaustion_date':None})
                for day,truth,pred in zip(dates,actual,forecast):
                    records.append({'source':source,'unit':manifest[source]['unit'],'model':model,'origin':str(origin.date()),
                        'date':str(day.date()),'actual_recorded_daily_total':float(truth),'prediction':float(pred)})
    daily=pd.DataFrame(records);window=pd.DataFrame(windows)
    daily.to_csv(OUT/'daily_predictions.csv',index=False);window.to_csv(OUT/'window_predictions.csv',index=False)
    results=[]
    for (source,model),group in daily.groupby(['source','model']):
        error=group.prediction-group.actual_recorded_daily_total
        balances=window.loc[window.source.eq(source)&window.model.eq(model),'conditional_final_balance_error']
        results.append({'source':source,'unit':manifest[source]['unit'],'model':model,'windows':len(balances),'daily_rows':len(group),
            'daily_total_mae':float(error.abs().mean()),'daily_total_rmse':float(np.sqrt((error**2).mean())),
            'conditional_final_balance_mae':float(balances.abs().mean()),'conditional_final_balance_rmse':float(np.sqrt((balances**2).mean())),
            'daily_bias':float(error.mean()),'exhaustion_date_error':None,'exhaustion_date_reason':'No verified opening balances/actual exhaustion outcomes.'})
    metrics=pd.DataFrame(results);metrics.to_csv(OUT/'metrics.csv',index=False)
    write(OUT/'metrics.json',{'results':results,'absolute_final_balance_validated':False,
        'exhaustion_date_validated':False,'full_hybrid_survival_validated':False,'currencies_pooled':False})
    write(OUT/'evaluation_ledger.json',{'status':'complete','configuration_lock_sha256':sha(OUT/'configuration_lock.json'),
        'passes':1,'daily_predictions_sha256':sha(OUT/'daily_predictions.csv'),'window_predictions_sha256':sha(OUT/'window_predictions.csv')})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
    for ax,(source,rows) in zip(axes,metrics.groupby('source')):
        rows.set_index('model')[['daily_total_mae','conditional_final_balance_mae']].plot.bar(ax=ax,rot=25)
        ax.set(title=source+' · '+manifest[source]['unit'],ylabel='Recorded-flow error, source units')
    fig.savefig(OUT/'errors.png',dpi=160)
    text='# Step 6: partial survival-pipeline evaluation\n\n'
    text+='**Full end-to-end survival validation is not established.** Neither source contains verified opening cash, essential-budget inputs, forward due schedules or actual exhaustion dates. No cash balance, allowance or exhaustion label is invented. Berka is not used; its completed models and frozen test remain untouched.\n\n'
    text+='Two separate from-scratch LSTMs use real historical recorded expenses, train-only scaling and fixed recursive 14-day rolling-origin predictions. No observation inside a forecast horizon is fed back, and the fixed fitted models are never updated on the final period. Amounts stay in INR or unspecified personal-source units, without pooling or PKR conversion. Existing app composition is shared through hybrid_daily_costs, but missing real user inputs force a documented past-only essential-cost proxy and no known future dues. An omitted due schedule means unavailable information, not verified zero obligations. Bills/Health/Education are not fully covered by this proxy.\n\n'
    text+='| Source | Model | 14-day windows | Daily MAE | Daily RMSE | Conditional final-balance MAE | Conditional RMSE |\n|---|---|---:|---:|---:|---:|---:|\n'
    for row in results:text+=f"| {row['source']} | {row['model']} | {row['windows']} | {row['daily_total_mae']:.2f} | {row['daily_total_rmse']:.2f} | {row['conditional_final_balance_mae']:.2f} | {row['conditional_final_balance_rmse']:.2f} |\n"
    text+='\n![Recorded-flow errors](errors.png)\n\n'
    text+='The conditional final-balance error is the negative cumulative spending error over 14 days. It equals a balance prediction error **only conditional on the same true initial balance and future income being supplied to both trajectories**. It is not an evaluated absolute account balance. Exhaustion-date error is **not estimable**, because its ground truth and starting cash are absent. No censoring date is silently treated as "never exhausted".\n\n'
    text+='**Done:** recursive daily-total recorded-flow errors, cumulative/conditional balance errors, statistical baseline comparison, shared hybrid cost composition, train-only scaling and saved per-day/per-window predictions on two real reference histories. **Failed to validate:** absolute final balances, actual exhaustion timing, the true shield with real essential budgets/dues, and a reliable student survival predictor. The hybrid proxy must not be presented as a validated survival model.\n\n'
    text+='**Still unvalidated:** true spending on unlogged days (a calendar slot with no record means recorded total zero, not proof of no spending), inherited category/transfer treatment, reference collection authenticity, future income uncertainty and independent people/student performance. Nonoverlapping windows from one household and one personal history are not independent users. A consented prospective dataset needs timestamped verified opening cash, income/allowance dates, budgets, commitments, complete daily expenses and observed balance/exhaustion outcomes before those claims can be tested.\n\n'
    text+='Artifacts: plan.json, configuration_lock.json, metrics.csv/json, daily_predictions.csv, window_predictions.csv. Evaluation is locked; do not retune using these outcomes. New research models remain outside the app.\n'
    (OUT/'REPORT.md').write_text(text,encoding='utf-8')
    print(metrics.to_string(index=False),flush=True)


if __name__=='__main__':main()
