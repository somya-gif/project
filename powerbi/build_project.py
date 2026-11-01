"""Generate editable PBIP/PBIR definitions. Desktop rendering remains a Windows gate."""
from pathlib import Path
import argparse,json,uuid
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'powerbi';MODEL=OUT/'RetentionLens.SemanticModel';REPORT=OUT/'RetentionLens.Report'
BASE='https://developer.microsoft.com/json-schemas/fabric/'

def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2),encoding='utf-8')

def expr(value):return {'expr':{'Literal':{'Value':value}}}
def text(value):return expr("'"+value.replace("'","''")+"'")
def projection(table,field,measure=False):
    return {'field':{'Measure' if measure else 'Column':{'Expression':{'SourceRef':{'Entity':table}},'Property':field}},
            'queryRef':f'{table}.{field}','nativeQueryRef':field}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data-dir',default=str(ROOT/'data/processed'))
    args=parser.parse_args()
    source=Path(args.data_dir).resolve().as_posix()
    tables=[]
    specs={'Sales':'sales_orders.csv','DailySales':'daily_sales.csv','Calendar':'calendar.csv',
           'Customers':'customers.csv','Cohorts':'cohort_retention.csv','Retention':'monthly_retention.csv',
           'Predictions':'customer_predictions.csv','Performance':'model_performance.csv'}
    force_text={'customer_id','order_id','month','cohort','country','likelihood_band','model_version'}
    for name,file in specs.items():
        d=pd.read_csv(ROOT/'data/processed'/file,nrows=100,dtype={c:str for c in force_text})
        columns=[];types=[]
        for col in d:
            if col in force_text:typ,mtype='string','type text'
            elif col in ['date','order_date','snapshot_date','first_observed_purchase']:typ,mtype='dateTime','type datetime'
            elif pd.api.types.is_integer_dtype(d[col]):typ,mtype='int64','Int64.Type'
            elif pd.api.types.is_numeric_dtype(d[col]):typ,mtype='double','type number'
            else:typ,mtype='string','type text'
            columns.append({'name':col,'dataType':typ,'sourceColumn':col,'summarizeBy':'none'})
            types.append('{"'+col+'", '+mtype+'}')
        query=['let',f'    Source = Csv.Document(File.Contents(DataFolder & "/{file}"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
            '    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
            '    Typed = Table.TransformColumnTypes(Headers, {'+', '.join(types)+'}, "en-GB")','in','    Typed']
        if name=='Customers':
            query[-2:]=['    // Anonymous invoice bucket is retained for financial reconciliation.', 'in',
                '    Table.InsertRows(Typed, Table.RowCount(Typed), {[customer_id="UNKNOWN", first_observed_purchase=null, country="Unknown", cohort="Unknown"]})']
        tables.append({'name':name,'columns':columns,'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':query}}]})
    measures={
      'DailySales':[
        ('Gross Sales','SUM(DailySales[gross_sales])','£#,##0.00'),
        ('Credits','SUM(DailySales[credits])','£#,##0.00'),
        ('Net Invoiced Sales','[Gross Sales] - [Credits]','£#,##0.00')],
      'Sales':[
        ('Orders','COUNTROWS(Sales)','#,##0'),
        ('Active Known Customers','CALCULATE(DISTINCTCOUNT(Sales[customer_id]), Sales[customer_id] <> "UNKNOWN")','#,##0'),
        ('Average Order Value','DIVIDE(SUM(Sales[revenue]), [Orders])','£#,##0.00'),
        ('Repeat Order Revenue','CALCULATE(SUM(Sales[revenue]), Sales[is_repeat_order] = 1)','£#,##0.00'),
        ('Repeat Buyer Share','VAR Known = FILTER(VALUES(Sales[customer_id]), Sales[customer_id] <> "UNKNOWN") RETURN DIVIDE(COUNTROWS(FILTER(Known, CALCULATE(COUNTROWS(Sales)) >= 2)), COUNTROWS(Known))','0.0%')],
      'Cohorts':[
        ('Cohort Retention','IF(HASONEVALUE(Cohorts[month_index]), DIVIDE(SUM(Cohorts[active_customers]), SUM(Cohorts[cohort_size])))','0.0%')],
      'Retention':[
        ('Monthly Retention','IF(HASONEVALUE(Retention[month]), DIVIDE(SUM(Retention[retained_from_previous_month]), SUM(Retention[previous_month_customers])))','0.0%'),
        ('Returning Share','DIVIDE(SUM(Retention[returning_customers]), SUM(Retention[active_customers]))','0.0%'),
        ('New Observed Customers','SUM(Retention[new_observed_customers])','#,##0'),
        ('Returning Customers','SUM(Retention[returning_customers])','#,##0')],
      'Predictions':[
        ('Scored Customers','COUNTROWS(Predictions)','#,##0'),
        ('Mean Probability','AVERAGE(Predictions[probability])','0.0%'),
        ('Likely Repeat Customers','SUM(Predictions[predicted_repeat])','#,##0'),
        ('Prediction Date','MAX(Predictions[snapshot_date])','yyyy-MM-dd')],
      'Performance':[
        ('Average Precision','AVERAGE(Performance[average_precision])','0.000'),
        ('Base Rate','AVERAGE(Performance[prevalence])','0.0%'),
        ('Top Decile Lift','AVERAGE(Performance[lift_at_top_10pct])','0.00x')]
    }
    dax=[]
    for t in tables:
        t['measures']=[{'name':n,'expression':e,'formatString':f} for n,e,f in measures.get(t['name'],[])]
        dax.extend(f'// {t["name"]}\n{n} = {e}\n' for n,e,f in measures.get(t['name'],[]))
    rels=[]
    for child,parent,col in [('Sales','Calendar','date'),('DailySales','Calendar','date'),('Sales','Customers','customer_id'),('Predictions','Customers','customer_id')]:
        rels.append({'name':str(uuid.uuid5(uuid.NAMESPACE_URL,child+parent+col)),
            'fromTable':child,'fromColumn':col,'toTable':parent,'toColumn':col,
            'fromCardinality':'many','toCardinality':'one','crossFilteringBehavior':'oneDirection','isActive':True})
    write(MODEL/'definition.pbism',{'$schema':BASE+'item/semanticModel/definitionProperties/1.0.0/schema.json','version':'1.0','settings':{}})
    write(MODEL/'model.bim',{'compatibilityLevel':1600,'model':{'culture':'en-GB','sourceQueryCulture':'en-GB',
        'defaultPowerBIDataSourceVersion':'powerBI_V3','expressions':[{'name':'DataFolder','kind':'m',
        'expression':'"'+source.replace('"','""')+'" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'}],
        'tables':tables,'relationships':rels}})
    write(OUT/'RetentionLens.pbip',{'$schema':BASE+'pbip/pbipProperties/1.0.0/schema.json','version':'1.0',
        'artifacts':[{'report':{'path':'RetentionLens.Report'}}],'settings':{'enableAutoRecovery':True}})
    write(REPORT/'definition.pbir',{'$schema':BASE+'item/report/definitionProperties/2.0.0/schema.json','version':'4.0',
        'datasetReference':{'byPath':{'path':'../RetentionLens.SemanticModel'}}})
    definition=REPORT/'definition'
    write(definition/'version.json',{'$schema':BASE+'item/report/definition/versionMetadata/1.0.0/schema.json','version':'2.0.0'})
    write(definition/'report.json',{'$schema':BASE+'item/report/definition/report/2.0.0/schema.json','themeCollection':{}})
    pages=[]
    def page(name,label):
        pages.append(name)
        p=definition/'pages'/name
        write(p/'page.json',{'$schema':BASE+'item/report/definition/page/2.0.0/schema.json','name':name,'displayName':label,'displayOption':'FitToPage','width':1280,'height':720})
        return p
    def visual(p,name,kind,title,roles,x,y,w,h):
        v={'$schema':BASE+'item/report/definition/visualContainer/2.4.0/schema.json','name':name,
            'position':{'x':x,'y':y,'z':0,'width':w,'height':h,'tabOrder':0},
            'visual':{'visualType':kind,'query':{'queryState':{role:{'projections':ps} for role,ps in roles.items()}},
            'visualContainerObjects':{'title':[{'properties':{'show':expr('true'),'text':text(title)}}]},'drillFilterOtherVisuals':True}}
        write(p/'visuals'/name/'visual.json',v)
    C=lambda t,f:projection(t,f);M=lambda t,f:projection(t,f,True)
    p=page('Executive','01 | Sales · GBP · final day partial')
    for i,(t,m) in enumerate([('DailySales','Gross Sales'),('DailySales','Credits'),('DailySales','Net Invoiced Sales'),('Sales','Orders')]):
        visual(p,f'kpi{i}','card',m,{'Values':[M(t,m)]},20+i*310,20,290,115)
    visual(p,'trend','lineChart','Gross and net invoiced sales',{'Category':[C('Calendar','month')],'Y':[M('DailySales','Gross Sales'),M('DailySales','Net Invoiced Sales')]},20,160,820,340)
    visual(p,'period','slicer','Sales month',{'Values':[C('Calendar','month')]},870,160,390,340)
    visual(p,'aov','card','Average order value',{'Values':[M('Sales','Average Order Value')]},20,530,390,150)
    visual(p,'customers','card','Known customers in selection',{'Values':[M('Sales','Active Known Customers')]},445,530,390,150)
    visual(p,'repeat','card','Customers with 2+ orders in selection',{'Values':[M('Sales','Repeat Buyer Share')]},870,530,390,150)
    p=page('Retention','02 | Retention · complete months only')
    visual(p,'retention','lineChart','Previous-month buyers who returned',{'Category':[C('Retention','month')],'Y':[M('Retention','Monthly Retention')]},20,20,800,310)
    visual(p,'share','lineChart','Returning share of current active customers',{'Category':[C('Retention','month')],'Y':[M('Retention','Returning Share')]},20,370,800,310)
    visual(p,'mix','clusteredColumnChart','First observed vs returning customers',{'Category':[C('Retention','month')],'Y':[M('Retention','New Observed Customers'),M('Retention','Returning Customers')]},850,20,410,660)
    p=page('Cohorts','03 | Cohorts · first observed purchase · not acquisition')
    visual(p,'matrix','pivotTable','Monthly purchase retention · blanks = not observed',{'Rows':[C('Cohorts','cohort')],'Columns':[C('Cohorts','month_index')],'Values':[M('Cohorts','Cohort Retention')]},20,20,1240,660)
    p=page('Predictions','04 | Predictions · historical 2011-12-09 snapshot')
    for i,m in enumerate(['Scored Customers','Mean Probability','Likely Repeat Customers']):
        visual(p,f'prediction{i}','card',m,{'Values':[M('Predictions',m)]},20+i*420,20,400,120)
    visual(p,'bands','clusteredBarChart','Likelihood bands (not churn)',{'Category':[C('Predictions','likelihood_band')],'Y':[M('Predictions','Scored Customers')]},20,170,390,250)
    visual(p,'bandfilter','slicer','Filter likelihood',{'Values':[C('Predictions','likelihood_band')]},20,450,390,230)
    visual(p,'customerlist','tableEx','Existing customer predictions · 30-day window',{'Values':[C('Predictions',f) for f in ['customer_id','probability','predicted_repeat','recency_days','orders_lifetime','revenue_lifetime']]},440,170,820,510)
    p=page('Evidence','05 | Model evidence · held-out test months')
    visual(p,'ap','lineChart','Average precision vs base rate by snapshot',{'Category':[C('Performance','snapshot_date')],'Y':[M('Performance','Average Precision'),M('Performance','Base Rate')]},20,20,780,320)
    visual(p,'lift','lineChart','Top 10% lift by snapshot',{'Category':[C('Performance','snapshot_date')],'Y':[M('Performance','Top Decile Lift')]},20,370,780,310)
    visual(p,'evidence','tableEx','Evaluation details',{'Values':[C('Performance',f) for f in ['snapshot_date','n','precision','recall','f1','brier_score']]},830,20,430,660)
    write(definition/'pages/pages.json',{'$schema':BASE+'item/report/definition/pagesMetadata/1.0.0/schema.json','pageOrder':pages,'activePageName':pages[0]})
    write(OUT/'RetentionLens_Theme.json',{'name':'Retention Lens','dataColors':['#0E938B','#1D4ED8','#F59E0B','#7C3AED','#64748B'],
        'background':'#F7FAFC','foreground':'#152D42','tableAccent':'#0E938B'})
    (OUT/'measures.dax').write_text('\n'.join(dax),encoding='utf-8')
    print(f'Generated {len(pages)} pages. DataFolder: {source}. Desktop verification/PBIX export still required.')

if __name__=='__main__':main()
