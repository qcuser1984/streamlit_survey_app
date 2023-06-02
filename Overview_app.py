'''Experimental web app prototype to summarize 
   survey progress and survey statistics all in
   one place with the access for different users
   across the local network
'''
#standard library imports
import os
from datetime import datetime
#fancy modules imports
import pandas as pd
import streamlit as st
import plotly.express as px

__version__="Beta 0.0.1"    #March 2023

proj_name = "ARAM 3D"
fourD_nav = r"Q:\06-ARAM\nav\Postplot_R\4dnav_lines\BR001522_4dnav.csv"

#fully rely on 4dnav output as data source for the receivers
def read_4dnav(file_path):
    if os.path.exists(file_path) and os.stat(file_path).st_size != 0:
        try:
            nav_df=pd.read_csv(file_path, skiprows=8)
            nav_df['DeploymentDateTime'] = nav_df["Aslaid Time"].apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f"))
            nav_df['DeploymentDate'] = nav_df['DeploymentDateTime'].apply(lambda x: x.date())
            nav_df['DeploymentJulianDay'] = nav_df['DeploymentDate'].apply(lambda x: int(datetime.strftime(x, "%j")))
            nav_df.rename(columns={"Preplot Easting":"PreplotEasting","Preplot Northing":"PreplotNorthing","Preplot Depth":"PreplotDepth",
                       "Aslaid Easting":"AslaidEasting","Aslaid Northing":"AslaidNorthing","Aslaid Depth":"AslaidDepth",
                       "Aslaid Tide Offset":"AslaidTideOffset","Aslaid Azimuth":"AslaidAzimuth","Is Aslaid Adjusted":"IsAslaidAdjusted",
                       "Recovered Time":"RecoveryDateTime","Recovered Easting":"RecoveredEasting","Recovered Northing":"RecoveredNorthing",
                       "Recovered Depth":"Recovered Depth", "Recovered Tide Offset":"RecoveredTideOffset","Recovered Azimuth":"RecoveredAzimuth",
                       "Is Recovered Adjusted":"IsRecoveredAdjusted","Deployed by ROV":"DeploymentROV","Recovered by ROV":"RecoveryROV"}, inplace=True)
            nav_df.drop(columns=["Aslaid Time","DeployedComments","RecoveredComments"], inplace=True)
            nav_df.fillna(0,inplace=True)
            return nav_df
        except Exception as exc:
            print(f"{exc}")
            return None
    else:
        return None

#basic application page config
st.set_page_config(
    page_title=f"{proj_name} overview",
    page_icon=":ocean:",
    layout="wide",
    menu_items = {'Get Help': "https://docs.streamlit.io",
    "Report a bug": "https://docs.streamlit.io/library/cheatsheet",
    "About":'# Really have *no idea* what that is!'}
    )

f"# {proj_name} overview app v. {__version__}"
#st.markdown()
st.sidebar.success(" ### Select option above")

receivers_df = read_4dnav(fourD_nav)

if st.checkbox("Project raw data"):
    st.text(f"Source: {fourD_nav}")
    st.dataframe(receivers_df)

st.markdown("---")
" ### Pre-beta version of survey overview web application"