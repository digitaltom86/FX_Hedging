import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="FX Hedging Model", page_icon="💱", layout="wide")

st.title("💱 FX Hedging Strategy Model")
st.markdown("Model hedgingowy dla treasury w USDT z kosztami operacyjnymi w EUR i PLN")

# Sidebar - parametry wejściowe
st.sidebar.header("📊 Parametry Treasury")
treasury_usdt = st.sidebar.number_input("Treasury (USDT)", value=1_025_000, step=50_000, format="%d")
monthly_eur_costs = st.sidebar.number_input("Miesięczne koszty EUR", value=95_000, step=5_000, format="%d")
monthly_pln_costs = st.sidebar.number_input("Miesięczne koszty PLN", value=230_000, step=10_000, format="%d")
forecast_months = st.sidebar.slider("Horyzont prognozy (miesiące)", 1, 24, 6)

st.sidebar.header("💹 Kursy walutowe")
st.sidebar.subheader("Kursy początkowe")
usd_pln_start = st.sidebar.number_input("USD/PLN (start)", value=3.60, step=0.01, format="%.2f")
eur_usd_start = st.sidebar.number_input("EUR/USD (start)", value=1.175, step=0.005, format="%.3f")

st.sidebar.subheader("Kursy końcowe (prognoza)")
usd_pln_end = st.sidebar.number_input("USD/PLN (koniec)", value=3.50, step=0.01, format="%.2f")
eur_usd_end = st.sidebar.number_input("EUR/USD (koniec)", value=1.20, step=0.005, format="%.3f")

st.sidebar.header("🛡️ Parametry hedgingu")
hedge_coverage = st.sidebar.slider("Pokrycie hedgingiem (%)", 0, 100, 100) / 100
otc_spread = st.sidebar.slider("Spread OTC (%)", 0.05, 0.50, 0.20, step=0.05) / 100
bank_fx_spread = st.sidebar.slider("Spread bankowy EUR/PLN (%)", 0.05, 0.30, 0.15, step=0.05) / 100

# Obliczenia
months = np.arange(1, forecast_months + 1)

# Interpolacja kursów (liniowa zmiana)
usd_pln_path = np.linspace(usd_pln_start, usd_pln_end, forecast_months)
eur_usd_path = np.linspace(eur_usd_start, eur_usd_end, forecast_months)

# Kursy zablokowane (hedging)
usd_pln_hedged = np.full(forecast_months, usd_pln_start)
eur_usd_hedged = np.full(forecast_months, eur_usd_start)

# Funkcja obliczająca koszty miesięczne
def calc_monthly_costs(usd_pln, eur_usd):
    pln_in_usd = monthly_pln_costs / usd_pln
    eur_in_usd = monthly_eur_costs * eur_usd
    return pln_in_usd + eur_in_usd

# Koszty bez hedgingu
costs_unhedged = np.array([calc_monthly_costs(usd_pln_path[i], eur_usd_path[i]) for i in range(forecast_months)])

# Koszty z hedgingiem (mix)
costs_hedged_part = np.array([calc_monthly_costs(usd_pln_hedged[i], eur_usd_hedged[i]) for i in range(forecast_months)])
costs_hedged = hedge_coverage * costs_hedged_part + (1 - hedge_coverage) * costs_unhedged

# Koszty hedgingu
hedging_execution_costs = costs_hedged_part * hedge_coverage * (otc_spread + bank_fx_spread * (monthly_pln_costs / usd_pln_start) / costs_hedged_part)

# Skumulowane koszty
cumulative_unhedged = np.cumsum(costs_unhedged)
cumulative_hedged = np.cumsum(costs_hedged + hedging_execution_costs)

# Pozostałe treasury
treasury_unhedged = treasury_usdt - cumulative_unhedged
treasury_hedged = treasury_usdt - cumulative_hedged

