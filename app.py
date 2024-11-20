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

class Database:
    def __init__(self):
        self.is_local = 'DATABASE_URL' not in os.environ
        if self.is_local:
            self.db_path = "amazon_prices.db"
            self.init_sqlite()
        else:
            self.conn_string = os.environ['DATABASE_URL']
            self.init_postgres()

    def init_sqlite(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    url TEXT NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER REFERENCES products(id),
                    price REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            for product_info in PRODUCTS.values():
                cursor.execute('''
                    INSERT OR IGNORE INTO products (name, url)
                    VALUES (?, ?)
                ''', (product_info['name'], product_info['url']))
            conn.commit()

    def init_postgres(self):
        with psycopg2.connect(self.conn_string) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS products (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        url TEXT NOT NULL
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS prices (
                        id SERIAL PRIMARY KEY,
                        product_id INTEGER REFERENCES products(id),
                        price REAL NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                for product_info in PRODUCTS.values():
                    cursor.execute('''
                        INSERT INTO products (name, url)
                        VALUES (%s, %s)
                        ON CONFLICT (name) DO NOTHING
                    ''', (product_info['name'], product_info['url']))
                conn.commit()

    def save_prices(self, prices):
        if self.is_local:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for price_info in prices:
                    cursor.execute('SELECT id FROM products WHERE name = ?', 
                                 (price_info['Produit'],))
                    product_id = cursor.fetchone()[0]
                    cursor.execute('''
                        INSERT INTO prices (product_id, price)
                        VALUES (?, ?)
                    ''', (product_id, price_info['Prix']))
                conn.commit()
        else:
            with psycopg2.connect(self.conn_string) as conn:
                with conn.cursor() as cursor:
                    for price_info in prices:
                        cursor.execute('''
                            SELECT id FROM products WHERE name = %s
                        ''', (price_info['Produit'],))
                        product_id = cursor.fetchone()[0]
                        cursor.execute('''
                            INSERT INTO prices (product_id, price)
                            VALUES (%s, %s)
                        ''', (product_id, price_info['Prix']))
                    conn.commit()

    def get_price_history(self):
        if self.is_local:
            with sqlite3.connect(self.db_path) as conn:
                query = '''
                    SELECT 
                        products.name,
                        prices.price,
                        prices.timestamp
                    FROM prices
                    JOIN products ON prices.product_id = products.id
                    ORDER BY prices.timestamp DESC
                '''
                return pd.read_sql_query(query, conn)
        else:
            with psycopg2.connect(self.conn_string) as conn:
                query = '''
                    SELECT 
                        products.name,
                        prices.price,
                        prices.timestamp
                    FROM prices
                    JOIN products ON prices.product_id = products.id
                    ORDER BY prices.timestamp DESC
                '''
                return pd.read_sql_query(query, conn)

def setup_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = "/usr/bin/chromium"
    
    # Configuration pour Amazon France
    chrome_options.add_argument('--lang=fr-FR')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_argument('accept-language=fr-FR,fr;q=0.9')
    
    # Ajouter des préférences de langue et région
    chrome_options.add_experimental_option('prefs', {
        'intl.accept_languages': 'fr-FR,fr',
        'profile.default_content_settings.cookies': 1,
        'profile.default_content_settings.geolocation': 1
    })
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        st.error(f"Erreur lors de l'initialisation du driver: {str(e)}")
        return None
def handle_cookies(driver):
    try:
        wait = WebDriverWait(driver, 10)
        cookie_button = wait.until(EC.presence_of_element_located((By.ID, "sp-cc-accept")))
        cookie_button.click()
        time.sleep(1)
        return True
    except Exception:
        return False

def change_location(driver, postal_code="94310"):
    try:
        wait = WebDriverWait(driver, 10)
        delivery_button = wait.until(
            EC.element_to_be_clickable((By.ID, "nav-global-location-popover-link"))
        )
        delivery_button.click()
        time.sleep(2)
        
        postal_input = wait.until(EC.presence_of_element_located((By.ID, "GLUXZipUpdateInput")))
        postal_input.clear()
        postal_input.send_keys(postal_code)
        
        apply_button = wait.until(EC.element_to_be_clickable((By.ID, "GLUXZipUpdate")))
        apply_button.click()
        time.sleep(2)
        
        try:
            done_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "a-popover-footer")))
            done_button.click()
            time.sleep(1)
        except:
            pass
            
        return True
    except Exception:
        return False

