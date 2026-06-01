import sys
from types import ModuleType

# 1. PYTHON 3.14 VALEMODUULIT (Estetään pyiceberg-kaatuminen)
if 'pyiceberg' not in sys.modules:
    mock_iceberg = ModuleType('pyiceberg')
    mock_catalog = ModuleType('pyiceberg.catalog')
    mock_rest = ModuleType('pyiceberg.catalog.rest')
    class DummyClass: pass
    mock_rest.RestCatalog = DummyClass
    sys.modules['pyiceberg'] = mock_iceberg
    sys.modules['pyiceberg.catalog'] = mock_catalog
    sys.modules['pyiceberg.catalog.rest'] = mock_rest

import pandas as pd
import streamlit as st
from datetime import datetime, date
import calendar
import plotly.express as px
import requests

# --- SALASANASUOJAUS ---
if not st.session_state.get("authenticated"):
    st.title("🔒 Padel CRM - Kirjaudu sisään")
    kayttajatunnus = st.text_input("Käyttäjätunnus")
    salasana = st.text_input("Salasana", type="password")
    if st.button("Kirjaudu sisään", use_container_width=True):
        if kayttajatunnus == "admin" and salasana == "padel2026":
            st.session_state["authenticated"] = True
            st.success("Kirjautuminen onnistui!")
            st.rerun()
        else:
            st.error("Väärä käyttäjätunnus tai salasana.")
    st.stop()

