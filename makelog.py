import csv

with open('support_issues/support_issues.csv', newline='', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

with open('support_issues/log.txt', 'w', encoding='utf-8') as f:
    f.write('SUPPORT TRIAGE AGENT - RUN LOG\n')
    f.write('=' * 60 + '\n\n')
    for i, r in enumerate(rows, 1):
        f.write(f'[{i:02d}] {r["subject"] or r["issue"][:55]}\n')
        f.write(f'      status={r["status"]} | type={r["request_type"]} | area={r["product_area"]}\n')
        f.write(f'      justification: {r["justification"]}\n\n')

print('log.txt created successfully!')
