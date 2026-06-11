import streamlit as st
import pandas as pd
import requests
import io
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# ----------------------------
# Page configuration
# ----------------------------
st.set_page_config(page_title="IPC Sessions Performance", layout="wide")

# ----------------------------
# Data loading (cached)
# ----------------------------
API_TOKEN = "758d7eba264755945b857a816322859ca94f3fc3"
CSV_URL = "https://eu.kobotoolbox.org/api/v2/assets/anSxARjeQhpiJnBunZbbUP/export-settings/esiT387NvdJHWf7kP6CbGKg/data.csv"

@st.cache_data(ttl=3600)
def load_data():
    response = requests.get(CSV_URL, headers={"Authorization": f"Token {API_TOKEN}"})
    if response.status_code == 200:
        csv_data = io.StringIO(response.text)
        df = pd.read_csv(csv_data, sep=';')
        
        # Derived columns
        females_cols = ['Females reached: 0 - 9 yrs','Females reached: 10 - 14 yrs',
                        'Females reached: 15 - 19 yrs','Females reached: 20 - 24 yrs',
                        'Females reached: 25 yrs and above']
        df['Tot_females_reached'] = df[females_cols].sum(axis=1)
        
        wr_cols = ['Females reached: 10 - 14 yrs','Females reached: 15 - 19 yrs',
                   'Females reached: 20 - 24 yrs','Females reached: 25 yrs and above']
        df['WRA'] = df[wr_cols].sum(axis=1)
        
        pwd_cols = ['PWD 0 - 9 yrs reached','PWD 10 - 14 yrs reached','PWD 15 - 19 yrs reached',
                    'PWD 20 - 24 yrs reached','PWD 25 yrs and above reached']
        df['Tot_PWD'] = df[pwd_cols].sum(axis=1)
        
        LGBTQI_cols = ['0 - 9 yrs reached','10 - 14 yrs reached','15 - 19 yrs reached',
                       '20 - 24 yrs reached','25 yrs and above reached']
        df['Tot_LGBTQI'] = df[LGBTQI_cols].sum(axis=1)
        
        males_cols = ['Males reached: 0 - 9 yrs','Males reached: 10 - 14 yrs','Males reached: 15 - 19 yrs',
                      'Males reached: 20 - 24 yrs','Males reached: 25 yrs and above']
        df['Tot_males_reached'] = df[males_cols].sum(axis=1)
        
        no_reached_cols = ['Tot_females_reached','WRA','Tot_PWD','Tot_LGBTQI','Tot_males_reached']
        df['No_reached'] = df[no_reached_cols].sum(axis=1)
        
        # Month column
        df['month'] = pd.to_datetime(df['start']).dt.month_name()
        
        return df
    else:
        st.error(f"Error loading data: {response.status_code}")
        return pd.DataFrame()

df = load_data()
if df.empty:
    st.stop()

# ----------------------------
# Targets dictionary
# ----------------------------
targets = {
    'Kwale':14780, 'Marsabit':8257, 'Kilifi':16737, 'Nairobi':24603, 'Samburu':13158,
    'West Pokot':15955, 'Mandera':12909, 'Kajiado':13067, 'Homa Bay':9523, 'Narok':11969,
    'Elgeyo Marakwet':9857, 'Baringo':7375, 'Garissa':11808
}
target_df = pd.DataFrame(list(targets.items()), columns=['County', 'Target'])

# ----------------------------
# Helper: WRA achievement plot data
# ----------------------------
def prepare_wra_data():
    df_filtered = df[df['County of operation'].isin(targets.keys())]
    agg = df_filtered.groupby('County of operation')['WRA'].sum().reset_index()
    agg.columns = ['County', 'WRA_Reached']
    merged = agg.merge(target_df, on='County', how='right').fillna(0)
    merged['Achievement_Pct'] = (merged['WRA_Reached'] / merged['Target']) * 100
    merged['Achievement_Pct'] = merged['Achievement_Pct'].clip(upper=100)
    return merged.sort_values('Achievement_Pct', ascending=False)

plot_df = prepare_wra_data()

