import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Click Competition Dashboard", layout="wide")
st.title("Click Competition Dashboard 🎯")

# --- Sidebar: Data Upload ---
st.sidebar.header("🔄 Upload Your Click Competition Data")
with st.sidebar.expander("📖 Data Format Guide & Sample"):
    st.markdown("""
    Your data should have these columns:  
    - `Contestant id`: Unique ID for each contestant  
    - `Name`: Contestant full name  
    - `gender`: Gender of contestant  
    - `Location`: City or country  
    - `number of clicks/ points`: Number of clicks by contestant (the main metric)  
    - `Date of Participation`: Date of participation (YYYY-MM-DD)  
    - `Profile Creation Date`: Date contestant joined  
    - `time_spent_seconds`: (Optional) Time spent on the page in seconds (if you want to add engagement rate)
    
    Example columns in your Excel:
    ```
    Contestant id,Name,Age,rank,email,gender,number of clicks/ points,
    Date of Participation,Location,Profile Creation Date,Device/Browser Info
    ```
    """)

uploaded_file = st.sidebar.file_uploader(
    "Upload your dataset (Excel .xlsx file)", 
    type=["xlsx"]
)

# --- Data loading and processing function ---
@st.cache_data
def load_and_process_click_data(file):
    df = pd.read_excel(file)

    # Rename columns for easier handling
    df = df.rename(columns={
        "Contestant id": "user_id",
        "Name": "name",
        "gender": "gender",
        "Location": "location",
        "number of clicks/ points": "num_clicks",
        "Date of Participation": "date_participated",
        "Profile Creation Date": "profile_creation_date",
        "Device/Browser Info": "device",
        "rank": "provided_rank"
    })

    # Convert data types as needed
    df['date_participated'] = pd.to_datetime(df['date_participated'], errors='coerce')
    df['profile_creation_date'] = pd.to_datetime(df['profile_creation_date'], errors='coerce')

    # If 'num_clicks' is not numeric, convert to int (safely)
    df['num_clicks'] = pd.to_numeric(df['num_clicks'], errors='coerce').fillna(0).astype(int)

    # Calculate rank by num_clicks descending - if you want to use the provided rank, comment next two lines
    df = df.sort_values('num_clicks', ascending=False)
    df['rank'] = df['num_clicks'].rank(method='min', ascending=False).astype(int)

    # If you want, use the provided rank from your file instead:
    # df['rank'] = pd.to_numeric(df['provided_rank'], errors='coerce').fillna(0).astype(int)

    # If you have time spent info, calculate click rate (optional; not in your provided sheet)
    # For now we skip click_rate due to no time_spent_seconds column.

    return df

if uploaded_file is not None:
    try:
        df = load_and_process_click_data(uploaded_file)
        st.success("✅ Data loaded successfully!")
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        st.stop()
else:
    st.info("Please upload your click competition Excel dataset to proceed.")
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("🔍 Filters")

# Date filter
date_min = df['date_participated'].min().date()
date_max = df['date_participated'].max().date()

selected_dates = st.sidebar.date_input("Date range", [date_min, date_max], min_value=date_min, max_value=date_max)

# Location filter
locations = st.sidebar.multiselect("Select Locations", options=sorted(df['location'].dropna().unique()), default=sorted(df['location'].dropna().unique()))

# Gender filter
genders = st.sidebar.multiselect("Select Gender", options=sorted(df['gender'].dropna().unique()), default=sorted(df['gender'].dropna().unique()))

# Rank filter
rank_min = int(df['rank'].min())
rank_max = int(df['rank'].max())

rank_range = st.sidebar.slider(
    "Select Rank Range",
    min_value=rank_min,
    max_value=rank_max,
    value=(rank_min, rank_max)
)

