"""
Generates editable Power BI Project (PBIP/PBIR) definitions from local data exports.
Run with: python powerbi/build_project.py
"""

import argparse
import json
import uuid
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'powerbi'
MODEL = OUT / 'RetentionLens.SemanticModel'
REPORT = OUT / 'RetentionLens.Report'
SCHEMA_BASE = 'https://developer.microsoft.com/json-schemas/fabric/'


def write_json(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding='utf-8')


def expr(value):
    return {'expr': {'Literal': {'Value': value}}}


def text_expr(value):
    return expr("'" + value.replace("'", "''") + "'")


def projection(table: str, field: str, is_measure: bool = False):
    return {
        'field': {
            'Measure' if is_measure else 'Column': {
                'Expression': {'SourceRef': {'Entity': table}},
                'Property': field,
            }
        },
        'queryRef': f'{table}.{field}',
        'nativeQueryRef': field,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', default=str(ROOT / 'data/processed'))
    args = parser.parse_args()
    source_dir = Path(args.data_dir).resolve().as_posix()

    tables = []
    specs = {
        'Sales': 'sales_orders.csv',
        'DailySales': 'daily_sales.csv',
        'Calendar': 'calendar.csv',
        'Customers': 'customers.csv',
        'Cohorts': 'cohort_retention.csv',
        'Retention': 'monthly_retention.csv',
        'Predictions': 'customer_predictions.csv',
        'Performance': 'model_performance.csv',
    }
    force_text = {'customer_id', 'order_id', 'month', 'cohort', 'country', 'likelihood_band', 'model_version'}

    for name, file in specs.items():
        csv_file = ROOT / 'data/processed' / file
        if not csv_file.exists():
            print(f"Data file '{file}' not found in data/processed/. Please run 'python -m src.pipeline' first.")
            return

        sample_df = pd.read_csv(csv_file, nrows=100, dtype={c: str for c in force_text})
        columns, type_mappings = [], []

        for col in sample_df:
            if col in force_text:
                typ, mtype = 'string', 'type text'
            elif col in ['date', 'order_date', 'snapshot_date', 'first_observed_purchase']:
                typ, mtype = 'dateTime', 'type datetime'
            elif pd.api.types.is_integer_dtype(sample_df[col]):
                typ, mtype = 'int64', 'Int64.Type'
            elif pd.api.types.is_numeric_dtype(sample_df[col]):
                typ, mtype = 'double', 'type number'
            else:
                typ, mtype = 'string', 'type text'

            columns.append({'name': col, 'dataType': typ, 'sourceColumn': col, 'summarizeBy': 'none'})
            type_mappings.append('{"' + col + '", ' + mtype + '}')

        power_query = [
            'let',
            f'    Source = Csv.Document(File.Contents(DataFolder & "/{file}"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
            '    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
            '    Typed = Table.TransformColumnTypes(Headers, {' + ', '.join(type_mappings) + '}, "en-GB")',
            'in',
            '    Typed',
        ]

        if name == 'Customers':
            power_query[-2:] = [
                '    // Retain anonymous orders for complete financial totals',
                'in',
                '    Table.InsertRows(Typed, Table.RowCount(Typed), {[customer_id="UNKNOWN", first_observed_purchase=null, country="Unknown", cohort="Unknown"]})',
            ]

        tables.append({
            'name': name,
            'columns': columns,
            'partitions': [{
                'name': name,
                'mode': 'import',
                'source': {'type': 'm', 'expression': power_query},
            }],
        })

    measures = {
        'DailySales': [
            ('Gross Sales', 'SUM(DailySales[gross_sales])', '£#,##0.00'),
            ('Credits', 'SUM(DailySales[credits])', '£#,##0.00'),
            ('Net Invoiced Sales', '[Gross Sales] - [Credits]', '£#,##0.00'),
        ],
        'Sales': [
            ('Orders', 'COUNTROWS(Sales)', '#,##0'),
            ('Active Known Customers', 'CALCULATE(DISTINCTCOUNT(Sales[customer_id]), Sales[customer_id] <> "UNKNOWN")', '#,##0'),
            ('Average Order Value', 'DIVIDE(SUM(Sales[revenue]), [Orders])', '£#,##0.00'),
            ('Repeat Order Revenue', 'CALCULATE(SUM(Sales[revenue]), Sales[is_repeat_order] = 1)', '£#,##0.00'),
            ('Repeat Buyer Share', 'VAR Known = FILTER(VALUES(Sales[customer_id]), Sales[customer_id] <> "UNKNOWN") RETURN DIVIDE(COUNTROWS(FILTER(Known, CALCULATE(COUNTROWS(Sales)) >= 2)), COUNTROWS(Known))', '0.0%'),
        ],
        'Cohorts': [
            ('Cohort Retention', 'IF(HASONEVALUE(Cohorts[month_index]), DIVIDE(SUM(Cohorts[active_customers]), SUM(Cohorts[cohort_size])))', '0.0%'),
        ],
        'Retention': [
            ('Monthly Retention', 'IF(HASONEVALUE(Retention[month]), DIVIDE(SUM(Retention[retained_from_previous_month]), SUM(Retention[previous_month_customers])))', '0.0%'),
            ('Returning Share', 'DIVIDE(SUM(Retention[returning_customers]), SUM(Retention[active_customers]))', '0.0%'),
            ('New Observed Customers', 'SUM(Retention[new_observed_customers])', '#,##0'),
            ('Returning Customers', 'SUM(Retention[returning_customers])', '#,##0'),
        ],
        'Predictions': [
            ('Scored Customers', 'COUNTROWS(Predictions)', '#,##0'),
            ('Mean Probability', 'AVERAGE(Predictions[probability])', '0.0%'),
            ('Likely Repeat Customers', 'SUM(Predictions[predicted_repeat])', '#,##0'),
            ('Prediction Date', 'MAX(Predictions[snapshot_date])', 'yyyy-MM-dd'),
        ],
        'Performance': [
            ('Average Precision', 'AVERAGE(Performance[average_precision])', '0.000'),
            ('Base Rate', 'AVERAGE(Performance[prevalence])', '0.0%'),
            ('Top Decile Lift', 'AVERAGE(Performance[lift_at_top_10pct])', '0.00x'),
        ],
    }

    dax_export = []
    for t in tables:
        t['measures'] = [{'name': n, 'expression': e, 'formatString': f} for n, e, f in measures.get(t['name'], [])]
        dax_export.extend(f'// {t["name"]}\n{n} = {e}\n' for n, e, f in measures.get(t['name'], []))

    relationships = []
    rel_specs = [
        ('Sales', 'Calendar', 'date'),
        ('DailySales', 'Calendar', 'date'),
        ('Sales', 'Customers', 'customer_id'),
        ('Predictions', 'Customers', 'customer_id'),
    ]
    for child, parent, col in rel_specs:
        relationships.append({
            'name': str(uuid.uuid5(uuid.NAMESPACE_URL, child + parent + col)),
            'fromTable': child,
            'fromColumn': col,
            'toTable': parent,
            'toColumn': col,
            'fromCardinality': 'many',
            'toCardinality': 'one',
            'crossFilteringBehavior': 'oneDirection',
            'isActive': True,
        })

    write_json(MODEL / 'definition.pbism', {
        '$schema': SCHEMA_BASE + 'item/semanticModel/definitionProperties/1.0.0/schema.json',
        'version': '1.0',
        'settings': {},
    })
    write_json(MODEL / 'model.bim', {
        'compatibilityLevel': 1600,
        'model': {
            'culture': 'en-GB',
            'sourceQueryCulture': 'en-GB',
            'defaultPowerBIDataSourceVersion': 'powerBI_V3',
            'expressions': [{
                'name': 'DataFolder',
                'kind': 'm',
                'expression': '"' + source_dir.replace('"', '""') + '" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
            }],
            'tables': tables,
            'relationships': relationships,
        },
    })

    write_json(OUT / 'RetentionLens.pbip', {
        '$schema': SCHEMA_BASE + 'pbip/pbipProperties/1.0.0/schema.json',
        'version': '1.0',
        'artifacts': [{'report': {'path': 'RetentionLens.Report'}}],
        'settings': {'enableAutoRecovery': True},
    })
    write_json(REPORT / 'definition.pbir', {
        '$schema': SCHEMA_BASE + 'item/report/definitionProperties/2.0.0/schema.json',
        'version': '4.0',
        'datasetReference': {'byPath': {'path': '../RetentionLens.SemanticModel'}},
    })

    definition = REPORT / 'definition'
    write_json(definition / 'version.json', {
        '$schema': SCHEMA_BASE + 'item/report/definition/versionMetadata/1.0.0/schema.json',
        'version': '2.0.0',
    })
    write_json(definition / 'report.json', {
        '$schema': SCHEMA_BASE + 'item/report/definition/report/2.0.0/schema.json',
        'themeCollection': {},
    })

    pages = []

    def add_page(name: str, label: str):
        pages.append(name)
        page_dir = definition / 'pages' / name
        write_json(page_dir / 'page.json', {
            '$schema': SCHEMA_BASE + 'item/report/definition/page/2.0.0/schema.json',
            'name': name,
            'displayName': label,
            'displayOption': 'FitToPage',
            'width': 1280,
            'height': 720,
        })
        return page_dir

    def add_visual(page_dir, name, kind, title, roles, x, y, w, h):
        v = {
            '$schema': SCHEMA_BASE + 'item/report/definition/visualContainer/2.4.0/schema.json',
            'name': name,
            'position': {'x': x, 'y': y, 'z': 0, 'width': w, 'height': h, 'tabOrder': 0},
            'visual': {
                'visualType': kind,
                'query': {'queryState': {role: {'projections': ps} for role, ps in roles.items()}},
                'visualContainerObjects': {'title': [{'properties': {'show': expr('true'), 'text': text_expr(title)}}]},
                'drillFilterOtherVisuals': True,
            },
        }
        write_json(page_dir / 'visuals' / name / 'visual.json', v)

    C = lambda t, f: projection(t, f)
    M = lambda t, f: projection(t, f, True)

    # Page 1: Executive Sales Overview
    p = add_page('Executive', 'Sales Overview')
    kpis = [
        ('DailySales', 'Gross Sales'),
        ('DailySales', 'Credits'),
        ('DailySales', 'Net Invoiced Sales'),
        ('Sales', 'Orders'),
    ]
    for i, (tbl, meas) in enumerate(kpis):
        add_visual(p, f'kpi{i}', 'card', meas, {'Values': [M(tbl, meas)]}, 20 + i * 310, 20, 290, 115)

    add_visual(p, 'trend', 'lineChart', 'Gross and Net Invoiced Sales', {
        'Category': [C('Calendar', 'month')],
        'Y': [M('DailySales', 'Gross Sales'), M('DailySales', 'Net Invoiced Sales')],
    }, 20, 160, 820, 340)
    add_visual(p, 'period', 'slicer', 'Filter by Month', {'Values': [C('Calendar', 'month')]}, 870, 160, 390, 340)
    add_visual(p, 'aov', 'card', 'Average Order Value', {'Values': [M('Sales', 'Average Order Value')]}, 20, 530, 390, 150)
    add_visual(p, 'customers', 'card', 'Active Customers', {'Values': [M('Sales', 'Active Known Customers')]}, 445, 530, 390, 150)
    add_visual(p, 'repeat', 'card', 'Repeat Buyer Share', {'Values': [M('Sales', 'Repeat Buyer Share')]}, 870, 530, 390, 150)

    # Page 2: Customer Retention
    p = add_page('Retention', 'Customer Retention')
    add_visual(p, 'retention', 'lineChart', 'Month-over-Month Retention Rate', {
        'Category': [C('Retention', 'month')],
        'Y': [M('Retention', 'Monthly Retention')],
    }, 20, 20, 800, 310)
    add_visual(p, 'share', 'lineChart', 'Returning Share of Active Customers', {
        'Category': [C('Retention', 'month')],
        'Y': [M('Retention', 'Returning Share')],
    }, 20, 370, 800, 310)
    add_visual(p, 'mix', 'clusteredColumnChart', 'New vs. Returning Customers', {
        'Category': [C('Retention', 'month')],
        'Y': [M('Retention', 'New Observed Customers'), M('Retention', 'Returning Customers')],
    }, 850, 20, 410, 660)

    # Page 3: Cohort Analysis
    p = add_page('Cohorts', 'Cohort Analysis')
    add_visual(p, 'matrix', 'pivotTable', 'Monthly Cohort Retention Matrix', {
        'Rows': [C('Cohorts', 'cohort')],
        'Columns': [C('Cohorts', 'month_index')],
        'Values': [M('Cohorts', 'Cohort Retention')],
    }, 20, 20, 1240, 660)

    # Page 4: Predictions
    p = add_page('Predictions', 'Customer Predictions')
    for i, meas in enumerate(['Scored Customers', 'Mean Probability', 'Likely Repeat Customers']):
        add_visual(p, f'prediction{i}', 'card', meas, {'Values': [M('Predictions', meas)]}, 20 + i * 420, 20, 400, 120)

    add_visual(p, 'bands', 'clusteredBarChart', 'Customer Count by Likelihood Band', {
        'Category': [C('Predictions', 'likelihood_band')],
        'Y': [M('Predictions', 'Scored Customers')],
    }, 20, 170, 390, 250)
    add_visual(p, 'bandfilter', 'slicer', 'Filter by Likelihood Band', {
        'Values': [C('Predictions', 'likelihood_band')],
    }, 20, 450, 390, 230)
    add_visual(p, 'customerlist', 'tableEx', 'Customer Repeat Purchase Probabilities', {
        'Values': [C('Predictions', f) for f in ['customer_id', 'probability', 'predicted_repeat', 'recency_days', 'orders_lifetime', 'revenue_lifetime']],
    }, 440, 170, 820, 510)

    # Page 5: Model Evidence
    p = add_page('Evidence', 'Model Performance')
    add_visual(p, 'ap', 'lineChart', 'Average Precision vs. Base Rate (Held-out Months)', {
        'Category': [C('Performance', 'snapshot_date')],
        'Y': [M('Performance', 'Average Precision'), M('Performance', 'Base Rate')],
    }, 20, 20, 780, 320)
    add_visual(p, 'lift', 'lineChart', 'Top 10% Lift by Snapshot', {
        'Category': [C('Performance', 'snapshot_date')],
        'Y': [M('Performance', 'Top Decile Lift')],
    }, 20, 370, 780, 310)
    add_visual(p, 'evidence', 'tableEx', 'Snapshot Performance Metrics', {
        'Values': [C('Performance', f) for f in ['snapshot_date', 'n', 'precision', 'recall', 'f1', 'brier_score']],
    }, 830, 20, 430, 660)

    write_json(definition / 'pages/pages.json', {
        '$schema': SCHEMA_BASE + 'item/report/definition/pagesMetadata/1.0.0/schema.json',
        'pageOrder': pages,
        'activePageName': pages[0],
    })
    write_json(OUT / 'RetentionLens_Theme.json', {
        'name': 'Retention Lens',
        'dataColors': ['#0E938B', '#1D4ED8', '#F59E0B', '#7C3AED', '#64748B'],
        'background': '#F7FAFC',
        'foreground': '#152D42',
        'tableAccent': '#0E938B',
    })
    (OUT / 'measures.dax').write_text('\n'.join(dax_export), encoding='utf-8')
    print(f'Successfully generated Power BI project definitions ({len(pages)} pages).')


if __name__ == '__main__':
    main()
