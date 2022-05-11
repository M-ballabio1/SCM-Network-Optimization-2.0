# -*- coding: utf-8 -*-
"""
Created on Sat May  7 10:25:47 2022

@author: matte
"""

#%% Introduction


#%% Libraries

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

#%% Path

path = r'C:\Users\matte\OneDrive\Desktop\documenti\matteo\password e progetti\progetti\Dataset_ML&DL\datasets_supply'
file_excel0 = path+r'/CandidateLocations.xlsx'
file_excel1 = path+r'/CurrentCustomers.xlsx'
file_excel2 = path+r'/ProspectiveCustomers.xlsx'
file_excel3 = path+r'/Kitchenware RevenueSegment.xlsx'
file_excel4 = path+r'/Growth.xlsx'


#%% Exploring dataset and some Variables

df_Locations = pd.read_excel(file_excel0)
df_cur_customer = pd.read_excel(file_excel1)
df_new_customer = pd.read_excel(file_excel2)
df_kit_revenue = pd.read_excel(file_excel3)
df_growth = pd.read_excel(file_excel4)

# basic informations of dataset
print("Righe dataset iniziale:",df_Locations.shape[0])
print("Colonne dataset iniziale:",df_Locations.shape[1])
print(df_Locations.info())                                             #structure and datatypes of data
print(df_Locations.nunique())                                          #Looking unique values for each variables
print(df_Locations.head())                                             #Looking the data


#%% Data Visualization

def Visualization():
    plt.bar(df_Locations['Identifier'],df_Locations['Max yearly capacity'])
    plt.show()

    plt.bar(df_Locations['Identifier'],df_Locations['Yearly fixed cost'])
    plt.show()

    df_Locations['Capacity/FixedCost'] = df_Locations['Max yearly capacity']/df_Locations['Yearly fixed cost']
    plt.bar(df_Locations['Identifier'],df_Locations['Capacity/FixedCost'])
    plt.title('Capacity of new warehouse vs fixed cost to open there')
    plt.show()

    sns.heatmap(df_Locations.corr(), annot=True, cmap='YlOrBr', fmt='.0%')
    fig = plt.gcf()
    fig.set_size_inches(10,8)
    plt.show()

    plt.bar(df_kit_revenue['Year'],df_kit_revenue['Revenue bln USD'])
    plt.title("Market's Revenue of kitchenware")
    plt.show()


    # evaluation demand old and new possible
    total_demand_Old=sum(df_cur_customer.iloc[:,6])
    total_demand_New=sum(df_new_customer.iloc[:,6])
    total_demand_Final_possible=(total_demand_New+total_demand_Old)
    print(total_demand_Final_possible)

    year_follow = [2023,2024,2025,2026]
    l=[0,1,3,4]
    ritmo=0.05
    for i in l:
        total_demand_could_serve_2026 = (total_demand_Old*(1+ritmo)**i)
        print(total_demand_could_serve_2026)

    #growth market kits for kitchen in the next years
    plt.figure()
    plt.plot(df_kit_revenue.iloc[:,0],df_kit_revenue.iloc[:,1], marker='o')
    plt.plot()
    plt.xlabel("time")
    plt.ylabel("growth market")
    plt.show()
    return

print(Visualization())
    
#%% Analysis

# In 2022, there is 183 units of capacity that it's not used
total_capacity_Bologna=7000
total_demand_31_customer_2022=6817
total_demand_all_customers_2022=16407

total_demand_served_old=sum(df_cur_customer.iloc[:,6])
exced_old=total_capacity_Bologna - total_demand_served_old


# if we consider a market volume's growth of 5% yearly --> Bologna warehouse demand that could be serve in 2026
total_demand_could_serve_2026_Bologna = (total_demand_served_old*(1.05)**4)
total_demand_could_serve_2026_Warehouses = (total_demand_all_customers_2022*(1.05)**4)
    






    
























