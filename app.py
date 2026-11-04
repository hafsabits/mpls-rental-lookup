"""Rental Records: look up a Minneapolis rental's license, owner, and code violations."""

import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

st.set_page_config(page_title="Rental Records · Minneapolis", page_icon="🏠", layout="wide")

PROJECT = st.secrets["gcp"]["project_id"]
DATASET = st.secrets["gcp"]["dataset"]


def table(name: str) -> str:
    return f"`{PROJECT}.{DATASET}.{name}`"


def show(value, fmt: str = "{}") -> str:
    """Format a value for display, or show a dash when it's missing."""
    return "—" if pd.isna(value) else fmt.format(value)


@st.cache_resource
def get_client() -> bigquery.Client:
    credentials = service_account.Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"])
    )
    return bigquery.Client(credentials=credentials, project=PROJECT)


@st.cache_data(ttl=3600, show_spinner="Loading...")
def run_query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Run a query with safe parameters (never pasted into the SQL). Cached for an hour."""
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter(name, kind, value) for name, kind, value in params]
    )
    return get_client().query(sql, job_config=job_config).to_dataframe()


def show_owner(owner_key) -> None:
    """Owner summary, map, and list of every property they own."""
    if pd.isna(owner_key) or not owner_key:
        return
    owner = run_query(f"SELECT * FROM {table('owners')} WHERE owner_key = @k", (("k", "STRING", owner_key),))
    if owner.empty:
        return
    o = owner.iloc[0]

    st.markdown(f"### Owner: {o['owner_name']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Properties", show(o["properties"], "{:,}"))
    c2.metric("Units", show(o["units"], "{:,}"))
    c3.metric("Open violations", show(o["violations_open"], "{:,}"))
    c4.metric("Violations per unit (2 yrs)", show(o["violations_2yr_per_unit"], "{:.2f}"))

    portfolio = run_query(
        f"""SELECT address, units, tier, violations_open, violations_2yr,
                   violations_2yr_per_unit, latitude, longitude
            FROM {table('rental_properties')}
            WHERE owner_key = @k
            ORDER BY violations_2yr DESC""",
        (("k", "STRING", owner_key),),
    )
    st.map(portfolio.dropna(subset=["latitude", "longitude"]), latitude="latitude", longitude="longitude")
    st.dataframe(portfolio.drop(columns=["latitude", "longitude"]), hide_index=True)
    st.caption(
        "Owners are matched by the name on the rental license. One landlord may use "
        "several LLC names that are not yet grouped together."
    )


def show_property(p: pd.Series) -> None:
    """Property details, its violation history, and its owner."""
    st.subheader(p["address"])
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("License tier", show(p["tier"]))
    c2.metric("Units", show(p["units"], "{:,}"))
    c3.metric("Open violations", show(p["violations_open"], "{:,}"))
    c4.metric("Violations, last 2 yrs", show(p["violations_2yr"], "{:,}"))
    c5.metric("Per unit, last 2 yrs", show(p["violations_2yr_per_unit"], "{:.2f}"))

    st.markdown(
        f"**Owner:** {show(p['owner_name'])}  \n"
        f"**License:** {show(p['license_number'])} · {show(p['status'])} · expires {show(p['expiration_date'])}  \n"
        f"**Neighborhood:** {show(p['neighborhood'])}"
    )

    if not pd.isna(p["apn"]):
        violations = run_query(
            f"""SELECT processed_date, category, description, status, resolved_date
                FROM {table('violations_clean')}
                WHERE apn = @apn
                ORDER BY processed_date DESC""",
            (("apn", "STRING", p["apn"]),),
        )
        st.markdown(f"#### Code violations since 2016 ({len(violations):,})")
        if violations.empty:
            st.success("No code violations on record for this parcel since 2016.")
        else:
            st.bar_chart(violations["category"].value_counts())
            st.dataframe(violations, hide_index=True)
        st.caption(
            "Violations are recorded by parcel and may predate the current owner. "
            "Commercial fire inspections are not included."
        )

    show_owner(p["owner_key"])


# ---------- Page ----------

st.title("🏠 Rental Records")
st.markdown(
    "Look up any licensed rental in Minneapolis: its license, who owns it, "
    "and its history of city code violations."
)

last_updated = run_query(f"SELECT MAX(loaded_at) AS t FROM {table('rental_properties')}")["t"].iloc[0]
st.caption(f"Data from the City of Minneapolis · last updated {last_updated:%B %d, %Y}")

tab_search, tab_owners, tab_about = st.tabs(["Look up an address", "Largest owners", "About"])

with tab_search:
    query = st.text_input("Street address", placeholder="e.g. 2400 Lyndale, or Lake St")
    if len(query.strip()) >= 3:
        matches = run_query(
            f"""SELECT * FROM {table('rental_properties')}
                WHERE address_search LIKE @pattern
                ORDER BY address
                LIMIT 50""",
            (("pattern", "STRING", f"%{query.strip().upper()}%"),),
        )
        if matches.empty:
            st.info("No licensed rentals match. Try fewer words, like the house number and street name.")
        else:
            choice = st.selectbox(
                f"{len(matches)} matching rentals",
                matches.index,
                format_func=lambda i: f"{matches.at[i, 'address']}  ({show(matches.at[i, 'owner_name'])})",
            )
            show_property(matches.loc[choice])

with tab_owners:
    st.markdown("The largest rental owners in Minneapolis, by number of licensed units.")
    top = run_query(
        f"""SELECT owner_key, owner_name, properties, units, violations_open,
                   violations_2yr, violations_2yr_per_unit
            FROM {table('owners')}
            ORDER BY units DESC
            LIMIT 50"""
    )
    st.dataframe(top.drop(columns=["owner_key"]), hide_index=True)
    pick = st.selectbox(
        "See an owner's properties",
        top.index,
        index=None,
        placeholder="Choose an owner",
        format_func=lambda i: top.at[i, "owner_name"],
    )
    if pick is not None:
        show_owner(top.at[pick, "owner_key"])

with tab_about:
    st.markdown(
        """
**What this is.** A free tool that brings Minneapolis public records about rental
housing into one place, so renters can check a property and its owner before signing a lease.

**Data sources.** City of Minneapolis Open Data: Active Rental Licenses and code
violation cases (2016 to present). Updated weekly.

**How to read it.** Violations include routine inspection findings, many of them minor.
Open violations and recent ones matter most. "Per unit" adjusts for building size,
so large buildings and duplexes compare fairly.

**Privacy.** Owner phone numbers and emails published by the city are left out on purpose.

**Disclaimer.** This data comes from public records and may contain errors or be out of date.
It is not legal advice. Violations may predate the current owner.
"""
    )