# ----------------------------
# Page 1: WRA Achievement
# ----------------------------
def page_wra_achievement():
    st.markdown("## 🎯 WRA Achievement by County")
    
    # ---- Donut Chart ----
    total_actual = df['WRA'].sum()
    total_target = sum(targets.values())
    total_gap = total_target - total_actual
    overall_rate = (total_actual / total_target * 100).round(1)
    
    fig_donut, ax = plt.subplots(figsize=(5,4))
    sizes = [total_actual, total_gap]
    labels = [f'Achieved\n{total_actual:,}', f'Gap\n{total_gap:,}']
    colors_donut = ['orange', 'purple']
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors_donut,
                                      autopct='%1.1f%%', startangle=90,
                                      wedgeprops=dict(width=0.3))
    centre_circle = plt.Circle((0,0), 0.70, fc='none')
    ax.add_artist(centre_circle)
    ax.text(0, 0, f'Overall\nAchievement\n{overall_rate}%',
            ha='center', va='center', fontsize=12, fontweight='bold')
    ax.set_title('Overall Performance Summary')
    st.pyplot(fig_donut)
    plt.close(fig_donut)
    
    st.markdown("---")
    
    # ---- Interactive Controls ----
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        sort_by = st.selectbox("Sort by", options=['Achievement_Pct', 'WRA_Reached', 'Target'],
                               index=0, key="sort_by")
    with col2:
        threshold1 = st.slider("Critical < threshold (%)", 5, 33, 15, 1, key="th1")
    with col3:
        threshold2 = st.slider("Below Target < threshold (%)", 30, 44, 32, 1, key="th2")
    
    # ---- Bar Chart (Matplotlib) ----
    df_sorted = plot_df.sort_values(sort_by, ascending=True).copy()
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor('#F8F9FA')
    ax.set_facecolor('#F8F9FA')
    y_pos = np.arange(len(df_sorted))
    colors = ['#E74C3C' if p < threshold1 else '#F39C12' if p < threshold2 else '#27AE60'
              for p in df_sorted['Achievement_Pct']]
    ax.barh(y_pos, df_sorted['Achievement_Pct'], color=colors, edgecolor='white', linewidth=1.5)
    for i, (pct, wra, target) in enumerate(zip(df_sorted['Achievement_Pct'],
                                               df_sorted['WRA_Reached'],
                                               df_sorted['Target'])):
        ax.text(pct + 1, i, f'{pct:.1f}%', va='center', fontsize=10, fontweight='bold')
        ax.text(pct - 3, i, f'{wra:,}/{target:,}', va='center', ha='right', fontsize=8, color='#7F8C8D')
    ax.axvline(x=100, color='#2C3E50', linestyle='--', linewidth=2, alpha=0.7, label='Target (100%)')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(df_sorted['County'], fontsize=11)
    ax.set_xlabel('Achievement Percentage (%)', fontsize=12, fontweight='bold')
    ax.set_title('WRA Achievement by County (% of Target)', fontsize=16, fontweight='bold', pad=20, color='#2C3E50')
    ax.set_xlim(0, 100)
    ax.grid(axis='x', alpha=0.3, linestyle='--', color='#BDC3C7')
    legend_elements = [
        plt.Rectangle((0,0),1,1, facecolor='#E74C3C', label=f'Critical (< {threshold1:.0f}%)'),
        plt.Rectangle((0,0),1,1, facecolor='#F39C12', label=f'Below Target ({threshold1:.0f}–{threshold2:.0f}%)'),
        plt.Rectangle((0,0),1,1, facecolor='#27AE60', label=f'Good Progress (> {threshold2:.0f}%)')
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10)
    st.pyplot(fig)
    plt.close(fig)
    
    st.markdown("---")
    
    # ---- County Summary Table ----
    st.markdown("## 📍 County‑Level Reach Summary")
    available_months = sorted(df['month'].dropna().unique(),
                              key=lambda x: datetime.strptime(x, '%B').month)
    month_choice = st.selectbox("Select Month", options=['All Months'] + available_months, index=0)
    
    metrics_cols = ['Tot_females_reached', 'WRA', 'Tot_PWD', 'Tot_LGBTQI', 'Tot_males_reached']
    filtered = df if month_choice == 'All Months' else df[df['month'] == month_choice]
    summary = filtered.groupby('County of operation')[metrics_cols].sum().reset_index()
    summary.columns = [col.replace('_', ' ').title() for col in summary.columns]
    
    st.dataframe(summary, use_container_width=True)
    
    # Overall totals
    st.markdown("**Overall Totals**")
    for col in metrics_cols:
        total = filtered[col].sum()
        st.markdown(f"- Total {col.replace('_', ' ').title()}: **{total:,.0f}**")
    
