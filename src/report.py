"""Generate evidence figure from measured exports, not illustrative numbers."""
from pathlib import Path
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data/processed'
def main():
    m=json.loads((ROOT/'artifacts/metrics.json').read_text())['test']
    d=pd.read_csv(DATA/'test_predictions.csv');pr,rc,_=precision_recall_curve(d.target,d.probability)
    sales=pd.read_csv(DATA/'daily_sales.csv').groupby('month').gross_sales.sum()/1e6
    cohort=pd.read_csv(DATA/'cohort_retention.csv').pivot(index='cohort',columns='month_index',values='retention_rate')
    cal=pd.read_csv(DATA/'calibration.csv')
    plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#334155','text.color':'#152D42','font.size':10})
    fig,axes=plt.subplots(2,2,figsize=(15,10));fig.patch.set_facecolor('#F7FAFC')
    fig.suptitle('RETENTION LENS  |  Measured project evidence',x=.06,ha='left',fontsize=23,fontweight='bold',y=.97)
    fig.text(.06,.915,f"Historical UCI data  •  Test AP {m['average_precision']:.3f}  •  Base rate {m['prevalence']:.1%}  •  Top-decile lift {m['lift_at_top_10pct']:.2f}×",fontsize=12)
    ax=axes[0,0];ax.plot(sales.index,sales.values,color='#0E938B',linewidth=2.5);ax.set_title('Gross invoiced sales · GBP millions',loc='left',pad=15)
    ax.set_xticks(range(0,len(sales),4),sales.index[::4],rotation=25);ax.set_ylabel('GBP million');ax.grid(axis='y',alpha=.15)
    ax=axes[0,1];ax.plot(rc,pr,color='#1D4ED8',linewidth=2);ax.axhline(m['prevalence'],linestyle='--',color='#64748B',label='Test prevalence');ax.set(xlabel='Recall',ylabel='Precision',xlim=(0,1),ylim=(0,1));ax.set_title('Held-out precision–recall',loc='left',pad=15);ax.legend(frameon=False)
    ax=axes[1,0];img=ax.imshow(cohort.to_numpy(),vmin=0,vmax=1,cmap='YlGnBu',aspect='auto');ax.set_title('Monthly cohort retention · blank = unobserved',loc='left',pad=15);ax.set_xlabel('Months since first observed purchase');ax.set_yticks(range(0,len(cohort),4),cohort.index[::4]);fig.colorbar(img,ax=ax,fraction=.03,pad=.02)
    ax=axes[1,1];ax.plot([0,1],[0,1],'--',color='#94A3B8',label='Perfect reliability');ax.plot(cal.mean_probability,cal.observed_rate,'o-',color='#0E938B',label='Test bins');ax.set(xlabel='Mean predicted probability',ylabel='Observed purchase rate',xlim=(0,1),ylim=(0,1));ax.set_title('Probability reliability · no separate calibration',loc='left',pad=15);ax.legend(frameon=False)
    fig.text(.06,.025,'Sumit Gole  |  21,489 test snapshots, not unique people  |  December 2011 sales are partial  |  Not a Power BI screenshot',fontsize=10,color='#475569')
    fig.subplots_adjust(top=.85,bottom=.11,left=.07,right=.96,hspace=.48,wspace=.3)
    fig.savefig(ROOT/'docs/Measured_Evidence.png',dpi=150,facecolor=fig.get_facecolor());plt.close(fig)
if __name__=='__main__':main()
