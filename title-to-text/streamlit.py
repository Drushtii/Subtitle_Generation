import streamlit as st
from subtitle import subtitle
from streamlit_option_menu import option_menu

st.set_page_config(page_title="subtitle generator👋", layout="wide")


class MultiApp:

    def __init__(self):
        self.apps = []

    def add_app(self, title, func):

        self.apps.append({"title": title, "function": func})

    def run():
        with st.sidebar:
            app = option_menu(
                menu_title="subtitle generator 👋 ",
                options=[
                    "Home",
                    "video-to-subtitle",
                ],
                menu_icon="robot",
                default_index=0,
                styles={
                    "container": {"padding": "5!important"},
                    "icon": {"color": "white", "font-size": "20px"},
                    "nav-link": {
                        "color": "white",
                        "font-size": "18px",
                        "text-align": "left",
                        "margin": "2.5px",
                        "--hover-color": "grey",
                        "padding": "5px",
                        "border-radius": "2.5px",
                        "white-space": "no-wrap",
                    },
                    "nav-link-selected": {"background-color": "#ADD8E6"},
                    "menu-title": {"color": "white"},
                },
            )
        if app == "Home":
            st.subheader("Welcome to subtitle generator!** 👋")
        if app == "video-to-subtitle":
            subtitle()

    run()
