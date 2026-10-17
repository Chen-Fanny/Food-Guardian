"""
Main Streamlit Application Entrypoint.
Food Guardian: A Knowledge-Guided AI Agent for Smart Food Inventory Management and Household Food Waste Reduction.
[Status: Proposal Stage / Scaffold]
"""

import streamlit as st


def main():
    st.set_page_config(
        page_title="Food Guardian | Proposal Stage",
        page_icon="🥑",
        layout="wide",
    )

    st.title("🥑 Food Guardian")
    st.subheader(
        "A Knowledge-Guided AI Agent for Smart Food Inventory Management and Household Food Waste Reduction"
    )

    st.info(
        "ℹ️ **Current Status: Project Proposal & Architecture Setup**\n\n"
        "The application modules are currently under active development. "
        "Please refer to `README.md` and project documentation for system architecture and development milestones."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📋 Planned System Capabilities")
        st.markdown(
            """
            - **Inventory Management**: Track and manage household food items (CRUD).
            - **Date Reminders**: Intelligent tracking of expiration and *Use By* vs *Best Before* labels.
            - **AI Agent Cooking Advisor**: LLM tool-calling agent to recommend recipes using expiring ingredients.
            - **Food Knowledge Retrieval**: Domain knowledge on proper storage methods and shelf-life extension.
            - **Waste Analytics**: Data-driven insights on food consumption and waste reduction trends.
            """
        )

    with col2:
        st.markdown("### 🛠️ Architecture & Tech Stack")
        st.markdown(
            """
            - **Frontend**: Streamlit
            - **Data Layer**: SQLite & Pandas
            - **AI Engine**: LLM with Tool Calling Architecture
            - **Knowledge Source**: Structured JSON Food Knowledge Base
            """
        )


if __name__ == "__main__":
    main()
