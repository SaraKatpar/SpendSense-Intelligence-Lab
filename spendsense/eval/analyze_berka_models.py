"""Metrics/CIs/bias/plots from the saved single-pass predictions; no fitting/scoring."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import average_precision_score
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'training'))
from berka_experiment import OUT,CACHE,SEED,read,save,sha,verify_protocol,clustered_regression,weights


def interval(values):
    values=np.asarray(values,dtype=float);valid=values[np.isfinite(values)]
    missing=int(len(values)-len(valid));unreliable=missing>len(values)*.05
    return {'ci95':np.quantile(valid,[.025,.975]).tolist() if len(valid) and not unreliable else None,
        'valid_draws':len(valid),'undefined_draws':missing,'unreliable_or_unavailable':bool(unreliable or not len(valid))}


def binary_bootstrap(frame,probability):
    y=frame.low_balance_event_B.astype(int).to_numpy();p=np.asarray(probability)
    accounts=np.sort(frame.account_id.unique());inverse=pd.Index(accounts).get_indexer(frame.account_id)
    n=len(accounts);sizes=np.bincount(inverse);row_weight=1/sizes[inverse]
    draws=np.random.default_rng(SEED).multinomial(n,np.full(n,1/n),size=2000)
    positive_counts=np.bincount(inverse,weights=y,minlength=n)
    negative_counts=sizes-positive_counts
    zero_positive=(draws@positive_counts)==0;zero_negative=(draws@negative_counts)==0
    predicted=p>=.5
    brier_by_account=pd.Series((p-y)**2).groupby(frame.account_id.to_numpy()).mean().reindex(accounts).to_numpy()
    briers=draws@brier_by_account/n
    aps=np.full(2000,np.nan);precisions=np.full(2000,np.nan);recalls=np.full(2000,np.nan)
    raw=[]
    for i,draw in enumerate(draws):
        w=draw[inverse]*row_weight
        if not zero_positive[i] and not zero_negative[i]:aps[i]=average_precision_score(y,p,sample_weight=w)
        tp=float(w[(y==1)&predicted].sum());fp=float(w[(y==0)&predicted].sum());fn=float(w[(y==1)&~predicted].sum())
        if tp+fp>0:precisions[i]=tp/(tp+fp)
        if tp+fn>0:recalls[i]=tp/(tp+fn)
        raw.append({'draw':i,'zero_positive':bool(zero_positive[i]),'zero_negative':bool(zero_negative[i]),
            'brier':briers[i],'average_precision':aps[i],'precision_at_0_5':precisions[i],'recall_at_0_5':recalls[i]})
    tp=float(row_weight[(y==1)&predicted].sum());fp=float(row_weight[(y==0)&predicted].sum());fn=float(row_weight[(y==1)&~predicted].sum())
    result={'status':'EXPLORATORY; descriptive values only, no performance claim',
        'accounts':n,'months':len(frame),'positive_months':int(y.sum()),'positive_accounts':int(frame.loc[y==1,'account_id'].nunique()),
        'account_weighted_average_precision':float(average_precision_score(y,p,sample_weight=row_weight)),
        'account_macro_brier':float(brier_by_account.mean()),'account_weighted_precision_at_0_5':tp/(tp+fp) if tp+fp else None,
        'account_weighted_recall_at_0_5':tp/(tp+fn) if tp+fn else None,
        'raw_confusion_at_0_5':{'tn':int(((y==0)&~predicted).sum()),'fp':int(((y==0)&predicted).sum()),'fn':int(((y==1)&~predicted).sum()),'tp':int(((y==1)&predicted).sum())},
        'bootstrap_draws':2000,'zero_positive_draws':int(zero_positive.sum()),'zero_negative_draws':int(zero_negative.sum()),
        'intervals':{'average_precision':interval(aps),'brier':interval(briers),'precision_at_0_5':interval(precisions),'recall_at_0_5':interval(recalls)},
        'handling':'Single-class draws leave AP undefined. Recall is undefined without actual positives; precision is undefined without predicted positives. Brier remains defined. No forced-zero AP, no resampling until positives appear. Intervals with >5% undefined draws are not published.',
        'average_precision_definition':'Account-weighted, non-interpolated average precision; not trapezoidal PR area or a mean over mostly single-class accounts.'}
    return result,pd.DataFrame(raw)


def bias_report():
    data=pd.read_csv(CACHE/'selection_bias.csv')
    data['first']=pd.to_datetime(data['first']);data['last']=pd.to_datetime(data['last'])
    summaries=[];metrics=['full_span_months','full_month_debit_mean','full_month_ledger_mean','active_debit_fraction','negative_snapshot_fraction','median_month_end_ratio_all_source']
    for partition in ('all','train','validation','test'):
        subset=data if partition=='all' else data[data.partition.eq(partition)]
        for status in (True,False):
            group=subset[subset.scorable.eq(status)]
            record={'partition':partition,'status':'scorable' if status else 'unscorable','accounts':len(group),
                'first_observation_median':str(group['first'].median().date()) if len(group) else None,
                'ever_negative_accounts':int(group.ever_negative.sum()),'unscorable_reasons':group.unscorable_reason.value_counts().astype(int).to_dict()}
            for col in metrics:
                values=group[col].dropna()
                record[col]={'median':float(values.median()),'q25':float(values.quantile(.25)),'q75':float(values.quantile(.75)),'mean':float(values.mean())} if len(values) else None
            summaries.append(record)
    differences=[]
    for part in ('all','train','validation','test'):
        subset=data if part=='all' else data[data.partition.eq(part)]
        a=subset[subset.scorable];b=subset[~subset.scorable]
        for col in metrics:
            first=a[col].dropna();second=b[col].dropna()
            scale=np.sqrt((first.var()+second.var())/2) if len(first)>1 and len(second)>1 else np.nan
            differences.append({'partition':part,'metric':col,'standardized_mean_difference_scorable_minus_unscorable':float((first.mean()-second.mean())/scale) if np.isfinite(scale) and scale>0 else None})
    data.to_csv(OUT/'account_selection_bias.csv',index=False)
    save(OUT/'selection_bias.json',{'scope':'Descriptive entire-source account summaries, computed after the configuration lock; not predictors, tuning objectives or causal comparisons.',
        'summaries':summaries,'standardized_mean_differences':differences,
        'interpretation':'Later first observations and shorter recorded histories can exclude accounts under the historical cutoffs. The 193 unscorable accounts cannot receive invented errors. Whole-source balance behavior includes observations outside the assigned modeling years and is descriptive only. Test has no unscorable comparator.'})
    return data,summaries


def plot_regression(metrics,maes,rmses,names,all_available=False):
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for axis,key in zip(axes,('mae','rmse')):
        values=[metrics[name][key] for name in names];bounds=np.array([metrics[name][key+'_ci95'] for name in names])
        axis.errorbar(values,np.arange(len(names)),xerr=[np.array(values)-bounds[:,0],bounds[:,1]-np.array(values)],fmt='o',capsize=4,color='#286455')
        axis.set_yticks(np.arange(len(names)),[name.replace('_',' ') for name in names]);axis.invert_yaxis();axis.set_xlabel(key.upper()+' (ratio units)');axis.grid(axis='x',alpha=.2)
    title='Primary regression — all available exact targets (coverage differs)' if all_available else 'Paired comparison — common exact-target cases'
    fig.suptitle(title+'\n95% account-cluster bootstrap intervals, 2,000 draws')
    filename='regression_all_available_bootstrap' if all_available else 'regression_bootstrap'
    fig.tight_layout();fig.savefig(OUT/'plots'/(filename+'.png'),dpi=180);fig.savefig(OUT/'plots'/(filename+'.svg'));plt.close(fig)


def plots_other(test,lock,bias):
    best=lock['development_preference']
    exact=test[test.month_end_ratio.notna()]
    fig,ax=plt.subplots(figsize=(6,5));ax.scatter(exact.month_end_ratio,exact[best],s=12,alpha=.35,color='#286455')
    low=min(exact.month_end_ratio.min(),exact[best].min());high=max(exact.month_end_ratio.max(),exact[best].max())
    ax.plot([low,high],[low,high],color='#9d6650',linestyle='--');ax.set_xlabel('Observed month-end ratio');ax.set_ylabel('Predicted ratio');ax.set_title('Development-selected '+best+' — frozen test\nAll exact targets; no clipping');fig.tight_layout();fig.savefig(OUT/'plots'/'regression_predictions.png',dpi=180);plt.close(fig)
    counts=bias.groupby(['partition','scorable']).size().unstack(fill_value=0).reindex(['train','validation','test'])
    fig,ax=plt.subplots(figsize=(7,4));counts.rename(columns={False:'Unscorable',True:'Scorable'}).plot.bar(stacked=True,ax=ax,color=['#c98a68','#448879'])
    ax.set_ylabel('Accounts');ax.set_xlabel('Frozen partition');ax.set_title('Coverage: 639 scorable / 193 unscorable');ax.tick_params(axis='x',rotation=0);fig.tight_layout();fig.savefig(OUT/'plots'/'account_coverage.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    for axis,col,title in zip(axes,['full_span_months','full_month_debit_mean','median_month_end_ratio_all_source'],['Observed full months','Eligible debits / month','Median closing/outflow ratio']):
        axis.boxplot([bias.loc[bias.scorable,col].dropna(),bias.loc[~bias.scorable,col].dropna()],tick_labels=['Scorable','Unscorable'],showfliers=False)
        axis.set_title(title);axis.grid(axis='y',alpha=.2)
    fig.suptitle('Selection-bias diagnostics — whole-source descriptive summaries');fig.tight_layout();fig.savefig(OUT/'plots'/'selection_bias.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4));name='logistic_regularized'
    for value,label in [(False,'No observed B event'),(True,'Observed B event')]:
        ax.hist(test.loc[test.low_balance_event_B.eq(value),name],bins=15,alpha=.55,label=label)
    ax.axvline(.5,color='black',linestyle='--',label='Frozen cutoff 0.5');ax.set_yscale('log');ax.set_xlabel('Predicted probability');ax.set_ylabel('Account-months (log count)');ax.set_title('EXPLORATORY B — 7 positive months / 4 accounts\nDescriptive only; no performance claim');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(OUT/'plots'/'exploratory_binary_scores.png',dpi=180);plt.close(fig)


def main():
    verify_protocol();(OUT/'plots').mkdir(exist_ok=True)
    ledger=read(OUT/'test_evaluation_ledger.json');lock=read(OUT/'configuration_lock.json')
    assert ledger['status']=='complete' and ledger['evaluation_passes']==1
    assert sha(OUT/'test_predictions_ONCE.csv')==ledger['saved_predictions_sha256']
    assert sha(OUT/'configuration_lock.json')==ledger['configuration_lock_sha256']
    test=pd.read_csv(OUT/'test_predictions_ONCE.csv')
    reg_names=['persistence','pace']+[name for name,v in lock['models'].items() if v['role']=='regression']
    exact=test[test.month_end_ratio.notna()]
    common=exact.dropna(subset=reg_names)
    metrics,maes,rmses,names=clustered_regression(common,{name:common[name].to_numpy() for name in reg_names})
    records=[]
    for name,m in metrics.items():records.append({'model':name,**{k:v for k,v in m.items() if not isinstance(v,list)},'mae_ci_low':m['mae_ci95'][0],'mae_ci_high':m['mae_ci95'][1],'rmse_ci_low':m['rmse_ci95'][0],'rmse_ci_high':m['rmse_ci95'][1]})
    pd.DataFrame(records).to_csv(OUT/'regression_test_metrics.csv',index=False)
    pd.DataFrame({name+'_mae':maes[:,i] for i,name in enumerate(names)}|{name+'_rmse':rmses[:,i] for i,name in enumerate(names)}).to_csv(OUT/'regression_bootstrap_draws.csv',index_label='draw')
    all_available={}
    for name in reg_names:
        subset=exact[exact[name].notna()]
        value,_,_,_=clustered_regression(subset,{name:subset[name].to_numpy()});all_available[name]=value[name]
    available_rows=[]
    for name,m in all_available.items():available_rows.append({'model':name,**{k:v for k,v in m.items() if not isinstance(v,list)},
        'mae_ci_low':m['mae_ci95'][0],'mae_ci_high':m['mae_ci95'][1],'rmse_ci_low':m['rmse_ci95'][0],'rmse_ci_high':m['rmse_ci95'][1]})
    pd.DataFrame(available_rows).to_csv(OUT/'regression_all_available_metrics.csv',index=False)
    differences={}
    selected=lock['development_preference'];position=names.index(selected)
    for baseline in ('persistence','pace'):
        idx=names.index(baseline);differences[baseline]={'mae_difference':metrics[selected]['mae']-metrics[baseline]['mae'],
            'mae_difference_ci95':np.quantile(maes[:,position]-maes[:,idx],[.025,.975]).tolist(),
            'rmse_difference':metrics[selected]['rmse']-metrics[baseline]['rmse'],
            'rmse_difference_ci95':np.quantile(rmses[:,position]-rmses[:,idx],[.025,.975]).tolist()}
    save(OUT/'regression_results.json',{'primary_all_available_cases':all_available,'paired_common_cases':metrics,'all_available_cases':all_available,
        'development_selected_pipeline':selected,'paired_differences_selected_minus_baseline':differences,
        'bootstrap_draws':2000,'unit':'account cluster','selection_after_test':False,'target':'month-end balance/reference outflow ratio; different from earlier-month B event'})
    binary={}
    for name,v in lock['models'].items():
        if v['role']!='exploratory_binary':continue
        result,draws=binary_bootstrap(test,test[name].to_numpy());binary[name]=result
        draws.to_csv(OUT/(name+'_bootstrap_draws.csv'),index=False)
    save(OUT/'exploratory_binary_results.json',binary)
    warning={}
    for name in reg_names:
        subset=exact[exact[name].notna()];truth=subset.month_end_ratio.lt(.05);prediction=subset[name].lt(.05)
        warning[name]={'definition':'Month-end ratio warning only; NOT binary event B','months':len(subset),'true_month_end_low_months':int(truth.sum()),
            'tp':int((truth&prediction).sum()),'fp':int((~truth&prediction).sum()),'fn':int((truth&~prediction).sum()),'tn':int((~truth&~prediction).sum())}
    save(OUT/'derived_month_end_warning.json',warning)
    diagnostic=exact.copy();diagnostic['selected_abs_error']=(diagnostic[selected]-diagnostic.month_end_ratio).abs()
    diagnostic.nlargest(10,'selected_abs_error').to_csv(OUT/'post_lock_extreme_ratio_diagnostic.csv',index=False)
    save(OUT/'extreme_ratio_notes.json',{'scope':'Post-lock descriptive error diagnosis only. No refit, clipping, threshold change or removal.',
        'selected_model':selected,'largest_observed_target_ratio':float(exact.month_end_ratio.max()),
        'max_absolute_error':float(diagnostic.selected_abs_error.max()),'common_baseline_excluded_months':len(exact)-len(common),
        'interpretation':'A large ratio can arise from a small strictly past outflow denominator. Report full-target results prominently; common-case results are not a replacement population.'})
    bias,_=bias_report();plot_regression(metrics,maes,rmses,names)
    plot_regression(all_available,None,None,names,all_available=True);plots_other(test,lock,bias)
    print('REGRESSION COMMON CASES',json.dumps(metrics),flush=True)
    print('EXPLORATORY BOOTSTRAP DIAGNOSTICS',json.dumps({k:{'zero_positive_draws':v['zero_positive_draws'],'zero_negative_draws':v['zero_negative_draws'],'intervals':v['intervals']} for k,v in binary.items()}),flush=True)


if __name__=='__main__':main()