# Runway calculation
def calc_runway(treasury, monthly_costs):
    remaining = treasury
    for i, cost in enumerate(monthly_costs):
        remaining -= cost
        if remaining <= 0:
            return i + (remaining + cost) / cost
    return len(monthly_costs)

runway_unhedged = calc_runway(treasury_usdt, costs_unhedged)
runway_hedged = calc_runway(treasury_usdt, costs_hedged + hedging_execution_costs)

# Layout główny
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Treasury", f"{treasury_usdt:,.0f} USDT")
with col2:
    delta_runway = runway_hedged - runway_unhedged
    st.metric("Runway (bez hedgingu)", f"{runway_unhedged:.1f} mies.")
with col3:
    st.metric("Runway (z hedgingiem)", f"{runway_hedged:.1f} mies.", delta=f"{delta_runway:+.2f} mies.")
with col4:
    total_savings = cumulative_unhedged[-1] - cumulative_hedged[-1] if forecast_months > 0 else 0
    st.metric("Oszczędności z hedgingu", f"{total_savings:,.0f} USD")

st.markdown("---")

# Wykresy
tab1, tab2, tab3, tab4 = st.tabs(["📈 Kursy walutowe", "💰 Koszty operacyjne", "🏦 Treasury", "📊 Analiza scenariuszy"])

with tab1:
    fig = make_subplots(rows=1, cols=2, subplot_titles=("USD/PLN", "EUR/USD"))
    fig.add_trace(go.Scatter(x=months, y=usd_pln_path, name="USD/PLN (rynek)", line=dict(color="red")), row=1, col=1)
    fig.add_trace(go.Scatter(x=months, y=usd_pln_hedged, name="USD/PLN (hedge)", line=dict(color="green", dash="dash")), row=1, col=1)
    fig.add_trace(go.Scatter(x=months, y=eur_usd_path, name="EUR/USD (rynek)", line=dict(color="blue")), row=1, col=2)
    fig.add_trace(go.Scatter(x=months, y=eur_usd_hedged, name="EUR/USD (hedge)", line=dict(color="green", dash="dash")), row=1, col=2)
    fig.update_layout(height=400, title_text="Ścieżki kursów walutowych")
    fig.update_xaxes(title_text="Miesiąc")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=months, y=costs_unhedged, name="Bez hedgingu", marker_color="red", opacity=0.7))
    fig2.add_trace(go.Bar(x=months, y=costs_hedged, name="Z hedgingiem", marker_color="green", opacity=0.7))
    fig2.add_trace(go.Scatter(x=months, y=hedging_execution_costs, name="Koszt hedgingu", line=dict(color="orange", dash="dot")))
    fig2.update_layout(height=400, title_text="Miesięczne koszty operacyjne (USD)", barmode="group", xaxis_title="Miesiąc", yaxis_title="USD")
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=months, y=treasury_unhedged, name="Bez hedgingu", fill="tozeroy", line=dict(color="red")))
    fig3.add_trace(go.Scatter(x=months, y=treasury_hedged, name="Z hedgingiem", fill="tozeroy", line=dict(color="green")))
    fig3.add_hline(y=0, line_dash="dash", line_color="black", annotation_text="Zero")
    fig3.update_layout(height=400, title_text="Pozostałe Treasury (USDT)", xaxis_title="Miesiąc", yaxis_title="USDT")
    st.plotly_chart(fig3, use_container_width=True)

