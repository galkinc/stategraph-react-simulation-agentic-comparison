from statsmodels.stats.contingency_tables import mcnemar
import numpy as np

print("Проверка различных таблиц для McNemar:")
print("Формат: table[[0,0], [0,b], [c,0], [1,1]] где [0,1]=b discordant, [1,0]=c discordant")
print()

# statistic=9.0 возможно только при specific table
# p=0.52 возможно при exact test с маленькой таблицей

for b in range(20):
    for c in range(20):
        if b + c > 0:
            table = np.array([[10, b], [c, 10]])  # a=10, d=10 для примера
            try:
                result = mcnemar(table, exact=True)
                if abs(result.statistic - 9.0) < 0.5 and abs(result.pvalue - 0.52) < 0.05:
                    print(f'b={b}, c={c}: stat={result.statistic:.2f}, p={result.pvalue:.2f}')
                    print(f'  Table: {table}')
            except Exception as e:
                pass

# Также проверим без correction
print("\n\nПроверка без Yates correction:")
for b in range(20):
    for c in range(20):
        if b + c > 0:
            table = np.array([[10, b], [c, 10]])
            try:
                result = mcnemar(table, exact=False, correction=False)
                if abs(result.statistic - 9.0) < 0.5 and abs(result.pvalue - 0.52) < 0.05:
                    print(f'b={b}, c={c}: stat={result.statistic:.2f}, p={result.pvalue:.2f}')
            except:
                pass