# ----------------------------
# Page 2: Monthly Org Summary
# ----------------------------
def page_monthly_org_summary():
    st.markdown("## 🏥 Organization Monthly Performance Dashboard")
    available_months = sorted(df['month'].dropna().unique(),
                              key=lambda x: datetime.strptime(x, '%B').month)
    month_choice = st.selectbox("Select Month", options=['All Months'] + available_months, index=0, key="month_org")
    
    filtered = df if month_choice == 'All Months' else df[df['month'] == month_choice]
    
    # WRA summary (all orgs)
    wra_summary = filtered.groupby('Organisation unit name').agg(
        Num_Sessions=('start', 'size'),
        Total_WRA=('WRA', 'sum')
    ).reset_index()
    wra_summary['Avg_WRA_per_Session'] = (wra_summary['Total_WRA'] / wra_summary['Num_Sessions']).round(0).astype(int)
    wra_summary = wra_summary.sort_values('Num_Sessions', ascending=False)
    
    # LGBTQI summary (specific orgs)
    orgs_of_interest = ['AYARHEP', 'Malindi Desire CBO']
    lgbtqi_filtered = filtered[filtered['Organisation unit name'].isin(orgs_of_interest)]
    lgbtqi_summary = lgbtqi_filtered.groupby('Organisation unit name').agg(
        Num_Sessions=('start', 'size'),
        Total_LGBTQI=('Tot_LGBTQI', 'sum')
    ).reset_index()
    lgbtqi_summary['Avg_LGBTQI_per_Session'] = (lgbtqi_summary['Total_LGBTQI'] / lgbtqi_summary['Num_Sessions']).round(0).astype(int)
    lgbtqi_summary = lgbtqi_summary.sort_values('Num_Sessions', ascending=False)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### 📊 Monthly WRA Summary  \n**Month:** {month_choice}")
        st.dataframe(wra_summary, use_container_width=True)
        total_orgs = len(wra_summary)
        total_sessions = wra_summary['Num_Sessions'].sum()
        total_wra = wra_summary['Total_WRA'].sum()
        avg_wra = (total_wra / total_sessions).round(2) if total_sessions else 0
        st.markdown(f"""
        **Summary Statistics**  
        - Total Organizations: **{total_orgs}**  
        - Total Sessions: **{total_sessions:,}**  
        - Total WRA Reached: **{total_wra:,.0f}**  
        - Avg WRA/Session: **{avg_wra}**
        """)
    with col2:
        st.markdown(f"### 🏳️‍🌈 Monthly LGBTQI Summary  \n**Month:** {month_choice}  \n*(AYARHEP, Malindi Desire CBO)*")
        st.dataframe(lgbtqi_summary, use_container_width=True)
        if not lgbtqi_summary.empty:
            total_orgs_lgbt = len(lgbtqi_summary)
            total_sessions_lgbt = lgbtqi_summary['Num_Sessions'].sum()
            total_lgbtqi = lgbtqi_summary['Total_LGBTQI'].sum()
            avg_lgbtqi = (total_lgbtqi / total_sessions_lgbt).round(2) if total_sessions_lgbt else 0
            st.markdown(f"""
            **Summary Statistics**  
            - Total Organizations: **{total_orgs_lgbt}**  
            - Total Sessions: **{total_sessions_lgbt:,}**  
            - Total LGBTQI Reached: **{total_lgbtqi:,.0f}**  
            - Avg LGBTQI/Session: **{avg_lgbtqi}**
            """)