# Filter dataframe based on sidebar selections
filtered_df = df[
    (df['date_participated'].dt.date >= selected_dates[0]) &
    (df['date_participated'].dt.date <= selected_dates[1]) &
    (df['location'].isin(locations)) &
    (df['gender'].isin(genders)) &
    (df['rank'] >= rank_range[0]) &
    (df['rank'] <= rank_range[1])
]

if filtered_df.empty:
    st.warning("No data matches the selected filters.")
    st.stop()

# --- Tabs for analysis ---
tabs = st.tabs(["Overview", "Leaderboard", "Clicks Analysis", "Demographics", "Raw Data"])

# TAB 1: Overview
with tabs[0]:
    st.header("🎯 Competition Overview")
    total_clicks = filtered_df['num_clicks'].sum()
    total_contestants = filtered_df['user_id'].nunique()
    avg_clicks = filtered_df['num_clicks'].mean()
    max_clicks = filtered_df['num_clicks'].max()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Clicks", f"{total_clicks:,}")
    col2.metric("Total Contestants", f"{total_contestants:,}")
    col3.metric("Average Clicks per Contestant", f"{avg_clicks:.1f}")
    col4.metric("Max Clicks", f"{max_clicks:,}")

    # Monthly Clicks Trend
    trend_df = filtered_df.copy()
    trend_df['month'] = trend_df['date_participated'].dt.to_period('M').astype(str)
    monthly_clicks = trend_df.groupby('month')['num_clicks'].sum().reset_index()
    fig_trend = px.line(monthly_clicks, x='month', y='num_clicks', title='Monthly Clicks Trend', markers=True)
    st.plotly_chart(fig_trend, use_container_width=True)

# TAB 2: Leaderboard
with tabs[1]:
    st.header("🏆 Leaderboard")
    st.write("Top 20 contestants by clicks")
    st.dataframe(
        filtered_df.sort_values('rank').head(20)[['rank', 'name', 'gender', 'location', 'num_clicks']],
        use_container_width=True
    )

    # Clicks distribution by gender
    fig_box = px.box(
        filtered_df, 
        x='gender', 
        y='num_clicks', 
        title='Clicks Distribution by Gender', 
        points='all',
        color='gender'
    )
    st.plotly_chart(fig_box, use_container_width=True)

# TAB 3: Clicks Analysis
with tabs[2]:
    st.header("📈 Clicks Performance Analysis")

    # Histogram of clicks
    fig_hist = px.histogram(
        filtered_df, 
        x='num_clicks', 
        nbins=30, 
        color='gender', 
        marginal='box',
        title="Clicks Histogram by Gender"
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    # Scatter plot: clicks vs age (if age present)
    if 'Age' in filtered_df.columns:
        fig_scatter = px.scatter(
            filtered_df, 
            x='Age', 
            y='num_clicks', 
            color='gender',
            size='num_clicks',
            hover_data=['name', 'location', 'rank'],
            title="Clicks vs Age"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("Age column not found in data for scatter plot.")

# TAB 4: Demographics
with tabs[3]:
    st.header("🌍 Demographics and Location Analysis")

    # Total clicks by location bar chart
    loc_df = filtered_df.groupby('location')['num_clicks'].sum().reset_index()
    fig_loc = px.bar(loc_df.sort_values('num_clicks', ascending=False), x='location', y='num_clicks', title='Total Clicks by Location', labels={'num_clicks': 'Total Clicks', 'location': 'Location'})
    st.plotly_chart(fig_loc, use_container_width=True)

    # Gender distribution pie chart
    gender_counts = filtered_df['gender'].value_counts().reset_index()
    gender_counts.columns = ['gender', 'count']
    fig_pie = px.pie(gender_counts, names='gender', values='count', title='Contestants by Gender')
    st.plotly_chart(fig_pie, use_container_width=True)

# TAB 5: Raw Data
with tabs[4]:
    st.header("📋 Raw Data")
    st.dataframe(filtered_df, use_container_width=True)

    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download filtered data as CSV",
        data=csv,
        file_name='filtered_click_competition_data.csv',
        mime='text/csv'
    )