def track_current_prices():
    driver = setup_driver()
    if not driver:
        st.error("Impossible d'initialiser le navigateur")
        return None
        
    current_prices = []
    cookies_handled = False
    
    try:
        for product in PRODUCTS.values():
            try:
                for attempt in range(3):
                    try:
                        url = product['url']
                        if 'amazon.' in url and not 'amazon.fr' in url:
                            url = url.replace('amazon.com', 'amazon.fr')
                        
                        driver.get(url)
                        time.sleep(5)
                        
                        if not cookies_handled:
                            handle_cookies(driver)
                            change_location(driver, "94310")
                            cookies_handled = True
                            time.sleep(2)

                        selectors = [
                            ".a-price .a-offscreen",
                            "span.a-price-whole",
                            "#corePrice_feature_div .a-price-whole"
                        ]
                        
                        price = None
                        for selector in selectors:
                            try:
                                element = WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                                )
                                price_text = element.get_attribute("textContent") or element.text
                                price_text = ''.join(filter(lambda x: x.isdigit() or x in ',.', price_text))
                                price = float(price_text.replace(",", ".").strip())
                                break
                            except:
                                continue
                                
                        if price:
                            current_prices.append({
                                'Produit': product['name'],
                                'Prix': round(price, 2)
                            })
                            break
                            
                    except Exception as e:
                        if attempt == 2:
                            st.error(f"Erreur pour {product['name']}: {str(e)}")
                            
            except Exception as e:
                st.error(f"Erreur pour {product['name']}: {str(e)}")
                continue
                
        return current_prices
        
    finally:
        if driver:
            driver.quit()

def should_update_price(db, product_name, new_price):
    """Vérifie si le prix a changé depuis la dernière mise à jour"""
    history_df = db.get_price_history()
    if history_df.empty:
        return True
    
    latest_price = history_df[history_df['name'] == product_name].iloc[0]['price'] if not history_df[history_df['name'] == product_name].empty else None
    
    if latest_price is None or abs(latest_price - new_price) > 0.01:  # Différence de plus d'un centime
        return True
    return False

def auto_check_prices():
    """Vérifie automatiquement les prix et ne les sauvegarde que s'ils ont changé"""
    db = Database()
    current_prices = track_current_prices()
    
    if current_prices:
        prices_changed = False
        for price_info in current_prices:
            if should_update_price(db, price_info['Produit'], price_info['Prix']):
                prices_changed = True
                break
        
        if prices_changed:
            db.save_prices(current_prices)
            now = datetime.now().strftime("%H:%M:%S")
            st.toast(f"🔄 Prix mis à jour à {now}")
        else:
            st.toast("📊 Pas de changement de prix détecté")

def display_price_history(db):
    history_df = db.get_price_history()
    
    if not history_df.empty:
        history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
        
        st.header("💰 Prix actuels")
        latest_prices = history_df.groupby('name').first().reset_index()
        
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(latest_prices[['name', 'price']], hide_index=True)
        with col2:
            total = latest_prices['price'].sum()
            st.metric("Total du panier", f"{total:.2f}€")
        
        st.header("📈 Évolution des prix")
        fig = px.line(history_df, 
                     x='timestamp', 
                     y='price', 
                     color='name',
                     title="Évolution des prix dans le temps")
        st.plotly_chart(fig, use_container_width=True)
        
        st.header("📋 Historique complet")
        st.dataframe(
            history_df.sort_values('timestamp', ascending=False),
            hide_index=True
        )
    else:
        st.info("Aucun historique de prix disponible. Cliquez sur 'Actualiser les prix' pour commencer le suivi.")

def main():
    st.title("📊 Suivi des Prix Amazon")

    # Configuration dans la barre latérale
    with st.sidebar:
        st.header("⚙️ Configuration")
        check_interval = st.slider(
            "Intervalle de vérification (minutes)",
            min_value=5,
            max_value=60,
            value=15,
            step=5
        )
        auto_check = st.toggle("Activer la vérification automatique", value=True)

    # Conteneur pour le statut
    status_container = st.empty()

    db = Database()

    if auto_check:
        # Utiliser st.empty() pour mettre à jour dynamiquement
        last_check = st.empty()
        next_check = st.empty()
        
        while True:
            current_time = datetime.now()
            last_check.write(f"🕐 Dernière vérification : {current_time.strftime('%H:%M:%S')}")
            
            # Exécuter la vérification
            auto_check_prices()
            
            # Calculer et afficher le prochain check
            next_time = current_time + timedelta(minutes=check_interval)
            next_check.write(f"⏰ Prochaine vérification : {next_time.strftime('%H:%M:%S')}")
            
            # Mettre à jour l'affichage
            display_price_history(db)
            
            # Attendre l'intervalle configuré
            time.sleep(check_interval * 60)
    else:
        if st.button("🔄 Actualiser les prix"):
            with st.spinner("Récupération des prix en cours..."):
                current_prices = track_current_prices()
                if current_prices:
                    db.save_prices(current_prices)
                    st.success("Prix mis à jour avec succès!")

        display_price_history(db)

if __name__ == "__main__":
    main()