# --- SUPABASE CONFIGURAATIO ---
if "secrets" in st.secrets and "secrets" in st.secrets["secrets"]:
    RAW_URL = st.secrets["secrets"]["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["secrets"]["SUPABASE_KEY"]
else:
    RAW_URL = "https://supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF0bXpka3Jjc3pwc2lnZXhpemFxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAzMDgyNzYsImV4cCI6MjA5NTg4NDI3Nn0.lDut-78b6bhA2anQeyy4Yx-5wblNOMCtfP3NbYV7dTg"

# Siistitään osoite kaikista vinoviivoista ja rest-liitteistä automaattisesti
PUHDAS_URL = RAW_URL.replace("/rest/v1", "").replace("/rest/v1/", "").rstrip("/")
API_URL = f"{PUHDAS_URL}/rest/v1"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def kuluva_kuukausi_valit():
    tana_an = date.today()
    eka_paiva = date(tana_an.year, tana_an.month, 1)
    res_tuple = calendar.monthrange(tana_an.year, tana_an.month)
    paivien_maara = int(res_tuple[1]) # Poimitaan varmasti pelkkä päivien lukumäärä numerona
    vika_paiva = date(tana_an.year, tana_an.month, paivien_maara)
    return eka_paiva, vika_paiva

def laske_kesto(aika_str):
    try:
        osat = aika_str.replace(" ", "").split("-")
        if len(osat) == 2:
            t1 = datetime.strptime(osat[0], "%H:%M")
            t2 = datetime.strptime(osat[1], "%H:%M")
            erotus = (t2 - t1).total_seconds() / 60
            return int(erotus) if erotus > 0 else 0
    except: return 0
    return 0

@st.cache_data(ttl=60)
def hae_pilvestä(taulu_nimi, parametri_str=""):
    try:
        url = f"{API_URL}/{taulu_nimi}{parametri_str}"
        vastaus = requests.get(url, headers=HEADERS)
        if vastaus.status_code == 200:
            return vastaus.json()
    except: pass
    return []

def paivita_valikot():
    st.cache_data.clear()

kaikki_pelaajat = [p["nimi"] for p in hae_pilvestä("valmennettavat", "?select=nimi&order=nimi.asc")]
kaikki_klubit = [k["nimi"] for k in hae_pilvestä("klubit", "?select=nimi&order=nimi.asc")]

st.set_page_config(page_title="Padel CRM Pilvi", layout="wide", page_icon="🎾")
st.sidebar.title("🎾 Padel-CRM")
if st.sidebar.button("🔒 Kirjaudu ulos"):
    st.session_state["authenticated"] = False
    st.rerun()

valittu_sivu = st.sidebar.radio("Navigointi:", ["Etusivu", "Valmennukset", "Asiakasrekisteri", "Klubit", "Tulot", "Kulut"])
if valittu_sivu == "Etusivu":
    st.title("🏠 Ohjausnäkymä - Etusivu")
    
    tulot_data = hae_pilvestä("manuaaliset_tulot")
    valmennukset_data = hae_pilvestä("valmennukset")
    
    df_kaikki_tulot = pd.DataFrame(tulot_data)
    df_kaikki_v = pd.DataFrame(valmennukset_data)
    
    k_vuosi = str(date.today().year)
    kokonaistulot_vuosi = 0.0
    tunnit_vuosi_yhteensa = 0.0
    
    if not df_kaikki_tulot.empty and "maksupvm" in df_kaikki_tulot.columns:
        df_kaikki_tulot["vuosi"] = pd.to_datetime(df_kaikki_tulot["maksupvm"]).dt.year.astype(str)
        kokonaistulot_vuosi = df_kaikki_tulot[df_kaikki_tulot["vuosi"] == k_vuosi]["summa"].sum()
        
    if not df_kaikki_v.empty and "paivamaara" in df_kaikki_v.columns:
        df_kaikki_v["vuosi"] = pd.to_datetime(df_kaikki_v["paivamaara"]).dt.year.astype(str)
        tunnit_vuosi_yhteensa = df_kaikki_v[df_kaikki_v["vuosi"] == k_vuosi]["kesto_min"].sum() / 60
        
    p_satake1, p_sarake2 = st.columns(2)
    
    with p_satake1:
        st.subheader("📊 Vuositilanne (Toteutuneet)")
        st.metric(f"Toteutuneet tulot vuonna {k_vuosi} (Vain maksetut)", f"{kokonaistulot_vuosi:.2f} €")
        st.metric(f"Toteutuneet valmennustunnit vuonna {k_vuosi}", f"{tunnit_vuosi_yhteensa:.1f} h")
        
        if not df_kaikki_tulot.empty and "maksutapa" in df_kaikki_tulot.columns:
            df_vuosi_tulot = df_kaikki_tulot[df_kaikki_tulot["vuosi"] == k_vuosi]
            if not df_vuosi_tulot.empty:
                tapa_kooste = df_vuosi_tulot.groupby("maksutapa")["summa"].sum().reset_index()
                fig = px.pie(tapa_kooste, values="summa", names="maksutapa", title="Toteutuneiden tulojen jakautuminen", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("Ei maksutapatuloja tälle vuodelle vielä.")
        else: st.info("Ei vielä kirjattuja toteutuneita tuloja.")
        
    with p_sarake2:
        st.subheader("📅 Kuluvan kuukauden tilanne & Ennuste")
        k_alku, k_loppu = kuluva_kuukausi_valit()
        kk_tulo_v, kk_kulu_v, tunnit_kk_yhteensa = 0.0, 0.0, 0.0
        
        if not df_kaikki_v.empty and "paivamaara" in df_kaikki_v.columns:
            df_kaikki_v["pvm_dt"] = pd.to_datetime(df_kaikki_v["paivamaara"]).dt.date
            df_kk = df_kaikki_v[(df_kaikki_v["pvm_dt"] >= k_alku) & (df_kaikki_v["pvm_dt"] <= k_loppu)]
            if not df_kk.empty:
                kk_tulo_v = df_kk["pelaajatulot_yhteensa"].sum() if "pelaajatulot_yhteensa" in df_kk.columns else 0.0
                kk_kulu_v = df_kk["kenttakulu_yhteensa"].sum() if "kenttakulu_yhteensa" in df_kk.columns else 0.0
                tunnit_kk_yhteensa = (df_kk["kesto_min"].sum() / 60) if "kesto_min" in df_kk.columns else 0.0
            
        kk_tuotto = kk_tulo_v - kk_kulu_v
        st.metric("Kuukauden laskettu tulo valmennuksista (Arvio)", f"{kk_tulo_v:.2f} €")
        st.metric("Kuukauden kenttämaksut (Kulu)", f"{kk_kulu_v:.2f} €")
        st.metric("Kuukauden ennustettu tuotto (Kate)", f"{kk_tuotto:.2f} €")
        st.metric("Kuukauden valmennustunnit", f"{tunnit_kk_yhteensa:.1f} h")
        
    st.markdown("---")
    st.subheader("🔍 Hae toteutuneita tuloja aikaväleillä ja maksutavoilla")
    h_alku, h_loppu = kuluva_kuukausi_valit()
    haku_aikavali = st.date_input("Valitse aikaväli hakuun", [h_alku, h_loppu], key="etusivu_haku_pvm")
    valittu_tapa = st.selectbox("Valitse maksutapa", ["Kaikki", "Lasku", "Käteinen", "MobilePay", "Liikuntaetu"])
    
    if isinstance(haku_aikavali, (list, tuple)) and len(haku_aikavali) == 2:
        a_pvm, l_pvm = haku_aikavali
        if not df_kaikki_tulot.empty and "maksupvm" in df_kaikki_tulot.columns:
            df_kaikki_tulot["pvm_dt"] = pd.to_datetime(df_kaikki_tulot["maksupvm"]).dt.date
            df_suodatettu_t = df_kaikki_tulot[(df_kaikki_tulot["pvm_dt"] >= a_pvm) & (df_kaikki_tulot["pvm_dt"] <= l_pvm)]
            if valittu_tapa != "Kaikki" and "maksutapa" in df_suodatettu_t.columns: 
                df_suodatettu_t = df_suodatettu_t[df_suodatettu_t["maksutapa"] == valittu_tapa]
            haku_summa = df_suodatettu_t["summa"].sum() if not df_suodatettu_t.empty else 0.0
            st.metric(f"Toteutuneet tulot ({valittu_tapa}) valitulla välillä", f"{haku_summa:.2f} €")
            if not df_suodatettu_t.empty: 
                st.dataframe(df_suodatettu_t[["maksupvm", "maksaja", "summa", "maksutapa"]], use_container_width=True, hide_index=True)
        else: 
            st.info("Ei toteutuneita maksuja järjestelmässä valitulla välillä.")
elif valittu_sivu == "Valmennukset":
    st.title("📅 Valmennusten hallinta")
    sarake1, sarake2 = st.columns(2)
    
    with sarake1:
        st.subheader("➕ Luo uusi valmennus")
        v_pvm = st.date_input("Päivämäärä", datetime.now())
        pvm_str = v_pvm.strftime("%Y-%m-%d")
        viikonpaiva = v_pvm.weekday()
        
        st.markdown("##### ⏱️ Valitse aika kellosta tai kirjoita alle")
        kello_ajat = [f"{h:02d}:{m:02d}" for h in range(6, 23) for m in (0, 30)]
        alku_valinta = st.selectbox("Aloitusaika", kello_ajat, index=20)
        loppu_valinta = st.selectbox("Lopetusaika", kello_ajat, index=23)
        v_aika = st.text_input("Vahvista tai kirjoita aika manuaalisesti", f"{alku_valinta} - {loppu_valinta}")
        
        kesto_min = laske_kesto(v_aika)
        kesto_h = kesto_min / 60
        if kesto_min > 0: st.success(f"⏱️ Kesto: {kesto_min} min ({kesto_h:.1f} h)")
            
        v_pelaajat = st.multiselect("Valitse pelaajat ryhmään", kaikki_pelaajat)
        v_klubi = st.selectbox("Valitse klubi", kaikki_klubit, index=None)
        
        oletettu_kenttahinta_tunti = 0.0
        if v_klubi:
            try:
                klubi_data = hae_pilvestä("klubit", f"?nimi=eq.{v_klubi}")
                if klubi_data and len(klubi_data) > 0:
                    hinnat_db = klubi_data[0]
                    alku_tunti = int(alku_valinta.split(":")[0])
                    if viikonpaiva >= 5:
                        oletettu_kenttahinta_tunti = float(hinnat_db.get("vklppuhinta", 0))
                    elif alku_tunti >= 16:
                        oletettu_kenttahinta_tunti = float(hinnat_db.get("primehinta", 0))
                    else:
                        oletettu_kenttahinta_tunti = float(hinnat_db.get("paivahinta", 0))
            except: pass

        v_kenttahinta_tunti = st.number_input("Kenttähinta (€ / h)", min_value=0.0, step=0.5, value=oletettu_kenttahinta_tunti)
        
        passilaisten_nimet = []
        if v_pelaajat:
            try:
                passilaiset_res = hae_pilvestä("valmennettavat", f"?on_kenttapassi=eq.1&passi_alku=lte.{pvm_str}&passi_loppu=gte.{pvm_str}")
                passilaisten_nimet = [p["nimi"] for p in passilaiset_res if p["nimi"] in v_pelaajat]
            except: pass
        
        alennuskerroin = max(0.0, 1.0 - (len(passilaisten_nimet) * 0.25))
        v_kenttakulu_yhteensa = (v_kenttahinta_tunti * kesto_h) * alennuskerroin
        if v_pelaajat and passilaisten_nimet:
            st.warning(f"🛡️ Kenttäpassi tunnistettu pelaajilla: {', '.join(passilaisten_nimet)}. Kenttähinnasta vähennetty {len(passilaisten_nimet)*25} %")
        if v_kenttakulu_yhteensa >= 0: st.metric("Kenttähinta kokonaisuudessaan (Alennuksen jälkeen)", f"{v_kenttakulu_yhteensa:.2f} €")
            
        oletushinta = st.number_input("Pelaajakohtainen oletushinta (€)", min_value=0.0, step=0.5, value=22.50)
        pelaajahinnat_str, v_pelaajatulot_yhteensa = "", 0.0
        if v_pelaajat:
            st.markdown("##### 💰 Pelaajien yksittäiset hinnat:")
            per_pelaaja_alennus = (v_kenttahinta_tunti * kesto_h) / 4 if kesto_h > 0 else 0.0
            hinnat_lista = [max(0.0, oletushinta - per_pelaaja_alennus) if p in passilaisten_nimet else oletushinta for p in v_pelaajat]
            hinta_df = pd.DataFrame({"Pelaaja": v_pelaajat, "Hinta (€)": hinnat_lista})
            muokatut_hinnat = st.data_editor(hinta_df, use_container_width=True, hide_index=True)
            v_pelaajatulot_yhteensa = muokatut_hinnat["Hinta (€)"].sum()
            pelaajahinnat_str = ", ".join([f"{row['Pelaaja']}: {row['Hinta (€)']:.2f}€" for _, row in muokatut_hinnat.iterrows()])
            v_oma_tulos = v_pelaajatulot_yhteensa - v_kenttakulu_yhteensa
            st.metric("Yhteenlaskettu saanti", f"{v_pelaajatulot_yhteensa:.2f} €")
            st.metric("Tulokseni (Kate)", f"{v_oma_tulos:.2f} €")

        st.markdown("##### ⚙️ Tuuraustiedot")
        v_tuuraaja_kylla = st.checkbox("Tunnilla oli tuuraajia")
        tuuraustiedot_str = "Ei tuuraajia"
        if v_tuuraaja_kylla and v_pelaajat:
            v_poissa_lista = st.multiselect("Kuka oli poissa?", v_pelaajat)
            tuuraus_parit = []
            for poissaolija in v_poissa_lista:
                tilalla = st.selectbox(f"Kuka tuurasi pelaajaa {poissaolija}?", kaikki_pelaajat, key=f"tuuri_{poissaolija}")
                if tilalla: tuuraus_parit.append(f"{tilalla} (tuuraa: {poissaolija})")
            tuuraustiedot_str = ", ".join(tuuraus_parit) if tuuraus_parit else "Ei määritetty"

        if st.button("Tallenna valmennus", use_container_width=True):
            if v_pelaajat and v_klubi:
                pelaajat_str = ", ".join(v_pelaajat)
                alennuksen_saajat_str = ", ".join(passilaisten_nimet) if passilaisten_nimet else "Ei alennuksia"
                uusi_valmennus = {
                    "paivamaara": pvm_str, "aika": v_aika, "kesto_min": int(kesto_min),
                    "pelaajat": pelaajat_str, "klubi": v_klubi, "kenttakulu_yhteensa": float(v_kenttakulu_yhteensa),
                    "pelaajatulot_yhteensa": float(v_pelaajatulot_yhteensa), "oma_tulos": float(v_oma_tulos),
                    "pelaajahinta": pelaajahinnat_str, "tuuraustiedot": tuuraustiedot_str, "alennuksen_saajat": alennuksen_saajat_str
                }
                url = f"{API_URL}/valmennukset"
                vastaus = requests.post(url, headers=HEADERS, json=uusi_valmennus)
                if vastaus.status_code == 201:
                    st.success("Tallennettu pilveen!")
                    st.rerun()
                else: st.error(f"Tallennus epäonnistui: {vastaus.text}")
            else: st.error("Valitse pelaajat ja klubi.")
    with sarake2:
        st.subheader("📋 Suoritetut valmennukset & Raportit")
        valmennukset_data = hae_pilvestä("valmennukset", "?order=paivamaara.desc")
        df_v = pd.DataFrame(valmennukset_data)
        
        if not df_v.empty:
            st.markdown("##### 🔍 Suodata aikavälillä")
            k_alku, k_loppu = kuluva_kuukausi_valit()
            aikavali = st.date_input("Valitse aikaväli", [k_alku, k_loppu], key="aikavali_haku")
            
            if isinstance(aikavali, (list, tuple)) and len(aikavali) == 2:
                alku_pvm, loppu_pvm = aikavali
                df_v["pvm_dt"] = pd.to_datetime(df_v["paivamaara"]).dt.date
                df_v = df_v[(df_v["pvm_dt"] >= alku_pvm) & (df_v["pvm_dt"] <= loppu_pvm)].drop(columns=["pvm_dt"])
            
            raportti_tyyppi = st.radio("Valitse näkymä:", ["Kaikki valmennukset listana", "Pelaajakohtainen kooste (Laskutustiedot)"], horizontal=True)
            
            if raportti_tyyppi == "Kaikki valmennukset listana":
                paivitetyt_valmennukset = st.data_editor(
                    df_v, use_container_width=True, hide_index=True, 
                    column_config={
                        "id": None, "paivamaara": "Päivä", "aika": "Aika", "kesto_min": "Kesto (min)",
                        "pelaajat": "Ryhmä", "klubi": "Klubi",
                        "kenttakulu_yhteensa": st.column_config.NumberColumn("Kenttä kulu", format="%.2f €"), 
                        "pelaajatulot_yhteensa": st.column_config.NumberColumn("Saanti tot", format="%.2f €"),
                        "oma_tulos": st.column_config.NumberColumn("Tulokseni", format="%.2f €"),
                        "pelaajahinta": "Hinnat", "tuuraustiedot": "Tuuraajat", "alennuksen_saajat": None
                    }, key="v_editor"
                )
                
                csv_v = df_v.to_csv(index=False, sep=";", encoding="utf-8-sig")
                st.download_button("📥 Vie valmennuslista Exceliin (CSV)", csv_v, f"valmennukset_{alku_pvm}_to_{loppu_pvm}.csv", "text/csv", use_container_width=True)
                
                if st.session_state.v_editor["edited_rows"]:
                    for r_idx, muutokset in st.session_state.v_editor["edited_rows"].items():
                        rivi_nyt = df_v.iloc[r_idx].to_dict()
                        t_id = int(rivi_nyt["id"])
                        
                        for sarake, uusi_arvo in muutokset.items():
                            rivi_nyt[sarake] = uusi_arvo
                            url = f"{API_URL}/valmennukset?id=eq.{t_id}"
                            requests.patch(url, headers=HEADERS, json={sarake: uusi_arvo})
                            
                        tot_saanti = 0.0
                        for th in str(rivi_nyt["pelaajahinta"]).split(","):
                            if ":" in th:
                                try: tot_saanti += float(th.split(":")[1].replace("€", "").strip())
                                except: pass
                        uusi_kenttakulu = float(rivi_nyt["kenttakulu_yhteensa"])
                        url = f"{API_URL}/valmennukset?id=eq.{t_id}"
                        requests.patch(url, headers=HEADERS, json={"pelaajatulot_yhteensa": tot_saanti, "oma_tulos": tot_saanti - uusi_kenttakulu})
                    st.rerun()
            
            else:
                kooste_data = {}
                for _, rivi in df_v.iterrows():
                    for osa in str(rivi.get("pelaajahinta", "")).split(","):
                        if ":" in osa and "€" in osa:
                            try:
                                p_nimi = osa.split(":")[0].strip()
                                p_hinta = float(osa.split(":")[1].replace("€", "").strip())
                                if p_nimi not in kooste_data:
                                    kooste_data[p_nimi] = {"Treenikerrat": 0, "Yhteenlaskettu valmennusmaksu (€)": 0.0}
                                kooste_data[p_nimi]["Treenikerrat"] += 1
                                kooste_data[p_nimi]["Yhteenlaskettu valmennusmaksu (€)"] += p_hinta
                            except: pass
                
                if kooste_data:
                    df_kooste = pd.DataFrame.from_dict(kooste_data, orient='index').reset_index().rename(columns={"index": "Pelaajan nimi"})
                    st.dataframe(df_kooste, use_container_width=True, hide_index=True, column_config={
                        "Yhteenlaskettu valmennusmaksu (€)": st.column_config.NumberColumn("Maksut yhteensä", format="%.2f €")
                    })
                    csv_k = df_kooste.to_csv(index=False, sep=";", encoding="utf-8-sig")
                    st.download_button("📥 Vie laskutuskooste Exceliin (CSV)", csv_k, f"laskutuskooste_{alku_pvm}_to_{loppu_pvm}.csv", "text/csv", use_container_width=True)
                else: st.info("Ei tunnistettuja pelaajahintoja tällä aikavälillä.")
            
            st.markdown("---")
            st.subheader("🗑️ Poista valmennus listalta")
            poistettava_v = st.selectbox("Valitse poistettava valmennuskerta:", df_v.apply(lambda r: f"ID {r['id']} | {r['paivamaara']} | {r['klubi']}", axis=1).tolist(), index=None, placeholder="Valitse...")
            if poistettava_v:
                v_id = int(poistettava_v.split(" | ")[0].replace("ID ", ""))
                if st.button("Kyllä, poista valmennus", type="primary", use_container_width=True):
                    url = f"{API_URL}/valmennukset?id=eq.{v_id}"
                    requests.delete(url, headers=HEADERS)
                    st.rerun()
        else: st.info("Ei valmennuksia valitulla aikavälillä.")
elif valittu_sivu == "Asiakasrekisteri":
    st.title("👥 Asiakasrekisteri (Pilviversio)")
    s1, s2 = st.columns(2)
    
    with s1:
        st.subheader("➕ Lisää uusi asiakas & Kenttäpassi")
        n = st.text_input("Nimi")
        p = st.text_input("Puhelin")
        e = st.text_input("Sähköposti")
        k = st.text_area("Kommentit")
        
        st.markdown("##### 🛡️ Kenttäpassi-asetukset")
        k_passi = st.checkbox("Pelaajalla on voimassa oleva kenttäpassi")
        p_alku, p_loppu = "2000-01-01", "2000-01-01"
        if k_passi:
            toistaiseksi = st.checkbox("Voimassa toistaiseksi", value=True)
            if toistaiseksi: 
                p_alku, p_loppu = date.today().strftime("%Y-%m-%d"), "2099-12-31"
            else:
                p_alku = st.date_input("Alku", date.today()).strftime("%Y-%m-%d")
                p_loppu = st.date_input("Loppu", date.today()).strftime("%Y-%m-%d")
                
        if st.button("Tallenna pelaaja", use_container_width=True):
            if n:
                uusi_asiakas = {
                    "nimi": n, "puhelin": p, "sahkoposti": e, "kommentit": k, 
                    "on_kenttapassi": 1 if k_passi else 0, "passi_alku": p_alku, "passi_loppu": p_loppu
                }
                url = f"{API_URL}/valmennettavat"
                vastaus = requests.post(url, headers=HEADERS, json=uusi_asiakas)
                
                if vastaus.status_code == 201:
                    paivita_valikot()
                    st.success(f"Pelaaja {n} tallennettu onnistuneesti pilveen!")
                    st.rerun()
                else:
                    st.error(f"Tallennus epäonnistui: {vastaus.text}")
            else:
                st.error("Anna vähintään pelaajan nimi.")
        
        st.markdown("---")
        st.subheader("🔍 Pelaajan kuukausikohtainen historia")
        valmennukset_data = hae_pilvestä("valmennukset")
        df_kaikki_v = pd.DataFrame(valmennukset_data)
        
        valittu_haku_pelaaja = st.selectbox("Valitse tutkittava pelaaja", kaikki_pelaajat, index=None, placeholder="Valitse nimi...")
        h_alku, h_loppu = kuluva_kuukausi_valit()
        haku_vali = st.date_input("Valitse historian aikaväli", [h_alku, h_loppu])
        
        if valittu_haku_pelaaja and not df_kaikki_v.empty and isinstance(haku_vali, (list, tuple)) and len(haku_vali) == 2:
            historia_alku, historia_loppu = haku_vali
            df_kaikki_v["pvm_dt"] = pd.to_datetime(df_kaikki_v["paivamaara"]).dt.date
            df_suodatettu = df_kaikki_v[(df_kaikki_v["pvm_dt"] >= historia_alku) & (df_kaikki_v["pvm_dt"] <= historia_loppu)]
            pelaajan_tunnit, pelaajan_kokonaissumma = [], 0.0
            
            for _, r_v in df_suodatettu.iterrows():
                if valittu_haku_pelaaja in str(r_v.get("pelaajat", "")) or valittu_haku_pelaaja in str(r_v.get("tuuraustiedot", "")):
                    for osa in str(r_v.get("pelaajahinta", "")).split(","):
                        if valittu_haku_pelaaja in osa and ":" in osa:
                            try:
                                h_luku = float(osa.split(":").replace("€", "").strip())
                                pelaajan_kokonaissumma += h_luku
                            except: pass
                    pelaajan_tunnit.append({"Päivä": r_v.get("paivamaara"), "Aika": r_v.get("aika"), "Klubi": r_v.get("klubi")})
                    
            if pelaajan_tunnit:
                st.metric(f"{valittu_haku_pelaaja} - Maksut yhteensä", f"{pelaajan_kokonaissumma:.2f} €")
                st.dataframe(pd.DataFrame(pelaajan_tunnit), use_container_width=True, hide_index=True)
            else:
                st.info("Ei tunteja tällä aikavälillä.")
            
    with s2:
        st.subheader("📝 Muokkaa ja poista asiakkaita")
        asiakkaat_data = hae_pilvestä("valmennettavat")
        df_a = pd.DataFrame(asiakkaat_data)
        
        if not df_a.empty:
            df_a = df_a[["id", "nimi", "puhelin", "sahkoposti", "kommentit", "on_kenttapassi", "passi_alku", "passi_loppu"]]
            paivitetyt_asiakkaat = st.data_editor(df_a, use_container_width=True, hide_index=True, column_config={"id": None}, key="a_editor")
            
            if st.session_state.a_editor["edited_rows"]:
                for r_idx, muutokset in st.session_state.a_editor["edited_rows"].items():
                    t_id = int(df_a.iloc[r_idx]["id"])
                    url = f"{API_URL}/valmennettavat?id=eq.{t_id}"
                    requests.patch(url, headers=HEADERS, json=muutokset)
                paivita_valikot()
                st.success("Muutokset päivitetty pilveen!")
                st.rerun()
                
            p_pelaaja = st.selectbox("Valitse poistettava pelaaja:", df_a["nimi"].tolist(), index=None, placeholder="Valitse nimi...")
            if p_pelaaja and st.button("Vahvista poisto pysyvästi", use_container_width=True):
                url = f"{API_URL}/valmennettavat?nimi=eq.{p_pelaaja}"
                requests.delete(url, headers=HEADERS)
                paivita_valikot()
                st.rerun()
        else:
            st.info("Asiakasrekisteri on vielä tyhjä. Lisää ensimmäinen pelaaja vasemmalta.")

elif valittu_sivu == "Klubit":
    st.title("🏢 Klubit")
    s1, s2 = st.columns(2)
    with s1:
        st.subheader("➕ Lisää klubi")
        kn = st.text_input("Klubin nimi")
        kp = st.number_input("Päivähinta (€)", min_value=0.0)
        km = st.number_input("PrimeHinta (€)", min_value=0.0)
        kv = st.number_input("VklppuHinta (€)", min_value=0.0)
        if st.button("Tallenna klubi", use_container_width=True):
            if kn:
                uusi_k = {"nimi": kn, "paivahinta": kp, "primehinta": km, "vklppuhinta": kv}
                url = f"{API_URL}/klubit"
                vastaus = requests.post(url, headers=HEADERS, json=uusi_k)
                if vastaus.status_code == 201:
                    paivita_valikot()
                    st.success(f"Klubi {kn} tallennettu onnistuneesti!")
                    st.rerun()
                else: 
                    st.error(f"Virhe: {vastaus.text}")
            else:
                st.error("Anna klubin nimi.")
    with s2:
        st.subheader("📝 Selaa klubeja")
        klubit_data = hae_pilvestä("klubit")
        df_k = pd.DataFrame(klubit_data)
        if not df_k.empty:
            df_k = df_k[["id", "nimi", "paivahinta", "primehinta", "vklppuhinta"]]
            paivitetyt_klubit = st.data_editor(df_k, use_container_width=True, hide_index=True, column_config={"id": None}, key="k_editor")
            if st.session_state.k_editor["edited_rows"]:
                for r_idx, muutokset in st.session_state.k_editor["edited_rows"].items():
                    t_id = int(df_k.iloc[r_idx]["id"])
                    url = f"{API_URL}/klubit?id=eq.{t_id}"
                    requests.patch(url, headers=HEADERS, json=muutokset)
                paivita_valikot()
                st.rerun()
            p_klubi = st.selectbox("Poista klubi:", df_k["nimi"].tolist(), index=None)
            if p_klubi and st.button("Vahvista klubin poisto"):
                url = f"{API_URL}/klubit?nimi=eq.{p_klubi}"
                requests.delete(url, headers=HEADERS)
                paivita_valikot()
                st.rerun()
elif valittu_sivu == "Tulot":
    st.title("💰 Tulojen seuranta (Toteutuneet maksut)")
    t_alku, t_loppu = kuluva_kuukausi_valit()
    tulojen_aikavali = st.date_input("Valitse tarkasteltava aikaväli", [t_alku, t_loppu], key="tulot_aikavali_haku")
    if isinstance(tulojen_aikavali, (list, tuple)) and len(tulojen_aikavali) == 2:
        alku_pvm, loppu_pvm = tulojen_aikavali
        alku_s, loppu_s = alku_pvm.strftime("%Y-%m-%d"), loppu_pvm.strftime("%Y-%m-%d")
        df_tulot = pd.DataFrame(hae_pilvestä("manuaaliset_tulot", f"?maksupvm=gte.{alku_s}&maksupvm=lte.{loppu_s}"))
        
        s1, s2 = st.columns(2)
        with s1:
            st.subheader("➕ Kirjaa uusi toteutunut maksu")
            t_maksaja = st.selectbox("Maksaja (Valitse asiakas)", kaikki_pelaajat, index=None, placeholder="Valitse pelaaja...")
            t_pvm = st.date_input("Maksupäivämäärä", datetime.now())
            t_summa = st.number_input("Summa (€)", min_value=0.0, step=5.0)
            t_tapa = st.selectbox("Maksutapa", ["Lasku", "Käteinen", "MobilePay", "Liikuntaetu"])
            if st.button("Tallenna tulo", use_container_width=True) and t_maksaja:
                pvm_t_str = t_pvm.strftime("%Y-%m-%d")
                uusi_tulo = {"maksaja": t_maksaja, "maksupvm": pvm_t_str, "summa": float(t_summa), "maksutapa": t_tapa}
                url = f"{API_URL}/manuaaliset_tulot"
                vastaus = requests.post(url, headers=HEADERS, json=uusi_tulo)
                if vastaus.status_code == 201:
                    st.success("Tulo kirjattu onnistuneesti!")
                    st.rerun()
        with s2:
            st.subheader("📝 Selaa ja muokkaa toteutuneita tuloja")
            if not df_tulot.empty:
                df_tulot = df_tulot[["id", "maksupvm", "maksaja", "summa", "maksutapa"]]
                paivitetyt_tulot = st.data_editor(df_tulot, use_container_width=True, hide_index=True, column_config={"id": None, "maksupvm": "Päivä", "summa": st.column_config.NumberColumn("Summa", format="%.2f €")}, key="tulot_editor")
                if st.session_state.tulot_editor["edited_rows"]:
                    for r_idx, muutokset in st.session_state.tulot_editor["edited_rows"].items():
                        t_id = int(df_tulot.iloc[r_idx]["id"])
                        url = f"{API_URL}/manuaaliset_tulot?id=eq.{t_id}"
                        requests.patch(url, headers=HEADERS, json=muutokset)
                    st.rerun()
                st.markdown("---")
                poistettava_tulo = st.selectbox("Poista tulo listalta:", df_tulot.apply(lambda r: f"ID {r['id']} | {r['maksaja']} | {r['summa']}€", axis=1).tolist(), index=None)
                if poistettava_tulo and st.button("Vahvista tulon poisto", type="primary", use_container_width=True):
                    t_id = int(poistettava_tulo.split(" | ").replace("ID ", ""))
                    url = f"{API_URL}/manuaaliset_tulot?id=eq.{t_id}"
                    requests.delete(url, headers=HEADERS)
                    st.rerun()
            else: st.info("Ei erillisiä toteutuneita tuloja tällä aikavälillä.")

elif valittu_sivu == "Kulut":
    st.title("📉 Kulujen seuranta")
    k_alku, k_loppu = kuluva_kuukausi_valit()
    kulujen_aikavali = st.date_input("Valitse tarkasteltava aikaväli", [k_alku, k_loppu], key="kulut_aikavali_haku")
    if isinstance(kulujen_aikavali, (list, tuple)) and len(kulujen_aikavali) == 2:
        alku_pvm, loppu_pvm = kulujen_aikavali
        alku_s, loppu_s = alku_pvm.strftime("%Y-%m-%d"), loppu_pvm.strftime("%Y-%m-%d")
        df_valmennuskulut = pd.DataFrame(hae_pilvestä("valmennukset", f"?select=paivamaara,aika,klubi,kenttakulu_yhteensa,alennuksen_saajat&paivamaara=gte.{alku_s}&paivamaara=lte.{loppu_s}"))
        df_omat_kulut = pd.DataFrame(hae_pilvestä("manuaaliset_kulut", f"?paivamaara=gte.{alku_s}&paivamaara=lte.{loppu_s}"))
        
        kokonais_kenttakulut = df_valmennuskulut["kenttakulu_yhteensa"].sum() if not df_valmennuskulut.empty else 0.0
        st.markdown("### 🏛️ Automaattinen kooste")
        st.info(f"📊 **Kaikki klubit / Kenttävuokrat yhteensä aikavälillä:** {kokonais_kenttakulut:.2f} €")
        with st.expander("🔎 Klikkaa tästä nähdäksesi tarkka seloste kenttämaksuista"):
            if not df_valmennuskulut.empty:
                df_naytettava = df_valmennuskulut.rename(columns={"paivamaara": "Päivä", "aika": "Kellonaika", "klubi": "Klubi", "kenttakulu_yhteensa": "Kulu (€)", "alennuksen_saajat": "Kenttäpassit"})
                st.dataframe(df_naytettava, use_container_width=True, hide_index=True, column_config={"Kulu (€)": st.column_config.NumberColumn("Kulu (€)", format="%.2f €")})
                csv_data = df_naytettava.to_csv(index=False, sep=";", encoding="utf-8-sig")
                st.download_button(label="📥 Vie seloste Exceliin (CSV-muodossa)", data=csv_data, file_name=f"kenttavuokrat_{alku_s}_to_{loppu_s}.csv", mime="text/csv", use_container_width=True)
            else: st.write("Ei kenttäkuluja tällä aikavälillä.")
        st.markdown("---")
        st.markdown("### 🛠️ Muut liiketoiminnan kulut")
        s1, s2 = st.columns(2)
        with s1:
            st.subheader("➕ Lisää uusi kulu")
            k_pvm = st.date_input("Kulukirjauksen päivä", datetime.now())
            k_selite = st.text_input("Kulun kuvaus (esim. Pallolaatikko x2)")
            k_kat = st.selectbox("Kategoria", ["Välineet", "Markkinointi", "Hallinto", "Muut kulut"])
            k_summa = st.number_input("Summa (€)", min_value=0.0, step=1.0)
            if st.button("Tallenna kulu", use_container_width=True) and k_selite:
                pvm_k_str = k_pvm.strftime("%Y-%m-%d")
                uusi_kulu = {"paivamaara": pvm_k_str, "selite": k_selite, "kategoria": k_kat, "summa": float(k_summa)}
                url = f"{API_URL}/manuaaliset_kulut"
                vastaus = requests.post(url, headers=HEADERS, json=uusi_kulu)
                if vastaus.status_code == 201:
                    st.success("Kulu tallennettu!"); st.rerun()
        with s2:
            st.subheader("📝 Selaa ja muokkaa muita kuluja")
            if not df_omat_kulut.empty:
                df_omat_kulut = df_omat_kulut[["id", "paivamaara", "selite", "kategoria", "summa"]]
                paivitetyt_kulut = st.data_editor(df_omat_kulut, use_container_width=True, hide_index=True, column_config={"id": None, "paivamaara": "Päivä", "summa": st.column_config.NumberColumn("Summa (€)", format="%.2f €")}, key="k_editor")
                if st.session_state.k_editor["edited_rows"]:
                    for r_idx, muutokset in st.session_state.k_editor["edited_rows"].items():
                        t_id = int(df_omat_kulut.iloc[r_idx]["id"])
                        url = f"{API_URL}/manuaaliset_kulut?id=eq.{t_id}"
                        requests.patch(url, headers=HEADERS, json=muutokset)
                    st.rerun()
                st.markdown("---")
                poistettava_kulu = st.selectbox("Poista kulu listalta:", df_omat_kulut.apply(lambda r: f"ID {r['id']} | {r['selite']} | {r['summa']}€", axis=1).tolist(), index=None)
                if poistettava_kulu and st.button("Vahvista kulun poisto", type="primary", use_container_width=True):
                    k_id = int(poistettava_kulu.split(" | ").replace("ID ", ""))
                    url = f"{API_URL}/manuaaliset_kulut?id=eq.{k_id}"
                    requests.delete(url, headers=HEADERS)
                    st.rerun()
            else: st.info("Ei muita kuluja tällä aikavälillä.")
