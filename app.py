import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="RideSmart | Fleet Decision Support", page_icon="🚕", layout="wide")
DATA_DIR = Path(__file__).parent / "data"
FLEET_SIZE = 500
UTILISATION = 0.85

@st.cache_data
def load_data():
    capacity = pd.read_csv(DATA_DIR / "capacity_data.csv")
    movement = pd.read_csv(DATA_DIR / "movement_results.csv")
    capacity["pickup_date"] = pd.to_datetime(capacity["pickup_date"])
    movement["pickup_date"] = pd.to_datetime(movement["pickup_date"])
    return capacity, movement

capacity, movement = load_data()

def largest_remainder(weights, total):
    weights = np.asarray(weights, dtype=float)
    if total <= 0 or weights.sum() <= 0:
        return np.zeros(len(weights), dtype=int)
    exact = weights / weights.sum() * int(total)
    allocation = np.floor(exact).astype(int)
    remaining = int(total - allocation.sum())
    if remaining:
        allocation[np.argsort(-(exact - allocation))[:remaining]] += 1
    return allocation

def calculate_strategy(frame, strategy):
    d = frame.copy().reset_index(drop=True)
    deployable = min(FLEET_SIZE, int(np.ceil(d["required_vehicles"].sum())))
    weights = (d["required_vehicles"] if strategy == "Proportional"
               else d["predicted"]).clip(lower=0)
    d["vehicles"] = largest_remainder(weights, deployable)
    d["service_capacity"] = d["vehicles"] * 60 * UTILISATION / d["average_duration"]
    d["served"] = np.minimum(d["predicted"], d["service_capacity"])
    d["unserved"] = (d["predicted"] - d["served"]).clip(lower=0)
    return d

def build_strategy(strategy):
    return pd.concat([
        calculate_strategy(capacity[capacity["pickup_hour"] == h], strategy)
        for h in sorted(capacity["pickup_hour"].unique())
    ], ignore_index=True)

proportional = build_strategy("Proportional")
priority = build_strategy("Demand Priority")
movement_eval = movement.copy()
movement_eval["vehicles"] = movement_eval["constrained_vehicles"]
movement_eval["service_capacity"] = movement_eval["constrained_capacity"]
movement_eval["served"] = movement_eval["constrained_served"]
movement_eval["unserved"] = movement_eval["constrained_unserved"]

strategies = {
    "Proportional": proportional,
    "Demand Priority": priority,
    "Movement Constrained": movement_eval
}

def get_metrics(df):
    demand = float(df["predicted"].sum())
    served = float(df["served"].sum())
    return demand, served, max(0, demand - served), (served / demand * 100 if demand else 0)

st.title("🚕 RideSmart")
st.caption("Urban Mobility Fleet Demand Forecasting & Rebalancing Decision Support")
st.info("Academic prototype · NYC Yellow Taxi data · 15 March 2025 · 10 selected zones")
st.sidebar.header("Scenario controls")
hour = st.sidebar.slider("Hour of day", 0, 23, 18)
strategy_name = st.sidebar.selectbox("Allocation strategy", list(strategies), index=2)
fleet_hour = strategies[strategy_name]
selected = fleet_hour[fleet_hour["pickup_hour"] == hour].copy()
demand, served, unserved, coverage = get_metrics(selected)

a, b, c, d = st.columns(4)
a.metric("Vehicles deployed", f"{int(selected['vehicles'].sum()):,}")
b.metric("Forecast pickups", f"{demand:,.0f}")
c.metric("Estimated served", f"{served:,.0f}")
d.metric("Hourly coverage", f"{coverage:.1f}%")

