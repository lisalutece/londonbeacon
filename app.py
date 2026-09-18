"""
====================================================================
LONDONBEACON
A touristic Streamlit app that helps people discover London
attractions and get simple walking directions to them.

WHAT THIS FILE DOES (top to bottom):
  1. Imports the libraries we need.
  2. Sets basic page settings (title, layout).
  3. Loads the attraction data from a CSV file.
  4. Injects custom CSS to create the background image, dark overlay,
     and to style the dropdown/chat boxes for good contrast.
  5. Draws the page: hero title -> category dropdown -> chatbot -> map.
  6. Small helper functions do the "thinking":
       - turning a typed address into GPS coordinates (geocoding)
       - measuring distance between two GPS points
       - asking OSRM for a walking route
       - drawing everything on a Folium map

HOW TO RUN THIS APP:
    streamlit run app.py

FOLDER STRUCTURE THIS FILE EXPECTS:
    app.py
    data/london_attractions.csv
    assets/london_3d_bg.png
    requirements.txt
====================================================================
"""

# ----------------------------------------------------------------
# STEP 1: IMPORTS
# ----------------------------------------------------------------
import base64                              # turns the background image into text so CSS can use it
from pathlib import Path                   # makes file paths work on Mac/Windows/Linux the same way

import folium                              # draws the interactive map (OpenStreetMap based)
import pandas as pd                        # reads and filters our CSV data
import requests                            # used to call the free OSRM walking-route API
import streamlit as st                     # the web app framework itself
import streamlit.components.v1 as components  # lets us inject the optional GPS JavaScript button
from geopy.distance import geodesic        # calculates distance in km between two GPS points
from geopy.geocoders import Nominatim      # turns a typed place name into GPS coordinates
from streamlit_folium import st_folium     # shows a Folium map inside a Streamlit app


# ----------------------------------------------------------------
# STEP 2: PAGE SETTINGS
# This MUST be the first Streamlit command in the whole script.
# ----------------------------------------------------------------
st.set_page_config(
    page_title="LONDONBEACON",
    page_icon="🇬🇧",
    layout="wide",
)

# Folder locations, worked out relative to this file so the app
# runs correctly no matter where it is opened from.
BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "london_attractions.csv"
BG_IMAGE_PATH = BASE_DIR / "assets" / "london_3d_bg.png"

# The categories shown in the dropdown menu. These must match the
# "category" column values used inside the CSV file exactly.
CATEGORIES = [
    "Parks", "Walks", "Museums", "Landmarks", "Vantage Points",
    "Markets", "Theatre/Cinemas", "Pubs", "Bars", "Restaurants",
]

# A fallback map centre (central London) used before any location is known.
LONDON_CENTER = (51.5074, -0.1278)


# ----------------------------------------------------------------
# STEP 3: LOAD DATA
# @st.cache_data means Streamlit only reads the file ONCE and
# reuses the result, instead of re-reading the CSV on every click.
# ----------------------------------------------------------------
@st.cache_data
def load_attractions() -> pd.DataFrame:
    """Read the attractions CSV into a pandas DataFrame (a table)."""
    df = pd.read_csv(DATA_PATH)
    df["category"] = df["category"].str.strip()  # remove stray spaces, just in case
    return df


@st.cache_data
def get_background_image_base64() -> str:
    """
    Convert the background PNG into a base64 text string.
    CSS can embed an image directly as text using this trick,
    so we don't need to host the image anywhere online.
    """
    image_bytes = BG_IMAGE_PATH.read_bytes()
    return base64.b64encode(image_bytes).decode()


