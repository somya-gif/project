"""Run with python -m src.pipeline. No synthetic fallback."""
import hashlib, json, platform, sys, urllib.request, zipfile
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (average_precision_score, roc_auc_score, brier_score_loss,
                            precision_score, recall_score, f1_score, confusion_matrix)
from sklearn.inspection import permutation_importance
from .features import FEATURES, snapshot, quality_and_clean

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/processed'; ART=ROOT/'artifacts'
URL='https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip'

def dump(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str),encoding='utf-8')

def metrics(y,p,threshold):
    pred=p>=threshold
    n=max(1,int(np.ceil(len(y)*.1)))
    top=np.argsort(-p,kind='stable')[:n]
    rate=float(np.mean(y))
    return {'n':len(y),'positives':int(np.sum(y)),'prevalence':rate,
        'average_precision':float(average_precision_score(y,p)),
        'roc_auc':float(roc_auc_score(y,p)), 'brier_score':float(brier_score_loss(y,p)),
        'precision':float(precision_score(y,pred,zero_division=0)),
        'recall':float(recall_score(y,pred,zero_division=0)),
        'f1':float(f1_score(y,pred,zero_division=0)),
        'precision_at_top_10pct':float(np.asarray(y)[top].mean()),
        'lift_at_top_10pct':float(np.asarray(y)[top].mean()/rate),
        'confusion_matrix_tn_fp_fn_tp':confusion_matrix(y,pred,labels=[0,1]).ravel().tolist()}

def bi_exports(purchases,credits,orders,end):
    # Preserve anonymous sales in financial totals; exclude from customer denominators.
    allorders=purchases.assign(customer_id=purchases.customer_id.fillna('UNKNOWN')).groupby('order_id',as_index=False).agg(
        customer_id=('customer_id','first'),order_date=('order_date','min'),revenue=('revenue','sum'),units=('quantity','sum'),country=('country','first'))
    allorders=allorders.sort_values(['order_date','order_id'])
    allorders['is_repeat_order']=((allorders.groupby('customer_id').cumcount()>0)&(allorders.customer_id!='UNKNOWN')).astype(int)
    allorders['date']=allorders.order_date.dt.strftime('%Y-%m-%d')
    allorders['month']=allorders.order_date.dt.strftime('%Y-%m')
    allorders.to_csv(DATA/'sales_orders.csv',index=False)
    customers=orders.sort_values('order_date').groupby('customer_id',as_index=False).agg(first_observed_purchase=('order_date','min'),country=('country','last'))
    customers['cohort']=customers.first_observed_purchase.dt.strftime('%Y-%m')
    customers.to_csv(DATA/'customers.csv',index=False)
    daily=allorders.groupby('date',as_index=False).agg(gross_sales=('revenue','sum'),orders=('order_id','size'),units=('units','sum'))
    cred=credits.assign(date=credits.order_date.dt.strftime('%Y-%m-%d')).groupby('date').credit_amount.sum()
    cal=pd.DataFrame({'date':pd.date_range(purchases.order_date.min().normalize(),end,freq='D')})
    cal['month']=cal.date.dt.strftime('%Y-%m');cal['year']=cal.date.dt.year
    cal['date']=cal.date.dt.strftime('%Y-%m-%d');cal.to_csv(DATA/'calendar.csv',index=False)
    daily=cal[['date']].merge(daily,on='date',how='left').fillna(0)
    daily['credits']=daily.date.map(cred).fillna(0)
    daily['net_invoiced_sales']=daily.gross_sales-daily.credits
    daily['month']=daily.date.str[:7];daily.to_csv(DATA/'daily_sales.csv',index=False)
    # Monthly retention: complete months only. Re-entry allowed; not survival retention.
    complete=orders[orders.order_date < end.to_period('M').start_time].copy()
    complete['month']=complete.order_date.dt.to_period('M')
    first=orders.groupby('customer_id').order_date.min().dt.to_period('M')
    complete['cohort']=complete.customer_id.map(first)
    counts=complete.groupby(['cohort','month']).customer_id.nunique()
    sizes=first.value_counts()
    rows=[]
    last=end.to_period('M')-1
    for cohort in sorted(first.unique()):
        for month in pd.period_range(cohort,last,freq='M'):
            n=int(counts.get((cohort,month),0));base=int(sizes[cohort])
            rows.append({'cohort':str(cohort),'month':str(month),'month_index':month.ordinal-cohort.ordinal,
                         'active_customers':n,'cohort_size':base,'retention_rate':n/base})
    pd.DataFrame(rows).to_csv(DATA/'cohort_retention.csv',index=False)
    rows=[]
    for month,g in complete.groupby('month'):
        active=set(g.customer_id); prev=set(complete.loc[complete.month==month-1,'customer_id'])
        returning=sum(first[c]<month for c in active)
        rows.append({'month':str(month),'active_customers':len(active),'new_observed_customers':len(active)-returning,
                     'returning_customers':returning,'previous_month_customers':len(prev),
                     'retained_from_previous_month':len(active&prev),
                     'monthly_retention_rate':len(active&prev)/len(prev) if prev else np.nan,
                     'returning_customer_share':returning/len(active)})
    pd.DataFrame(rows).to_csv(DATA/'monthly_retention.csv',index=False)