st.divider()
left, right = st.columns([1.3, 1])
with left:
    st.subheader(f"Vehicle allocation by zone · {hour:02d}:00")
    plot_data = selected.sort_values("vehicles")
    fig = px.bar(plot_data, x="vehicles", y="Zone", orientation="h",
                 color="vehicles", color_continuous_scale="Blues",
                 labels={"vehicles": "Vehicles allocated", "Zone": ""})
    fig.update_layout(height=440, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Estimated demand coverage")
    fig = go.Figure(go.Pie(labels=["Served", "Unserved"], values=[served, unserved],
                           hole=0.58, marker=dict(colors=["#16A34A", "#F59E0B"])))
    fig.update_layout(height=330, margin=dict(t=25, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.metric("Estimated unserved pickups", f"{unserved:,.0f}")

st.subheader("Zone-level decision table")
table = selected[["Zone", "predicted", "vehicles", "service_capacity", "served", "unserved"]].copy()
table.columns = ["Zone", "Forecast pickups", "Vehicles allocated", "Estimated capacity", "Estimated served", "Estimated unserved"]
st.dataframe(table.sort_values("Estimated unserved", ascending=False).round(1), use_container_width=True, hide_index=True)

st.divider()
st.subheader("Full-day strategy comparison")
rows = []
for name, df in strategies.items():
    total, served_total, unserved_total, coverage_total = get_metrics(df)
    rows.append({"Strategy": name, "Predicted demand": total, "Estimated served": served_total,
                 "Estimated unserved": unserved_total, "Coverage (%)": coverage_total})
summary = pd.DataFrame(rows)
st.dataframe(summary.round(2), use_container_width=True, hide_index=True)
fig = px.bar(summary, x="Strategy", y="Coverage (%)", color="Strategy",
             text=summary["Coverage (%)"].map(lambda x: f"{x:.2f}%"),
             color_discrete_sequence=["#64748B", "#2563EB", "#16A34A"])
fig.update_layout(showlegend=False, yaxis_range=[0, 100], height=370)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Hourly demand coverage")
hourly_rows = []
for name, df in strategies.items():
    for h, group in df.groupby("pickup_hour"):
        m = get_metrics(group)
        hourly_rows.append({"Hour": h, "Strategy": name, "Coverage (%)": m[3]})
hourly = pd.DataFrame(hourly_rows)
fig = px.line(hourly, x="Hour", y="Coverage (%)", color="Strategy", markers=True,
              color_discrete_sequence=["#64748B", "#2563EB", "#16A34A"])
fig.update_layout(height=380, yaxis_range=[0, 100], xaxis=dict(dtick=1))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Movement constraint audit")
if strategy_name == "Movement Constrained":
    audit = movement.groupby("pickup_hour", as_index=False).agg(
        vehicles_moved=("vehicles_moved", "first"),
        fleet=("constrained_vehicles", "sum"))
    fig = go.Figure()
    fig.add_bar(x=audit["pickup_hour"], y=audit["vehicles_moved"], name="Allocation changes")
    fig.add_scatter(x=audit["pickup_hour"], y=[100] * len(audit), mode="lines",
                    name="Assumed limit (100)", line=dict(color="red", dash="dash"))
    fig.update_layout(height=330, xaxis_title="Hour", yaxis_title="Vehicles")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Movement counts measure changes between zone allocation snapshots, not tracked physical vehicle journeys.")
else:
    st.caption("Select Movement Constrained to inspect the hourly allocation-change audit.")

with st.expander("Model assumptions and limitations"):
    st.markdown("""
    - One-day prototype scenario: 15 March 2025, using ten selected NYC taxi zones.
    - Forecast values are imported from the notebook; this dashboard does not retrain the forecasting model.
    - Fleet size is capped at 500 vehicles and target utilisation is assumed to be 85%.
    - Required vehicles are estimated from predicted hourly pickups and average trip duration.
    - Proportional allocation weights zones by estimated required vehicles; demand-priority weights zones by predicted pickups.
    - The movement-constrained results come from a simplified simulation with a 100-vehicle hourly allocation-change limit and a central-reserve assumption.
    - No individual vehicle identities, trip destinations, traffic, deadheading, road-network travel times or real-time driver availability are modelled.
    - Results are illustrative decision-support estimates, not live dispatch instructions.
    """)
st.caption("RideSmart academic prototype · All results are simulated estimates.")