# ----------------------------
# Page 3: People & Sessions (cascade)
# ----------------------------
def page_people_sessions():
    st.markdown("## 👥 Organization Performance Dashboard")
    available_counties = sorted(df['County of operation'].dropna().unique())
    available_months = ['All Months'] + sorted(df['month'].dropna().unique(),
                                               key=lambda x: datetime.strptime(x, '%B').month)
    
    county = st.selectbox("Step 1: Select County", options=['Select County'] + available_counties)
    if county != 'Select County':
        orgs = sorted(df[df['County of operation'] == county]['Organisation unit name'].dropna().unique())
        org = st.selectbox("Step 2: Select Organization", options=['Select Organization'] + orgs)
        month = st.selectbox("Step 3: Filter by Month (Optional)", options=available_months)
    else:
        org = 'Select Organization'
        month = 'All Months'
        st.info("Please select a county first")
    
    if county != 'Select County' and org != 'Select Organization':
        mask = (df['County of operation'] == county) & (df['Organisation unit name'] == org)
        filtered = df[mask]
        if month != 'All Months':
            filtered = filtered[filtered['month'] == month]
        
        if not filtered.empty:
            person_col = 'The name of the person conducting the session?'
            wra_col = 'WRA'
            if person_col in filtered.columns:
                person_sessions = filtered.groupby(person_col).agg(
                    Sessions=('start', 'size'),
                    Total_WRA=(wra_col, 'sum')
                ).reset_index()
                person_sessions['Avg WRA / Session'] = (person_sessions['Total_WRA'] / person_sessions['Sessions']).round(2)
                person_sessions = person_sessions.rename(columns={person_col: 'Person'})
                person_sessions = person_sessions.sort_values('Sessions', ascending=False)
                
                st.markdown(f"**Organization:** {org}  \n**County:** {county}  \n**Period:** {month}")
                st.dataframe(person_sessions, use_container_width=True)
                total_people = len(person_sessions)
                total_sessions = person_sessions['Sessions'].sum()
                total_wra = person_sessions['Total_WRA'].sum()
                st.markdown(f"""
                📊 **Summary**  
                - 👥 Total people: {total_people}  
                - 📅 Total sessions: {total_sessions}  
                - 👩‍👩‍👧‍👧 Total WRA reached: {total_wra:,.0f}
                """)
            else:
                st.error("Column for person name not found")
        else:
            st.warning("No data for the selected filters")
    elif county != 'Select County' and org == 'Select Organization':
        st.info("Please select an organization")

# ----------------------------
# Navigation & Authentication for Page 1
# ----------------------------
PAGE1_PASSWORD = "secret123"   # change as needed

if "authenticated_page1" not in st.session_state:
    st.session_state.authenticated_page1 = False

# Sidebar navigation
#strest.sidebar.image("NEW PS KENYA LOGO 2024 (1).png", width=200)  # adjust path or remove
st.sidebar.title("Pages")
page = st.sidebar.radio("Go to", ["Welcome", "WRA Achievement", "Monthly Org Summary", "People & Sessions"])

# Welcome page
if page == "Welcome":
    st.title("👋 Welcome to the WRA Dashboard Suite")
    st.markdown("Use the sidebar to navigate between reports.")
    st.markdown("---")
    st.markdown("### Data source: KoboToolbox")
    st.markdown(f"Total records loaded: {len(df):,}")

# Page 1 with password
elif page == "WRA Achievement":
    if not st.session_state.authenticated_page1:
        st.markdown("### 🔒 This page is password protected")
        pwd = st.text_input("Password", type="password")
        if st.button("Submit"):
            if pwd == PAGE1_PASSWORD:
                st.session_state.authenticated_page1 = True
                st.rerun()
            else:
                st.error("Incorrect password")
    else:
        page_wra_achievement()

# Other pages (no password)
elif page == "Monthly Org Summary":
    page_monthly_org_summary()
elif page == "People & Sessions":
    page_people_sessions()