def main():
    DATA.mkdir(parents=True,exist_ok=True);ART.mkdir(exist_ok=True)
    raw=ROOT/'data/raw';raw.mkdir(exist_ok=True)
    xlsx=raw/'online_retail_II.xlsx';archive=raw/'online_retail_ii.zip'
    if not xlsx.exists():
        if not archive.exists(): urllib.request.urlretrieve(URL,archive)
        with zipfile.ZipFile(archive) as z: xlsx.write_bytes(z.read('online_retail_II.xlsx'))
    print('Reading both source sheets...',flush=True)
    source=pd.concat(pd.read_excel(xlsx,sheet_name=None).values(),ignore_index=True)
    purchases,credits,orders,audit=quality_and_clean(source)
    # Last source day is incomplete. Treat its midnight as exclusive reliable boundary.
    end=pd.Timestamp(audit['max_timestamp']).normalize()
    orders.to_csv(DATA/'known_customer_orders.csv',index=False)
    dump(ART/'data_quality.json',audit)
    dump(ART/'provenance.json',{'source':URL,'doi':'10.24432/C5CG6D','creator':'Daqing Chen',
        'license':'CC BY 4.0','xlsx_sha256':hashlib.sha256(xlsx.read_bytes()).hexdigest(),
        'python':sys.version,'pandas':pd.__version__,'sklearn':sklearn.__version__,
        'platform':platform.platform(),'reliable_observation_end_exclusive':end})
    bi_exports(purchases,credits,orders,end)
    dates={'train':pd.date_range('2010-06-01','2011-02-01',freq='MS'),
           'validation':pd.date_range('2011-04-01','2011-06-01',freq='MS'),
           'test':pd.date_range('2011-08-01','2011-11-01',freq='MS')}
    assert dates['train'].max()+pd.Timedelta(days=30)<dates['validation'].min()
    assert dates['validation'].max()+pd.Timedelta(days=30)<dates['test'].min()
    splits={k:pd.concat([snapshot(orders,d,True,end) for d in ds],ignore_index=True) for k,ds in dates.items()}
    for k,d in splits.items(): d.to_csv(DATA/f'{k}_snapshots.csv',index=False)
    tr,va,te=(splits[k] for k in ['train','validation','test'])
    candidates={'base_rate':DummyClassifier(strategy='prior'),
        'logistic':make_pipeline(StandardScaler(),LogisticRegression(max_iter=1500,random_state=42)),
        'gradient_boosting':HistGradientBoostingClassifier(max_iter=160,max_leaf_nodes=15,l2_regularization=10,learning_rate=.06,early_stopping=False,random_state=42)}
    fitted={};comparison=[]
    for name,m in candidates.items():
        print('Training',name,flush=True)
        m.fit(tr[FEATURES],tr.target);p=m.predict_proba(va[FEATURES])[:,1]
        fitted[name]=m;comparison.append({'model':name,**metrics(va.target,p,.5)})
    best=max(comparison,key=lambda r:r['average_precision'])['model'];model=fitted[best]
    pval=model.predict_proba(va[FEATURES])[:,1]
    thresholds=np.arange(.05,.81,.01)
    threshold=float(max(thresholds,key=lambda t:f1_score(va.target,pval>=t,zero_division=0)))
    # Selection and threshold are frozen before held-out test evaluation.
    ptest=model.predict_proba(te[FEATURES])[:,1]
    report={'selected_model':best,'selection_metric':'validation average precision','threshold':threshold,
        'threshold_policy':'Validation F1 maximum; illustrative, not business-cost optimal',
        'features':FEATURES,'splits':{k:[str(x.date()) for x in ds] for k,ds in dates.items()},
        'validation_candidates':comparison,'test':metrics(te.target,ptest,threshold),
        'test_base_rate':metrics(te.target,fitted['base_rate'].predict_proba(te[FEATURES])[:,1],.5)}
    test_predictions=te[['customer_id','snapshot_date','target']].copy();test_predictions['probability']=ptest
    test_predictions.to_csv(DATA/'test_predictions.csv',index=False)
    monthly=[]
    for dt,g in test_predictions.groupby('snapshot_date'):
        monthly.append({'snapshot_date':str(dt.date()),**metrics(g.target,g.probability.to_numpy(),threshold)})
    report['test_by_month']=monthly
    pd.DataFrame(monthly).drop(columns=['confusion_matrix_tn_fp_fn_tp']).to_csv(DATA/'model_performance.csv',index=False)
    reliability=test_predictions.assign(bin=pd.cut(ptest,np.linspace(0,1,11),include_lowest=True)).groupby('bin',observed=True).agg(mean_probability=('probability','mean'),observed_rate=('target','mean'),count=('target','size')).reset_index()
    reliability.to_csv(DATA/'calibration.csv',index=False)
    imp=permutation_importance(model,va[FEATURES],va.target,scoring='average_precision',n_repeats=3,random_state=42)
    pd.DataFrame({'feature':FEATURES,'ap_decrease':imp.importances_mean,'std':imp.importances_std}).sort_values('ap_decrease',ascending=False).to_csv(DATA/'feature_importance.csv',index=False)
    latest=snapshot(orders,end);latest['probability']=model.predict_proba(latest[FEATURES])[:,1]
    latest['predicted_repeat']=(latest.probability>=threshold).astype(int)
    latest['likelihood_band']=pd.cut(latest.probability,[-.001,.2,.5,1],labels=['Low','Medium','High']).astype(str)
    latest['model_version']='retail-v1';latest.to_csv(DATA/'customer_predictions.csv',index=False)
    bundle={'model':model,'features':FEATURES,'threshold':threshold,'snapshot_date':str(end.date()),'model_version':'retail-v1'}
    joblib.dump(bundle,ART/'model.joblib',compress=3);dump(ART/'metrics.json',report)
    print(json.dumps({'quality':audit,'model':best,'threshold':threshold,'test':report['test']},indent=2),flush=True)

if __name__=='__main__':main()
