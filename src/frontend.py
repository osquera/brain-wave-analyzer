import os
from http import HTTPStatus

import pandas as pd
import requests
import streamlit as st
from requests.exceptions import Timeout

# Set page config
st.set_page_config(page_title="Brain Wave Analyzer", page_icon="🧠", layout="wide")

# Define the API URL
API_URL = os.getenv("API_URL", "http://localhost:8000")

# App header
st.title("🧠 Brain Wave Analyzer")
st.markdown("Upload an EDF file to analyze brain wave patterns and frequency bands.")

# File upload section
st.subheader("Upload EEG Recording")
uploaded_file = st.file_uploader("Choose an EDF file", type="edf")

if uploaded_file is not None:
    # Create a progress indicator
    with st.spinner("Processing EEG data..."):
        # Send the file to the API
        files = {"file": uploaded_file}

        try:
            response = requests.post(f"{API_URL}/analyze-edf/", files=files, timeout=30)

            if response.status_code == HTTPStatus.OK:
                # Get the results
                data = response.json()
                results = data["results"]

                # Create columns for the results
                st.subheader("Analysis Results")

                col1, col2, col3 = st.columns(3)

                # Get the image URLs
                freq_bands_url = f"{API_URL}{results['plot_urls']['frequency_bands_plot']}"
                avg_power_url = f"{API_URL}{results['plot_urls']['average_power_plot']}"
                rel_power_url = f"{API_URL}{results['plot_urls']['relative_power_plot']}"

                # Get the images from the API
                freq_bands_img = requests.get(freq_bands_url, timeout=10).content
                avg_power_img = requests.get(avg_power_url, timeout=10).content
                rel_power_img = requests.get(rel_power_url, timeout=10).content

                # Display the images
                with col1:
                    st.image(
                        freq_bands_img,
                        caption="Frequency Band Analysis",
                        use_column_width=True,
                    )

                with col2:
                    st.image(avg_power_img, caption="Average Power", use_column_width=True)

                with col3:
                    st.image(rel_power_img, caption="Relative Power", use_column_width=True)

                # Create a dataframe with the results
                st.subheader("Frequency Band Data")
                freq_bands = results["freq_bands"]
                avg_power = results["average_power"]
                rel_power = results["relative_power"]

                df = pd.DataFrame(
                    {
                        "Frequency Band": freq_bands,
                        "Average Power (dB/Hz)": avg_power,
                        "Relative Power": rel_power,
                    }
                )

                # Round the values for better display
                df["Average Power (dB/Hz)"] = df["Average Power (dB/Hz)"].round(4)
                df["Relative Power"] = df["Relative Power"].round(4)

                st.dataframe(df)

                # Add a download button for the data
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download Results as CSV",
                    csv,
                    "brain_wave_analysis.csv",
                    "text/csv",
                    key="download-csv",
                )

        except Timeout:
            st.error("Request timed out. The server might be overloaded or down.")
        except ConnectionError:
            st.error("Connection error. Please check if the backend server is running.")
        except requests.RequestException as err:
            # Catch specific request-related exceptions
            st.error(f"Error making request: {err!s}")
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
else:
    # Show info when no file is uploaded
    st.info("Please upload an EDF file to begin analysis.")

# Add an explanation section
with st.expander("About Brain Wave Frequency Bands"):
    st.markdown("""
    ## Brain Wave Frequency Bands

    The brain waves are categorized into five main frequency bands:

    - **Delta (0.5-4 Hz)**
    - **Theta (4-8 Hz)**
    - **Alpha (8-13 Hz)**
    - **Beta (13-30 Hz)**
    - **Gamma (30+ Hz)**

    This analyzer helps identify the distribution and power of these frequency bands in EEG recordings.
    """)

# Footer
st.markdown("---")
st.markdown("Brain Wave Analyzer | EEG Analysis Tool")
