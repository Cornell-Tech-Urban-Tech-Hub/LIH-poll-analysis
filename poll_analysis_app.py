"""
Interactive Streamlit app for analyzing poll responses from webinar sessions.

Run with: uv run streamlit run poll_analysis_app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


@st.cache_data
def load_data():
    """Load and cache the poll responses data."""
    df = pd.read_csv("poll-responses.csv")
    return df


def get_session_summary(df):
    """Get summary statistics by session."""
    summary = (
        df.groupby(["Webinar Date", "Month Year", "Webinar Title (Full)"])
        .agg({"Name": "nunique", "Question": "nunique", "Answer": "count"})
        .rename(
            columns={
                "Name": "Unique Respondents",
                "Question": "Unique Questions",
                "Answer": "Total Responses",
            }
        )
        .reset_index()
    )
    # Sort by date in reverse order (most recent first)
    summary = summary.sort_values("Webinar Date", ascending=False)
    return summary


def get_question_totals(df, session_filter=None):
    """Get totals for each question, optionally filtered by session."""
    if session_filter:
        df = df[df["Month Year"] == session_filter]

    totals = (
        df.groupby(["Webinar Date", "Month Year", "Webinar Title (Full)", "Question", "Answer"])
        .size()
        .reset_index(name="Count")
    )
    # Sort by date in reverse order (most recent first)
    totals = totals.sort_values("Webinar Date", ascending=False)
    return totals


def main():
    st.set_page_config(page_title="Poll Response Analysis", layout="wide")

    st.title("📊 Poll Response Analysis")
    st.markdown("---")

    # Load data
    try:
        df = load_data()
        st.success(f"✓ Loaded {len(df):,} responses from {df['Name'].nunique()} respondents")
    except FileNotFoundError:
        st.error("Could not find poll-responses.csv file. Please make sure it's in the same directory.")
        return

    # Sidebar filters
    st.sidebar.header("Filters")

    # Session filter - sort by date
    session_dates = df[["Webinar Date", "Month Year"]].drop_duplicates()
    session_dates = session_dates.sort_values("Webinar Date")
    sessions = session_dates["Month Year"].tolist()
    selected_session = st.sidebar.selectbox(
        "Select Session",
        ["All Sessions"] + sessions,
        index=0,
    )

    # Apply session filter
    if selected_session != "All Sessions":
        filtered_df = df[df["Month Year"] == selected_session]
    else:
        filtered_df = df

    # Question filter
    questions = sorted(filtered_df["Question"].unique())
    selected_question = st.sidebar.selectbox(
        "Select Question",
        ["All Questions"] + questions,
        index=0,
    )

    # Apply question filter
    if selected_question != "All Questions":
        filtered_df = filtered_df[filtered_df["Question"] == selected_question]

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📈 Session Overview", "📊 Question Totals", "🔍 Individual Responses", "📉 Analytics"]
    )

    # Tab 1: Session Overview
    with tab1:
        st.header("Session Overview")

        session_summary = get_session_summary(df)
        # Calculate height to show all rows (35px per row + 38px header)
        table_height = len(session_summary) * 35 + 38
        st.dataframe(
            session_summary,
            use_container_width=True,
            hide_index=True,
            height=table_height,
        )

        # Session metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Sessions", len(sessions))
        with col2:
            st.metric("Total Respondents", df["Name"].nunique())
        with col3:
            st.metric("Total Responses", len(df))

    # Tab 2: Question Totals
    with tab2:
        st.header("Question Totals")

        # Get question totals
        question_totals = get_question_totals(
            df,
            session_filter=None if selected_session == "All Sessions" else selected_session,
        )

        # Group by session (Webinar Date, Month Year, Webinar Title)
        sessions_in_view = question_totals[["Webinar Date", "Month Year", "Webinar Title (Full)"]].drop_duplicates()

        for _, session_row in sessions_in_view.iterrows():
            session_date = session_row["Webinar Date"]
            month_year = session_row["Month Year"]
            webinar_title = session_row["Webinar Title (Full)"]

            # Format date nicely (e.g., "January 2024")
            formatted_date = pd.to_datetime(str(session_date), format="%Y%m%d").strftime("%B %Y")

            # Create session header
            st.subheader(f"📅 {formatted_date} - {webinar_title}")

            # Filter data for this session
            session_data = question_totals[
                (question_totals["Webinar Date"] == session_date) &
                (question_totals["Month Year"] == month_year) &
                (question_totals["Webinar Title (Full)"] == webinar_title)
            ]

            # Group by question for this session
            questions_in_session = session_data["Question"].unique()

            for question in questions_in_session:
                with st.expander(f"📝 {question}", expanded=False):
                    question_data = session_data[session_data["Question"] == question]

                    # Calculate percentages
                    total = question_data["Count"].sum()
                    question_data = question_data.copy()
                    question_data["Percentage"] = (
                        question_data["Count"] / total * 100
                    ).round(1)

                    # Display data
                    display_data = question_data[["Answer", "Count", "Percentage"]].sort_values(
                        "Count", ascending=False
                    )
                    st.dataframe(display_data, use_container_width=True, hide_index=True)

                    # Pie chart with unique key
                    fig = px.pie(
                        question_data,
                        values="Count",
                        names="Answer",
                        title="Response Distribution",
                    )
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{session_date}_{question}")

            st.markdown("---")

    # Tab 3: Individual Responses
    with tab3:
        st.header("Individual Responses")

        # Additional filters for individual responses
        col1, col2 = st.columns(2)

        with col1:
            # Respondent filter
            respondents = sorted(filtered_df["Name"].unique())
            selected_respondent = st.selectbox(
                "Filter by Respondent",
                ["All Respondents"] + respondents,
                index=0,
            )

        with col2:
            # City filter
            cities = sorted(filtered_df["City, State"].unique())
            selected_city = st.selectbox(
                "Filter by City",
                ["All Cities"] + cities,
                index=0,
            )

        # Apply additional filters
        display_df = filtered_df.copy()

        if selected_respondent != "All Respondents":
            display_df = display_df[display_df["Name"] == selected_respondent]

        if selected_city != "All Cities":
            display_df = display_df[display_df["City, State"] == selected_city]

        # Display count
        st.info(f"Showing {len(display_df)} responses")

        # Display data
        display_columns = [
            "Webinar Date",
            "Month Year",
            "Webinar Title (Full)",
            "Name",
            "City, State",
            "State",
            "Population Range",
            "Question",
            "Answer",
        ]

        st.dataframe(
            display_df[display_columns],
            use_container_width=True,
            hide_index=True,
        )

        # Download button
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv,
            file_name="filtered_poll_responses.csv",
            mime="text/csv",
        )

    # Tab 4: Analytics
    with tab4:
        st.header("Analytics Dashboard")

        # Response distribution by state
        st.subheader("Responses by State")
        state_counts = filtered_df["State"].value_counts().reset_index()
        state_counts.columns = ["State", "Count"]

        fig = px.bar(
            state_counts.head(20),
            x="State",
            y="Count",
            title="Top 20 States by Response Count",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Population range distribution
        st.subheader("Responses by Population Range")
        pop_counts = filtered_df["Population Range"].value_counts().reset_index()
        pop_counts.columns = ["Population Range", "Count"]

        fig = px.pie(
            pop_counts,
            values="Count",
            names="Population Range",
            title="Distribution by City Population Range",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Top respondents
        st.subheader("Most Active Respondents")
        top_respondents = (
            filtered_df.groupby(["Name", "City, State"])
            .size()
            .reset_index(name="Response Count")
            .sort_values("Response Count", ascending=False)
            .head(15)
        )
        st.dataframe(top_respondents, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
