import streamlit as st
import plotly.graph_objects as go
from gdeltdoc import GdeltDoc, Filters
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime


# Function to calculate moving average
def calculate_moving_average(data, col_name, window_size=30):
    """Calculates the moving average of the given data.
    
    Args:
        data (pd.Series): The data series to calculate the moving average on.
        window_size (int): The number of periods to consider for the moving average.
        
    Returns:
        pd.Series: The moving average series.
    """

    # Create a copy of the data
    smoothed_data = data.copy()

    # Calculate the moving average of the 'Average Tone' column
    smoothed_data[col_name] = smoothed_data[col_name].rolling(window=window_size, center=True).mean()

    return smoothed_data

def generate_timeline_chart(timeline_data_dict, timeline_type):
    fig = go.Figure()
    for composite_key, timeline_data in timeline_data_dict.items():
        if composite_key.split(":")[0] == timeline_type["search_api"]:
            keyword = composite_key.split(":")[1]
            fig.add_trace(go.Scatter(x=timeline_data['datetime'], y=timeline_data[timeline_type["col_name"]], mode='lines', name=keyword))
    fig.update_layout(title=timeline_type["title"],
                      xaxis_title='Date',
                      yaxis_title=timeline_type["col_name"],
                      legend_title='Data Type',
                      hovermode='x unified')
    return fig

def generate_artical_data(filters):
    all_articles = pd.DataFrame(columns=["keyword", "url", "title", "seendate", "domain", "language", "sourcecountry"])
    for keyword, f in filters.items():
        articles = gd.article_search(f)
        if not articles.empty:
            articles["keyword"] = keyword
            articles = articles[["keyword", "url", "title", "seendate", "domain", "language", "sourcecountry"]]
            articles["seendate"] = articles["seendate"].apply(lambda x: datetime.strptime(x, '%Y%m%dT%H%M%SZ').strftime('%b %d, %Y %H:%M'))
            all_articles = pd.concat([all_articles, articles])
    return all_articles

def process_timeline_data(filters, timeline_types):
    # Iterate over the filters for Timeline Tone
    raw_data = {}
    smoothed_data = {}
    for keyword, f in filters.items():
        for timeline_type in timeline_types:
            try:
                # Fetch timeline for the current filter
                timeline = gd.timeline_search(timeline_type["search_api"], f)
            except Exception as e:
                print(f"An error occurred while fetching timeline for keyword '{keyword}': {str(e)}")
                timeline = pd.DataFrame()  # Set timeline to an empty DataFrame
                
            # If timeline data was found, process it
            if not timeline.empty:
                timeline['datetime'] = pd.to_datetime(timeline['datetime'])
                timeline.sort_values('datetime', inplace=True)
                # Combine the timeline_type and keyword to create the key
                key = f"{timeline_type['search_api']}:{keyword}"
                raw_data[key] = timeline
                # Assuming 'smooth' is a function that returns the smoothed data
                smoothed_data[key] = calculate_moving_average(timeline, col_name=timeline_type["col_name"])

    return raw_data, smoothed_data

# Initialize the GDELTDoc
gd = GdeltDoc()

# Streamlit UI
st.title('GDELT Search Interface')

# Sidebar for input
st.sidebar.header('Search Filters')
keyword1 = st.sidebar.text_input('Keyword 1', 'climate change')
keyword2 = st.sidebar.text_input('Keyword 2', 'hurricane')
keyword3 = st.sidebar.text_input('Keyword 3', 'tidal wave')
start_date = st.sidebar.date_input('Start Date', value=pd.to_datetime("2020-05-10"))
end_date = st.sidebar.date_input('End Date', value=pd.to_datetime("2021-05-11"))
domain = st.sidebar.text_input('Domain', 'bbc.co.uk,nytimes.com')
country = st.sidebar.text_input('Country', 'UK,US')
theme = st.sidebar.text_input('Theme', '')

# Timeline types
timeline_types = [{ "search_api": 'timelinetone', "title": "Average Tone", "col_name": "Average Tone" },
                  { "search_api": 'timelinevol', "title": "Volume As % Of Total", "col_name": "Volume Intensity" },
                  { "search_api": 'timelinevolraw', "title": "Volume Of Total Articles", "col_name": "Article Count" }]

# Button to perform search
if st.sidebar.button('Search'):
    filters = {}
    keywords = [keyword1, keyword2, keyword3]
    if len(domain.split(',')) == 1:
        domains = domain.strip() if domain else []
    else:
        domains = [d.strip() for d in domain.split(',')] if domain else []

    if len(country.split(',')) == 1:
        countries = country.strip() if country else []
    else:
        countries = [c.strip() for c in country.split(',')] if country else []

    for keyword in keywords:
        f = Filters(
            keyword=keyword,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            domain=domains,
            country=countries,
            theme=theme
        )
        filters[keyword] = f

    # Retrieve the article data and store it in the session state
    all_articles = generate_artical_data(filters)
    st.session_state.articles = all_articles


    # Retrieve the timeline data and store it in the session state
    raw_data, smoothed_data = process_timeline_data(filters, timeline_types)
    st.session_state.raw_data = raw_data
    st.session_state.smoothed_data = smoothed_data

# Display all the components    

# Display all the Timelines
tab = st.selectbox("Select a view", ("Raw Data", "Smoothed Data"))
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = {}
    st.session_state.smoothed_data = {}
if tab == "Raw Data":
    for timeline_type in timeline_types:
        st.plotly_chart(generate_timeline_chart(st.session_state.raw_data,timeline_type))   
else:
    for timeline_type in timeline_types:
        st.plotly_chart(generate_timeline_chart(st.session_state.smoothed_data,timeline_type))

# Display the articles
if 'articles' not in st.session_state:
    st.session_state.articles = pd.DataFrame()
if not st.session_state.articles.empty:
    st.write("Articles:")
    st.dataframe(st.session_state.articles, column_config={"url": st.column_config.LinkColumn(display_text="Link")})
else:
    st.write("No articles found.")