with tab4:
    st.subheader("Analiza scenariuszy")
    scenarios = {
        "Silny USD": {"usd_pln": 3.85, "eur_usd": 1.10, "prob": 0.15},
        "Stabilizacja": {"usd_pln": 3.58, "eur_usd": 1.18, "prob": 0.25},
        "Konsensus (słaby USD)": {"usd_pln": 3.50, "eur_usd": 1.20, "prob": 0.60},
    }
    
    scenario_results = []
    for name, params in scenarios.items():
        monthly_cost = calc_monthly_costs(params["usd_pln"], params["eur_usd"])
        total_cost = monthly_cost * forecast_months
        runway = treasury_usdt / monthly_cost
        hedged_cost = calc_monthly_costs(usd_pln_start, eur_usd_start)
        hedged_total = hedged_cost * forecast_months * (1 + otc_spread + bank_fx_spread)
        savings = total_cost - hedged_total
        scenario_results.append({
            "Scenariusz": name,
            "Prawdop.": f"{params['prob']*100:.0f}%",
            "USD/PLN": params["usd_pln"],
            "EUR/USD": params["eur_usd"],
            "Koszt mies. (USD)": f"{monthly_cost:,.0f}",
            "Koszt total (USD)": f"{total_cost:,.0f}",
            "Runway (mies.)": f"{runway:.1f}",
            "Oszczędn. z hedge": f"{savings:,.0f}"
        })
    
    df_scenarios = pd.DataFrame(scenario_results)
    st.dataframe(df_scenarios, use_container_width=True, hide_index=True)
    
    # Expected value
    ev_unhedged = sum(calc_monthly_costs(s["usd_pln"], s["eur_usd"]) * forecast_months * s["prob"] for s in scenarios.values())
    ev_hedged = calc_monthly_costs(usd_pln_start, eur_usd_start) * forecast_months * (1 + otc_spread + bank_fx_spread)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Expected Value (bez hedge)", f"{ev_unhedged:,.0f} USD")
    with col2:
        st.metric("Koszt z hedgingiem", f"{ev_hedged:,.0f} USD")
    with col3:
        st.metric("Expected oszczędności", f"{ev_unhedged - ev_hedged:,.0f} USD")

# Tabela szczegółowa
st.markdown("---")
st.subheader("📋 Szczegółowe zestawienie miesięczne")

df = pd.DataFrame({
    "Miesiąc": months,
    "USD/PLN": usd_pln_path,
    "EUR/USD": eur_usd_path,
    "Koszt bez hedge (USD)": costs_unhedged,
    "Koszt z hedge (USD)": costs_hedged,
    "Koszt hedgingu (USD)": hedging_execution_costs,
    "Treasury bez hedge": treasury_unhedged,
    "Treasury z hedge": treasury_hedged,
})
df = df.round(2)
st.dataframe(df, use_container_width=True, hide_index=True)

# Podsumowanie
st.markdown("---")
st.subheader("📝 Podsumowanie rekomendacji")

total_hedging_cost = hedging_execution_costs.sum()
total_diff = cumulative_unhedged[-1] - (cumulative_hedged[-1] - total_hedging_cost)

if total_diff > total_hedging_cost:
    st.success(f"""
    ✅ **Hedging jest opłacalny** w założonym scenariuszu
    - Oszczędności brutto: **{total_diff:,.0f} USD**
    - Koszt hedgingu: **{total_hedging_cost:,.0f} USD**
    - Oszczędności netto: **{total_diff - total_hedging_cost:,.0f} USD**
    - Wydłużenie runway: **{delta_runway:.2f} miesiąca**
    """)
else:
    st.warning(f"""
    ⚠️ **Hedging może nie być opłacalny** w założonym scenariuszu
    - Różnica kosztów: **{total_diff:,.0f} USD**
    - Koszt hedgingu: **{total_hedging_cost:,.0f} USD**
    - Bilans: **{total_diff - total_hedging_cost:,.0f} USD**
    """)

st.markdown("""
---
### 🚀 Jak uruchomić na GitHub

1. Stwórz nowe repo na GitHub
2. Dodaj plik `requirements.txt`:
```
streamlit
pandas
numpy
plotly
```

3. Dodaj plik `app.py` z tym kodem

4. Połącz z [Streamlit Cloud](https://streamlit.io/cloud):
   - Zaloguj się kontem GitHub
   - Wybierz repo i branch
   - Wskaż `app.py` jako główny plik
   - Deploy!
""")
