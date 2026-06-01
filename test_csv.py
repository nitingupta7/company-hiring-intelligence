import pandas as pd

df = pd.read_csv('/Users/nitingupta/Desktop/Python_project/input/investments_VC.csv', encoding='latin1')
print(df.shape)
print(df.head())