# ----------------------------------------------------------------
# STEP 4: CUSTOM CSS (background, dark overlay, widget styling)
# ----------------------------------------------------------------
def inject_custom_css() -> None:
    """
    Adds our own CSS to the page using st.markdown(unsafe_allow_html=True).
    This is the standard, supported way to style a Streamlit app.
    """
    bg_base64 = get_background_image_base64()

    st.markdown(
        f"""
        <style>
        /* Hide Streamlit's default hamburger menu, footer and header bar
           so the app looks like a clean, standalone website. */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}

        /* Overall page background colour (used below the hero image). */
        .stApp {{
            background-color: #0b0b12;
        }}

        /* Keep the page content nicely centred and not too wide. */
        .block-container {{
            padding-top: 0rem;
            max-width: 1300px;
        }}

        /* --- THE HERO SECTION ---
           This is the full-width image at the top of the page.
           A dark gradient is layered on TOP of the image using
           linear-gradient(), so the bottom of the picture fades
           into a dark, high-contrast background. That dark area is
           where the dropdown and chatbot will visually "sit". */
        .lb-hero {{
            position: relative;
            width: 100vw;
            margin-left: calc(-50vw + 50%);   /* stretches hero edge-to-edge */
            height: 60vh;
            min-height: 380px;
            background-image:
                linear-gradient(
                    to bottom,
                    rgba(5,5,10,0.05) 0%,
                    rgba(5,5,10,0.25) 55%,
                    rgba(5,5,10,0.85) 85%,
                    #0b0b12 100%
                ),
                url("data:image/png;base64,{bg_base64}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-end;
            text-align: center;
            padding-bottom: 1.5rem;
        }}

        /* The big "LONDONBEACON" title text on top of the hero image. */
        .lb-title {{
            font-family: 'Trebuchet MS', 'Segoe UI', sans-serif;
            font-weight: 800;
            font-size: clamp(2.2rem, 6vw, 4rem);
            letter-spacing: 0.12em;
            color: #ffffff;
            text-shadow: 0 4px 18px rgba(0,0,0,0.8);
            margin: 0;
        }}

        .lb-subtitle {{
            font-family: 'Segoe UI', sans-serif;
            font-size: clamp(0.9rem, 1.6vw, 1.1rem);
            color: #f3e6da;
            letter-spacing: 0.08em;
            text-shadow: 0 2px 10px rgba(0,0,0,0.8);
            margin-top: 0.4rem;
        }}

        /* Section headings used further down the page. */
        .lb-section-title {{
            font-family: 'Segoe UI', sans-serif;
            font-weight: 700;
            font-size: 1.3rem;
            color: #f5f2ec;
            border-left: 4px solid #e0724a;
            padding-left: 0.6rem;
            margin: 1.2rem 0 0.8rem 0;
        }}

        /* A styled "card" used to list each attraction. */
        .lb-card {{
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 10px;
            padding: 0.8rem 1rem;
            margin-bottom: 0.5rem;
            color: #f5f2ec;
        }}
        .lb-card b {{ color: #f0a684; }}
        .lb-card .lb-meta {{ color: #b9b3a8; font-size: 0.85rem; }}

        /* Make the dropdown (selectbox) readable on the dark background. */
        div[data-baseweb="select"] > div {{
            background-color: #1b1b28;
            color: #f5f2ec;
            border-color: rgba(255,255,255,0.15);
        }}

        /* Make the chat input box readable on the dark background. */
        .stChatInput textarea, .stChatInput input {{
            background-color: #1b1b28 !important;
            color: #f5f2ec !important;
        }}

        /* Slightly highlight chat bubbles so they stand out. */
        div[data-testid="stChatMessage"] {{
            background-color: rgba(255,255,255,0.05);
            border-radius: 12px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    """Draws the hero banner: background image + big title text on top."""
    # NOTE: the title "LONDONBEACON" is already part of the background
    # photo itself, so we only add the tagline here (not another
    # <h1> title) to avoid showing the name twice.
    st.markdown(
        """
        <div class="lb-hero">
            <div class="lb-subtitle">YOUR GUIDE TO LONDON &mdash; PARKS · LANDMARKS · FOOD · CULTURE</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------
# STEP 5: HELPER FUNCTIONS (the "brains" of the app)
# ----------------------------------------------------------------
def geocode_location(place_text: str):
    """
    Turns a typed place name (e.g. "Covent Garden") into GPS
    coordinates (latitude, longitude) using the free Nominatim
    (OpenStreetMap) geocoding service.

    Returns a (latitude, longitude) tuple, or None if not found.
    """
    geolocator = Nominatim(user_agent="londonbeacon_app")
    try:
        # We add ", London, UK" so short inputs like "Soho" geocode
        # inside London instead of matching a place elsewhere.
        result = geolocator.geocode(f"{place_text}, London, UK", timeout=10)
        if result is None:
            return None
        return (result.latitude, result.longitude)
    except Exception:
        # Any network/timeout problem -> treat it as "not found"
        # instead of crashing the whole app.
        return None


def find_nearby_attractions(df: pd.DataFrame, user_location, radius_km: float = 1.0, top_n: int = 5):
    """
    Given the user's (lat, lon) location, find the closest attractions
    in the dataset.

    Steps:
      1. Calculate the distance from the user to every attraction.
      2. Keep only the ones within `radius_km`.
      3. If nothing is that close, just take the closest ones anyway
         (so the chatbot always has something useful to say).
      4. Sort by distance and return the top N.
    """
    df = df.copy()
    df["distance_km"] = df.apply(
        lambda row: geodesic(user_location, (row["latitude"], row["longitude"])).km,
        axis=1,
    )

    nearby = df[df["distance_km"] <= radius_km].sort_values("distance_km")

    if nearby.empty:
        # Nothing within the radius: fall back to "closest overall".
        nearby = df.sort_values("distance_km")

    return nearby.head(top_n)


def get_walking_route(start, end):
    """
    Asks the free public OSRM routing server for a walking path
    between two GPS points, and returns a list of (lat, lon) points
    describing the route.

    If the API call fails for any reason (no internet, service down),
    we fall back to a simple straight line between start and end so
    the map still shows *something*.
    """
    try:
        # OSRM expects coordinates as "longitude,latitude" (opposite order!).
        url = (
            f"http://router.project-osrm.org/route/v1/foot/"
            f"{start[1]},{start[0]};{end[1]},{end[0]}"
            f"?overview=full&geometries=geojson"
        )
        response = requests.get(url, timeout=5)
        data = response.json()
        # The route coordinates come back as [lon, lat] pairs, so we
        # flip each pair to (lat, lon) for Folium.
        coordinates = data["routes"][0]["geometry"]["coordinates"]
        return [(lat, lon) for lon, lat in coordinates]
    except Exception:
        # Simple fallback: a straight line from start to end.
        return [start, end]


def build_map(user_location, recommendations: pd.DataFrame, route_points):
    """
    Builds a Folium map showing:
      - a marker for the user's location
      - a marker for each recommended attraction
      - a walking route line to the closest (top) recommendation
    """
    fmap = folium.Map(location=user_location, zoom_start=15, tiles="OpenStreetMap")

    # Marker for "you are here".
    folium.Marker(
        location=user_location,
        popup="You are here",
        icon=folium.Icon(color="blue", icon="user"),
    ).add_to(fmap)

    # One marker per recommended attraction.
    for _, row in recommendations.iterrows():
        folium.Marker(
            location=(row["latitude"], row["longitude"]),
            popup=f"{row['name']} ({row['distance_km']:.2f} km)",
            tooltip=row["name"],
            icon=folium.Icon(color="red", icon="info-sign"),
        ).add_to(fmap)

    # Draw the walking route as a coloured line.
    folium.PolyLine(route_points, color="#e0724a", weight=5, opacity=0.8).add_to(fmap)

    return fmap


# ----------------------------------------------------------------
# STEP 6: PAGE SECTIONS
# ----------------------------------------------------------------
def render_category_browser(df: pd.DataFrame) -> None:
    """Dropdown menu + list of the top 10 attractions in that category."""
    st.markdown('<div class="lb-section-title">Browse by Category</div>', unsafe_allow_html=True)

    category = st.selectbox("Choose what you're in the mood for:", CATEGORIES)

    # Filter the table to only rows matching the chosen category,
    # then keep at most the first 10 rows.
    top_places = df[df["category"] == category].head(10)

    for _, row in top_places.iterrows():
        st.markdown(
            f"""
            <div class="lb-card">
                <b>{row['name']}</b> &nbsp;<span class="lb-meta">({row['category']})</span><br>
                <span class="lb-meta">{row['description']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_gps_button() -> None:
    """
    OPTIONAL BONUS FEATURE - "Use My Current Location" button.

    Streamlit (Python) cannot read the browser's GPS by itself, so we
    inject a small piece of JavaScript using st.components.v1.html().
    When clicked, the JS asks the browser for the user's location, then
    reloads the page adding ?lat=...&lon=... to the URL. Streamlit can
    then read those values with st.query_params (see render_chatbot).

    Note: browsers only allow the Geolocation API on secure pages
    (https:// or localhost), so this button may not work if the app is
    opened over a plain http:// address.
    """
    components.html(
        """
        <button id="lb-gps-btn" style="
            background-color:#e0724a; color:white; border:none;
            padding:0.5rem 1rem; border-radius:8px; font-weight:600;
            cursor:pointer;">
            Use My Current Location
        </button>
        <script>
        const btn = document.getElementById("lb-gps-btn");
        btn.onclick = function() {
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;
                    // Reload the Streamlit page with the coordinates in the URL.
                    const url = new URL(window.parent.location.href);
                    url.searchParams.set("lat", lat);
                    url.searchParams.set("lon", lon);
                    window.parent.location.href = url.toString();
                },
                function(error) {
                    alert("Could not get your location: " + error.message);
                }
            );
        };
        </script>
        """,
        height=50,
    )


def render_chatbot(df: pd.DataFrame) -> None:
    """Chat interface: user types where they are, app replies with nearby ideas + a map."""
    st.markdown('<div class="lb-section-title">Ask LondonBeacon</div>', unsafe_allow_html=True)
    st.write("Tell me where you are (e.g. *\"Near Covent Garden\"* or *\"King's Cross Station\"*) "
             "and I'll suggest nearby places.")

    # st.session_state keeps data between reruns (Streamlit reruns the
    # whole script on every interaction, so without session_state we
    # would lose the chat history each time).
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "last_map_data" not in st.session_state:
        st.session_state.last_map_data = None

    # OPTIONAL BONUS: the "Use My Current Location" button above sets
    # ?lat=..&lon=.. on the page URL. We check for that here, once per
    # session, and treat it just like a typed chat message.
    render_gps_button()
    query_params = st.query_params
    if "lat" in query_params and "lon" in query_params and not st.session_state.get("gps_used"):
        st.session_state.gps_used = True  # only auto-run this once
        gps_location = (float(query_params["lat"]), float(query_params["lon"]))
        gps_text = f"My current GPS location ({gps_location[0]:.4f}, {gps_location[1]:.4f})"
        st.session_state.chat_history.append({"role": "user", "content": gps_text})
        recommendations = find_nearby_attractions(df, gps_location, radius_km=1.0, top_n=5)
        reply_lines = ["Here's what's nearby:"]
        for i, (_, row) in enumerate(recommendations.iterrows(), start=1):
            reply_lines.append(
                f"**{i}. {row['name']}** ({row['category']}) - "
                f"{row['distance_km']:.2f} km away. {row['description']}"
            )
        st.session_state.chat_history.append({"role": "assistant", "content": "\n\n".join(reply_lines)})
        top_pick = recommendations.iloc[0]
        route_points = get_walking_route(gps_location, (top_pick["latitude"], top_pick["longitude"]))
        st.session_state.last_map_data = (gps_location, recommendations, route_points)

    # Show all previous chat messages.
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # If we already have a location + recommendations, keep showing the map.
    if st.session_state.last_map_data is not None:
        user_location, recommendations, route_points = st.session_state.last_map_data
        fmap = build_map(user_location, recommendations, route_points)
        st_folium(fmap, width=None, height=420, key="lb_map")

    # The text box where the user types their location.
    user_input = st.chat_input("Where are you right now?")

    if user_input:
        # 1) Show the user's own message in the chat.
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # 2) Turn the typed text into GPS coordinates.
        with st.spinner("Finding that on the map..."):
            user_location = geocode_location(user_input)

        if user_location is None:
            reply = ("I couldn't find that place. Try a more specific landmark, "
                      "station, or postcode - e.g. \"Near Covent Garden\" or \"SW1A 1AA\".")
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            st.session_state.last_map_data = None
        else:
            # 3) Find nearby attractions and build a friendly reply.
            recommendations = find_nearby_attractions(df, user_location, radius_km=1.0, top_n=5)

            reply_lines = ["Here's what's nearby:"]
            for i, (_, row) in enumerate(recommendations.iterrows(), start=1):
                reply_lines.append(
                    f"**{i}. {row['name']}** ({row['category']}) - "
                    f"{row['distance_km']:.2f} km away. {row['description']}"
                )
            reply = "\n\n".join(reply_lines)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})

            # 4) Work out a walking route to the closest recommendation
            #    and save everything needed to redraw the map.
            top_pick = recommendations.iloc[0]
            route_points = get_walking_route(user_location, (top_pick["latitude"], top_pick["longitude"]))
            st.session_state.last_map_data = (user_location, recommendations, route_points)

        # Rerun the app so the new message + map appear immediately.
        st.rerun()


# ----------------------------------------------------------------
# STEP 7: MAIN — runs the whole app, top to bottom
# ----------------------------------------------------------------
def main() -> None:
    inject_custom_css()
    render_hero()

    attractions_df = load_attractions()

    # Two columns side by side: dropdown/list on the left,
    # chatbot + map on the right. On narrow (mobile) screens
    # Streamlit automatically stacks columns instead of squashing them.
    left_column, right_column = st.columns([1, 1.3], gap="large")

    with left_column:
        render_category_browser(attractions_df)

    with right_column:
        render_chatbot(attractions_df)


if __name__ == "__main__":
    main()
