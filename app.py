import streamlit as st
import psycopg2
import sqlite3
from psycopg2 import sql
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

# Configuration de base
st.set_page_config(page_title="Suivi des Prix Amazon", layout="wide")

# Constantes
PRODUCTS = {
    "manette": {
        "url": "https://www.amazon.fr/Manette-Xbox-rouge-sans-Fil/dp/B08SRMPBRF/",
        "name": "Manette Xbox Rouge Sans Fil"
    },
    "ram": {
        "url": "https://www.amazon.fr/Timetec-PC4-25600-Unbuffered-Compatible-Notebook/dp/B098TYN671/",
        "name": "RAM Timetec 32GB"
    },
    "housse": {
        "url": "https://www.amazon.fr/eXtremeRate-Antid%C3%A9rapante-Protection-Ergonomique-Capuchons-Gris/dp/B08LZB4LKR/",
        "name": "Housse eXtremeRate Grip"
    },
    "kit_charge": {
        "url": "https://www.amazon.fr/Xbox-Play-Charge-Kit-voor/dp/B08FCXLB8Z/",
        "name": "Kit charge Xbox Series"
    },
    "sisma_case": {
        "url": "https://www.amazon.fr/sisma-Rangement-Compatible-Pochette-Transport/dp/B0CF9B16DV/",
        "name": "Étui Sisma Xbox Series"
    }
}

[rest of the code remains unchanged...]
