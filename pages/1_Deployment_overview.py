#standard library imports
import os
import random
from datetime import datetime, timezone, timedelta

import warnings
warnings.filterwarnings('ignore')

#fancy modules imports
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


SPS_R_PREPLOT = r"Q:\06-ARAM\nav\preplot.r01"              #theoretical sps-r
FOURD_NAV = r"Q:\06-ARAM\nav\Postplot_R\4dnav_lines\BR001522_4dnav.csv"        #production file
# the actual cumulative on the surveyors side
SURVEY_SIDE_CSV = r"X:\Projects\07_BR001522_ARAM_Petrobras\06_SURVEY\26.QC\TO\MT1001522_CumulativeCSV.csv"


def add_error(number, error=11):
    ''' add some deviation in percents to a value '''
    return round(number * (random.randint(-error, error)/100+1))

def sps_to_frame_skip(path_to_sps,char):
    '''get a number of rows to skip to account for header'''
    try:
        with open(path_to_sps, 'r',encoding='utf-8') as file:
            lines = file.readlines()
            first_data_line=[i for i in lines if i.startswith(char)][0]
            to_skip=int(lines.index(first_data_line))
            return to_skip
    except Exception as exc:
        print(f'Something went wrong: {exc}')
        return None

#get only the deployment related columns from 4dnav
def read_4dnav_for_receivers(file_path):
    if os.path.exists(file_path) and os.stat(file_path).st_size != 0:
        try:
            nav_df=pd.read_csv(file_path, skiprows=8)
            nav_df['DeploymentDateTime'] = nav_df["Aslaid Time"].apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f"))
            nav_df['DeploymentDate'] = nav_df['DeploymentDateTime'].apply(lambda x: x.date())
            nav_df['JulianDay'] = nav_df['DeploymentDate'].apply(lambda x: int(datetime.strftime(x, "%j")))
            nav_df["DeploymentDateStr"] = nav_df['DeploymentDate'].apply(lambda x: datetime.strftime(x, "%Y-%m-%d"))
            nav_df["OnSeabed"] = (datetime.utcnow() - nav_df['DeploymentDateTime']).dt.days + 1
            nav_df.rename(columns={"Preplot Easting":"PreplotEasting",
                       "Preplot Northing":"PreplotNorthing","Preplot Depth":"PreplotDepth",
                       "Aslaid Easting":"AslaidEasting","Aslaid Northing":"AslaidNorthing","Aslaid Depth":"AslaidDepth",
                       "Aslaid Tide Offset":"AslaidTideOffset",
                       "Aslaid Azimuth":"AslaidAzimuth","Is Aslaid Adjusted":"IsAslaidAdjusted",
                       "Recovered Time":"RecoveryDateTime","Recovered Easting":"RecoveredEasting",
                       "Recovered Northing":"RecoveredNorthing",
                       "Recovered Depth":"RecoveredDepth", "Recovered Tide Offset":"RecoveredTideOffset",
                       "Recovered Azimuth":"RecoveredAzimuth",
                       "Is Recovered Adjusted":"IsRecoveredAdjusted",
                       "Deployed by ROV":"DeploymentROV","Recovered by ROV":"RecoveryROV"}, inplace=True)
            nav_df.drop(columns=["Aslaid Time","RecoveredComments"], inplace=True)
            nav_df = nav_df[["Line","Point","NodeCode","Index","PreplotEasting","PreplotNorthing","PreplotDepth",
                            "AslaidEasting","AslaidNorthing","AslaidDepth","AslaidTideOffset","AslaidAzimuth",
                            "PreplotToAslaidDistance",'PreplotToAslaidBearing',"PreplotToAslaidAlongTrack",
                            "PreplotToAslaidCrossTrack",'DeploymentROV','DeploymentDateTime',
                            "DeploymentDate",'JulianDay',"OnSeabed","DeploymentDateStr"]]
            nav_df.fillna(0,inplace=True)
            return nav_df
        except Exception as exc:
            print(f"{exc}")
            return None
    else:
        return None


#generate deployment stats dataframe based 
def get_deployment_stats_df(df_in):
    '''provide deployment statistics
       in form of dataFrame
       Easy to plot
    '''
    project_start = datetime.strptime("20230218", "%Y%m%d")
    project_timeline = pd.date_range(project_start,datetime.utcnow())
    timeline_df = pd.DataFrame(project_timeline, columns = ["Date"])
    timeline_df["Date"] = timeline_df["Date"].apply(lambda x : x.date())
    timeline_df["Date"] = pd.to_datetime(timeline_df["Date"]) ### <<< = really important!
    timeline_df['JulianDay'] = timeline_df['Date'].apply(lambda x: int(datetime.strftime(x, "%j")))
    counts_df = df_in.groupby("JulianDay").agg({"Point" : 'count'})
    counts_df["NodesDeployed"] = counts_df["Point"]
    counts_df.drop(columns = ["Point"], inplace = True)
    prod_df = pd.merge(timeline_df, counts_df, how = "outer", on = "JulianDay")
    #below dfs for both ROVs
    xlx_df = df_in.query('DeploymentROV == "XLX19"')
    uhd_df = df_in.query('DeploymentROV == "UHD64"')
    xlx_df = xlx_df.groupby("JulianDay").agg({"DeploymentROV" : "count"})
    uhd_df = uhd_df.groupby("JulianDay").agg({"DeploymentROV" : "count"})
    xlx_df.rename(columns={"DeploymentROV":"XLX19"},inplace=True)
    uhd_df.rename(columns={"DeploymentROV":"UHD64"},inplace=True)
    #merge all together
    prod_df = pd.merge(prod_df, xlx_df, how = "outer", on = "JulianDay")
    prod_df = pd.merge(prod_df, uhd_df, how = "outer", on = "JulianDay")
    prod_df.fillna(0, inplace=True)
    prod_df["TotalDeployed"] = (prod_df["NodesDeployed"].cumsum()).astype(int)
    prod_df["TotalByXLX19"] = (prod_df["XLX19"].cumsum()).astype(int)
    prod_df["TotalByUHD64"] = (prod_df["UHD64"].cumsum()).astype(int)
    prod_df["DeploymentComplete"] = round((prod_df["TotalDeployed"]/4071)*100,2)
    prod_df["IncreaseBy"] = round(prod_df["DeploymentComplete"].diff(),2)
    prod_df["XLX19_diff"] = round(prod_df["XLX19"].diff(),2)
    prod_df["UHD64_diff"] = round(prod_df["UHD64"].diff(),2)

    #statistics
    prod_df["rolling_3d_sum"] = prod_df.rolling(window = 3, on = "Date").NodesDeployed.sum()
    prod_df["rolling_3d_avg"] = round(prod_df.rolling(window = 3, on = "Date").NodesDeployed.mean())
    prod_df["rolling_3d_min"] = round(prod_df.rolling(window = 3, on = "Date").NodesDeployed.min(),2)
    prod_df["rolling_3d_max"] = round(prod_df.rolling(window = '3d', on = "Date").NodesDeployed.max(),2)

    prod_df.fillna(0.0,inplace = True, axis = 1)
    return prod_df

def predict_with_rolling(prod_df):
    '''experimental feature
       predict production based 
       on rolling min max and avg
       for the previous 5 days
    '''
    dates_df = pd.DataFrame(pd.date_range(prod_df.Date.max(), periods = 6), columns = ["Date"])
    predict_df = pd.merge(prod_df, dates_df, how = "outer", on = "Date")
    std = int(predict_df["NodesDeployed"][len(predict_df) - 9 : len(predict_df) - 6].std())        #standart deviation for the last three days prior to today
    predict_df = predict_df[len(predict_df) - 6 :]
    predict_df.fillna(method = "ffill", inplace = True)
    #below add standard deviation as percentage for mean, mix and max values 
    predict_df["rolling_3d_avg"][1:] = predict_df["rolling_3d_avg"][1:].apply(lambda x: add_error(x, error = std))
    predict_df["rolling_3d_min"][1:] = predict_df["rolling_3d_min"][1:].apply(lambda x: add_error(x, error = std))
    predict_df["rolling_3d_max"][1:] = predict_df["rolling_3d_max"][1:].apply(lambda x: add_error(x, error = std))
    return predict_df

@st.cache_data          #cache the dataframe that is not going to change
def th_sps_to_df(path_to_sps):
    '''read theretical S or R sps and return a frame'''
    if os.path.exists(path_to_sps):
        extension=os.path.splitext(os.path.split(path_to_sps)[1])[1]
        #print(extension)
        if extension not in ['.s01','.S01','.r01','.R01']:
            print(f'Unknown file extension {extension}')
            return None
        elif extension in ['.r01','.R01']:
            df_out = pd.read_csv(path_to_sps,
                                skiprows = sps_to_frame_skip(path_to_sps,'R'), sep = r'\s+',
                                names = ['code','Line','Point','idx','Easting','Northing','extras'])
            df_out.drop(columns = ['code','extras'], inplace = True)
            return df_out
        elif extension in ['.s01','.S01']:
            df_out= pd.read_csv(path_to_sps,
                                skiprows = sps_to_frame_skip(path_to_sps,'S'), sep = r'\s+',
                                names = ['code','Line','Point','idx','Easting','Northing','extras'])               
            df_out.drop(columns = ['code','extras'], inplace = True)
            return df_out
    else:
        print(f'No such file {path_to_sps}')
        return None

#a small auxiliary function 
def get_dates_list(days_number, mode = "past"):
    '''return a list of datetime.date() objects
       where first date is today and last is
       days_number ago or in the future
    '''
    if mode not in ["past", "future"]:
        print("Need correct mode: past or future")
        return None
    elif mode == "past":
        dates = [(datetime.utcnow() - timedelta(days = d)).strftime("%Y-%m-%d") for d in range(0,int(days_number))]
    else:
        dates = [(datetime.utcnow() + timedelta(days = d)).strftime("%Y-%m-%d") for d in range(0,int(days_number))]
    return dates


#basic application page config
st.set_page_config(
    page_title=f"Deployment overview",
    page_icon=":flipper:",
    layout="wide",
    menu_items = {'Get Help': "https://docs.streamlit.io",
    "Report a bug": "https://docs.streamlit.io/library/cheatsheet",
    "About":'# Really have *no idea* what that is!'}
    )

" ## :green[Deployment overview]"
(f" ##### :green[App last updated: {datetime.strftime(datetime.utcnow(), '%Y-%m-%d %H:%M')} UTC Julian Day: {datetime.strftime(datetime.utcnow(), '%j')}]")
m_time = datetime.strftime(datetime.fromtimestamp(os.stat(SURVEY_SIDE_CSV).st_mtime,tz = timezone.utc), '%Y-%m-%d %H:%M') #check actual m_time rather then time of last QGIS update
m_jd = datetime.strftime(datetime.fromtimestamp(os.stat(SURVEY_SIDE_CSV).st_mtime,tz = timezone.utc), '%j')
(f" ###### :green[Input data last updated: {m_time} UTC Julian Day: {m_jd}]")
st.markdown("---")
preplot_df = th_sps_to_df(SPS_R_PREPLOT)
deployed_df = read_4dnav_for_receivers(FOURD_NAV)
counts_df = get_deployment_stats_df(deployed_df)
predict_df = predict_with_rolling(counts_df)

dates_list = get_dates_list(2)
days_df = deployed_df.query(f'DeploymentDateStr in {dates_list}')

#checkbox for 4nav dataframe
if st.checkbox(" Show 4dnav raw data"):
    st.text(f"Source: {FOURD_NAV}")
    st.dataframe(deployed_df)

#checkbox for counts dataframe
if st.checkbox(" Show raw data for Deployment Counts"):
    st.text(f"Source: {FOURD_NAV}")
    st.dataframe(counts_df)

if st.checkbox(" Show raw data for Predictions"):
    st.text(f"Source: {FOURD_NAV}")
    st.dataframe(predict_df)

#the plotting block

#overview tab block
#progress map here 

#1.plotly express API
#progress_map_px = px.scatter(deployed_df, x = 'AslaidEasting', y = 'AslaidNorthing', color = "DeploymentROV",symbol="DeploymentROV", title = f"<b>Deployment progress</b>", hover_name = "NodeCode",
#                  hover_data = {'AslaidEasting': False, 'AslaidNorthing': False, 'Line': True, 'Point': True, 'JulianDay':True, "DeploymentDate":True, "DeploymentROV": True}, 
#                  labels= {'JulianDay': 'Julian day','DeploymentDate':'Deployment date',"DeploymentROV":"ROV"},width = 1000, height = 800)
#progress_map_px.add_trace(go.Scatter(x =preplot_df["Easting"], y = preplot_df["Northing"], mode = "markers", marker=dict(color = "gray", opacity = 0.2, size = 4), hoverinfo = "skip", showlegend = False))
#progress_map_px.add_trace(go.Scatter(x =days_df['AslaidEasting'], y = days_df['AslaidNorthing'], mode = "markers", marker=dict(color = "green", symbol = "diamond", opacity = 0.8, size = 8), 
#             hoverinfo = "skip", text = days_df['DeploymentDate'], name = f"Deployed last {len(dates_list)} days"))

#2. plotly go API
progress_map_go = go.Figure()
progress_map_go.add_trace(go.Scatter(x =preplot_df.Easting, y = preplot_df.Northing, mode = "markers", marker=dict(color = "gray", opacity = 0.8, symbol = "pentagon",size = 6), hoverinfo = "skip", name = f"To deploy: {4071 - len(deployed_df)}"))
progress_map_go.add_trace(go.Scatter(x = deployed_df['AslaidEasting'], y = deployed_df['AslaidNorthing'], text = (deployed_df.NodeCode), name = f"Before: {len(deployed_df)-len(days_df)}", mode = "markers", marker = dict(symbol = "pentagon", color = "Gold", size = 6),
                          customdata = np.stack((deployed_df.Line, deployed_df.Point, deployed_df.DeploymentROV,deployed_df.DeploymentDate, deployed_df.JulianDay, deployed_df.Index), axis=-1), legendrank = 900,
                          hovertemplate = '''<b><i>Node info</i></b><br><b>Line: %{customdata[0]} </b><b>Point: %{customdata[1]} Index: %{customdata[5]}</b><br><b>Bumper: %{text}</b><br><b>Deployed by: %{customdata[2]}</b><br><b>Deployed: %{customdata[3]}, JD: %{customdata[4]}</b><extra></extra>'''))

progress_map_go.add_trace(go.Scatter(x =days_df['AslaidEasting'], y = days_df['AslaidNorthing'], mode = "markers", marker=dict(color = "green", symbol = "pentagon", opacity = 0.8, size = 8), legendrank = 800,
                          hoverinfo = "skip", name = f"Last {len(dates_list)} days: {len(days_df)}"))

progress_map_go.update_layout(title = f"<b>Deployed {len(deployed_df)} of 4071 nodes positions</b>",
                              xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", legend_title_text = "<i>Deployed:</i>",
                              font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"),legend={"itemsizing": "constant"}, width = 1000, height = 800)

#3. dive map go API
dive_time_go = go.Figure()
dive_time_go.add_trace(go.Scatter(x =preplot_df.Easting, y = preplot_df.Northing, mode = "markers", marker=dict(color = "gray", opacity = 0.8, symbol = "pentagon", size = 6), hoverinfo = "skip", name = "Not deployed", showlegend = False))
dive_time_go.add_trace(go.Scatter(x = deployed_df.AslaidEasting, y = deployed_df.AslaidNorthing, mode = "markers", showlegend = False, marker = dict(size = 8, color = deployed_df.OnSeabed, symbol = "pentagon",colorscale = "Rainbow", showscale = True),
                       customdata = np.stack((deployed_df.Line, deployed_df.Point, deployed_df.Index, deployed_df.OnSeabed,deployed_df.DeploymentDate, deployed_df.JulianDay,deployed_df.NodeCode), axis=-1),
                       hovertemplate = '''<b><i>Node info</i></b><br><b>Line: %{customdata[0]} </b><b>Point: %{customdata[1]} Index: %{customdata[2]}<br><b>Bumper: %{customdata[6]}</b><br><b>Days on seabed: %{customdata[3]}</b><br><b>Deployed at: %{customdata[4]}, JD: %{customdata[5]}</b><extra></extra>'''))
dive_time_go.update_layout(title = "<b>Seabed time (days)</b>", xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"), width = 1000, height = 800)



#water depths map px only
water_depths =  px.scatter(deployed_df, x = 'AslaidEasting', y = 'AslaidNorthing', color = 'AslaidDepth', color_continuous_scale = px.colors.sequential.Turbo, title = "<b>Water depth at deployment (m)</b>", 
                  hover_data = {'AslaidEasting': False, 'AslaidNorthing': False, 'Line': True, 'Point': True, "AslaidTideOffset": True },  hover_name = "NodeCode",
                  labels = {"AslaidTideOffset":"Tide Offset (m)", "AslaidDepth":"Depth (m)"}, width = 1000, height = 800)
water_depths.add_trace(go.Scatter(x =preplot_df["Easting"], y = preplot_df["Northing"], mode = "markers", marker=dict(color = "gray",opacity = 0.2, size = 4), hoverinfo = "skip", showlegend = False))
water_depths.update_layout(title = "<b>Water depth at deployment (m)</b>", xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", 
                  font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"))

#water depths map go API
water_depths_go = go.Figure()
water_depths_go.add_trace(go.Scatter(x =preplot_df.Easting, y = preplot_df.Northing, mode = "markers",
                         marker=dict(color = "gray", opacity = 0.8, size = 6, symbol = "pentagon"), hoverinfo = "skip", name = "Not deployed", showlegend = False))
water_depths_go.add_trace(go.Scatter(x = deployed_df.AslaidEasting, y = deployed_df.AslaidNorthing, mode = "markers", showlegend = False, marker = dict(size = 8, color = deployed_df.AslaidDepth, symbol = "pentagon",colorscale = "Rainbow", showscale = True),
                        customdata = np.stack((deployed_df.Line, deployed_df.Point, deployed_df.AslaidDepth,deployed_df.DeploymentDate, deployed_df.JulianDay,deployed_df.NodeCode), axis=-1),
                        hovertemplate = '''<b><i>Node info</i></b><br><b>Line: %{customdata[0]}, </b><b>Point: %{customdata[1]}</b><br><b>Bumper: %{customdata[5]}</b><br><b>Deployment Depth: %{customdata[2]}</b><br><b>Deployed at: %{customdata[3]}, JD: %{customdata[4]}</b><extra></extra>'''))

water_depths_go.update_layout(title = "<b>Deployment depth (m)</b>", xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"), width = 1000, height = 800)

#Radial offsets map px only
preplot_deployment_offsets =  px.scatter(deployed_df, x = 'AslaidEasting', y = 'AslaidNorthing', color = 'PreplotToAslaidDistance', color_continuous_scale = px.colors.sequential.Turbo, title = "<b>Preplot to deployment radial offsets (m)</b>", hover_name = "NodeCode",
                  hover_data = {'AslaidEasting': False, 'AslaidNorthing': False, 'Line': True, 'Point': True, 'PreplotToAslaidDistance': True, "PreplotToAslaidAlongTrack": True, "PreplotToAslaidCrossTrack": True}, 
                  labels = {'PreplotToAslaidDistance':'Radial Offset', "PreplotToAslaidAlongTrack":"Inline offset", "PreplotToAslaidCrossTrack":"CrossLine offset"})
preplot_deployment_offsets.add_trace(go.Scatter(x =preplot_df["Easting"], y = preplot_df["Northing"], mode = "markers", marker=dict(color = "gray",opacity = 0.2, size = 4), hoverinfo = "skip", showlegend = False))
preplot_deployment_offsets.update_layout(title = "<b>Radial offsets (m)</b>", xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"),width = 1000, height = 800)

#radial offsets go API
preplot_deployment_offsets_go = go.Figure()
preplot_deployment_offsets_go.add_trace(go.Scatter(x =preplot_df.Easting, y = preplot_df.Northing, mode = "markers", marker=dict(color = "gray", opacity = 0.8, size = 6, symbol = "pentagon"), hoverinfo = "skip", name = "Not deployed", showlegend = False))
preplot_deployment_offsets_go.add_trace(go.Scatter(x = deployed_df.AslaidEasting, y = deployed_df.AslaidNorthing, mode = "markers", showlegend = False, marker = dict(size = 8, color = deployed_df.PreplotToAslaidDistance, symbol = "pentagon", colorscale = "Rainbow", showscale = True),
                        customdata = np.stack((deployed_df.Line, deployed_df.Point, deployed_df.PreplotToAslaidDistance,deployed_df.DeploymentDate, deployed_df.JulianDay,deployed_df.NodeCode), axis=-1),
                        hovertemplate = '''<b><i>Node info</i></b><br><b>Line: %{customdata[0]}, </b><b>Point: %{customdata[1]}</b><br><b>Bumper: %{customdata[5]}</b><br><b>Radial offset: %{customdata[2]} m</b><br><b>Deployed at: %{customdata[3]}, JD: %{customdata[4]}</b><extra></extra>'''))
preplot_deployment_offsets_go.update_layout(title = "<b>Preplot to deployment position distance (m)</b>", xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", 
                        font = dict(family = "Courier New, monospace", size=14, color="RoyalBlue"), width = 1000, height = 800)

#Counts tab plots

##1.Daily deployment plotly express API
#deployed_daily_px = px.bar(counts_df, x = 'Date', y = 'NodesDeployed', title = "<b>Nodes deployed by JD </b>", hover_data = {'JulianDay': True, 'Date': True }, width = 1000, height = 800)
#deployed_daily_px.add_trace(go.Scatter(x = counts_df["Date"], y = counts_df["XLX19"], mode = "lines+markers", name = "XLX19", text = counts_df["XLX19"]/counts_df["TotalDeployed"]*100, 
#                    hovertemplate = '''<b><i>Production</b></i><br><b>Date: </b>%{x}<br><b>Nodes deployed: </b>%{y}<br><b>Total/daily: </b>%{text:.2f}%<extra></extra>''', showlegend = False))
#deployed_daily_px.add_trace(go.Scatter(x = counts_df["Date"], y = counts_df["UHD64"], mode = "lines+markers", text = counts_df["UHD64"]/counts_df["TotalDeployed"]*100, name = "UHD64", 
#                    hovertemplate = '''<b><i>Production</b></i><br><b>Date: </b>%{x}<br><b>Nodes deployed: </b>%{y}<br><b>Total/daily: </b>%{text:.2f}%<extra></extra>''', showlegend = False))
## annotation
#deployed_daily_px.add_shape(type = "line", line_color = "green", line_width = 3, opacity = 0.5, x0=counts_df["Date"].min(), x1=counts_df["Date"].max(), y0 = 100, y1 = 100)
#deployed_daily_px.add_annotation(text = "<b>Daily target (100 nodes)</b>" , x = datetime(2023, 2, 23), y = 102, arrowhead = 3, arrowcolor = "green", showarrow = True)
#deployed_daily_px.update_layout(hovermode = 'x unified')

#1.Daily deployment bar chart using the go API

deployed_daily_go = go.Figure()
deployed_daily_go.add_trace(go.Bar(x = counts_df["Date"], y = counts_df["NodesDeployed"], name = "<b>Total</b>", 
                hovertemplate = '''<br><b>Date: </b>%{x}<br><b>Daily production: %{y} </b><br>'''))

deployed_daily_go.add_trace(go.Scatter(x = counts_df["Date"], y = counts_df["XLX19"], mode = "lines+markers", name = "<b>XLX19</b>", text = counts_df.XLX19_diff, 
                    hovertemplate = '''<br><b>XLX19</b><br><b>Nodes deployed: </b>%{y}<br><b>Daily change: </b>%{text:.2f}<extra></extra>'''))
deployed_daily_go.add_trace(go.Scatter(x = counts_df["Date"], y = counts_df["UHD64"], mode = "lines+markers", text = counts_df.UHD64_diff, name = "<b><i>UHD64</i></b>",
                    hovertemplate = '''<br><b>UHD64</b><br><b>Nodes deployed: </b>%{y}<br><b>Daily change: </b>%{text:.2f}<extra></extra>'''))

deployed_daily_go.add_shape(type = "line", line_color = "green", line_width = 3, opacity = 0.5, x0 = counts_df["Date"].min(), x1=counts_df["Date"].max(), y0 = 100, y1 = 100)
deployed_daily_go.add_annotation(text = "<b>Daily target (100 nodes)</b>" , x = datetime(2023, 3, 1), y = 102, arrowhead = 3, arrowcolor = "green", showarrow = True)

deployed_daily_go.update_layout(hovermode = 'x unified', width = 1000, height = 800, title = "<b>Daily deployment</b>", hoverdistance = 300,
                                xaxis_title = "<b><i>Date</i></b>", yaxis_title = "<b><i>Production</i></b>",
                                font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"))

#2.Cumulative deployment

# Cumulative sum graph object API
cumsum_deployed = go.Figure()
cumsum_deployed.add_trace(go.Scatter(x = counts_df["Date"], y = counts_df["TotalDeployed"], mode = "lines+markers", text = counts_df["IncreaseBy"], name = "<b><i>Total</i></b>", 
                hovertemplate = '''<br><b>Date: </b>%{x}<br><b>Total deployed: %{y} (+%{text}%)</b><br>'''))
cumsum_deployed.add_trace(go.Scatter(x = counts_df["Date"], y = counts_df["TotalByXLX19"], mode = "lines+markers", name = "<b>XLX19</b>", 
                hovertemplate = '''<br><b>Date: </b>%{x}<br><b>Total deployed: <i>%{y}</i></b><br>'''))
cumsum_deployed.add_trace(go.Scatter(x = counts_df["Date"], y = counts_df["TotalByUHD64"], mode= 'lines+markers', name = "<b>UHD64</b>", 
                hovertemplate = '''<br><b>Date: </b>%{x}<br><b>Total deployed: <i>%{y}</i></b><br>'''))

cumsum_deployed.update_layout(hovermode = 'x unified', width = 1000, height = 800, title = "<b>Cumulative deployment sum</b>",
                             xaxis_title = "<b><i>Date</i></b>", hoverdistance = 500,
                             yaxis_title = "<b><i>Production</i></b>", font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"))

#some statistics and predictive plots
#statitical plots go API
stats_plot = go.Figure()
stats_plot.add_trace(go.Scatter(x = counts_df["Date"], y = counts_df["rolling_3d_sum"], mode = "lines+markers", name = "<b><i>Sum</i></b>", marker = dict(color = "Crimson"),
                hovertemplate = '''<br><b>Rolling sum: %{y}</b><extra></extra>'''))
stats_plot.add_trace(go.Scatter(x = counts_df["Date"], y = counts_df["rolling_3d_avg"], mode = "lines+markers", name = "<b><i>Avg</i></b>", marker = dict(color = "SeaGreen"),
                hovertemplate = '''<br><b>Rolling avg: %{y}</b><extra></extra>'''))
stats_plot.add_trace(go.Scatter(x = counts_df["Date"], y = counts_df["NodesDeployed"], mode = "lines+markers", name = "<b>Deployed</b>", marker = dict(color = "LightBlue"),
                hovertemplate = '''<br><b>Deployed: %{y}</b><extra></extra>'''))
stats_plot.update_layout(hovermode = 'x unified', width = 1000, height = 800, title = "<b>Deployment statistics (3 days window)</b>",
                         xaxis_title = "<b><i>Date</i></b>", hoverdistance = 500,
                         yaxis_title = "<b><i>Counts</i></b>", legend_title_text ="<b><i>Rolling:</i></b>",
                         font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"))

#Vanga predictions go API
prediction_plot = go.Figure()
prediction_plot.add_trace(go.Scatter(x = predict_df["Date"], y = predict_df["rolling_3d_min"], mode = "lines+markers",
                marker = dict(color = "LightBlue"), name = "<b><i>Min</i></b>", 
                hovertemplate = '''<br><b>Predicted min: %{y}</b><extra></extra>'''))
prediction_plot.add_trace(go.Scatter(x = predict_df["Date"], y = predict_df["rolling_3d_avg"], mode = "lines+markers",
                marker = dict(color = "SeaGreen"), name = "<b><i>Avg</i></b>", 
                hovertemplate = '''<br><b>Predicted avg: %{y}</b><extra></extra>'''))
prediction_plot.add_trace(go.Scatter(x = predict_df["Date"], y = predict_df["rolling_3d_max"], mode = "lines+markers",
                marker = dict(color = "Crimson"), name = "<b><i>Max</i></b>", 
                hovertemplate = '''<br><b>Predicted max: %{y}</b><extra></extra>'''))

prediction_plot.update_layout(hovermode = 'x unified', width = 1000, height = 800, title = "<b>Predicted productions scenarios</b>",
                             xaxis_title = "<b><i>Date</i></b>", hoverdistance = 500,
                             yaxis_title = "<b><i>Predicted Counts</i></b>", legend_title_text = "<b><i>Rolling:</i></b>",
                             font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"))

#Attributes tab 
#tabs section

overview_tab, counts_tab, attributes_tab = st.tabs(["**Deployment overview**", "**Deployment counts**","**Line attributes**"])

with overview_tab:
    " ## :green[Deployment overview]"
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(progress_map_go, theme = None, use_container_width = False)
        st.plotly_chart(water_depths_go, theme = None, use_container_width = False)
    with col2:
        st.plotly_chart(dive_time_go, theme = None, use_container_width = False)
        
        st.plotly_chart(preplot_deployment_offsets_go, theme = None, use_container_width = False)
        
with counts_tab:
    " ## :green[Production overview]"
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(deployed_daily_go, theme = None, use_container_width = False)
        st.plotly_chart(stats_plot, theme = None, use_container_width = False)
    with col2:
        st.plotly_chart(cumsum_deployed, theme = None, use_container_width = False)
        st.plotly_chart(prediction_plot, theme = None, use_container_width = False)

with attributes_tab:
    " ## :green[Line by Line attributes]"
    lines_list = deployed_df.Line.unique()
    line_to_choose = st.selectbox("", lines_list)
    line_df = deployed_df.query(f'Line == {line_to_choose}')
    th_line_df = preplot_df.query(f'Line == {line_to_choose}')
    #
    deployed = len(line_df)
    to_deploy = len(th_line_df)
    ratio = round(deployed/to_deploy*100)
    ttl = f"Nodes deployed: {deployed} of {to_deploy} ({ratio}%)"
    #plot here
    col1, col2 = st.columns(2)
    with col1:
        # create attributes sublots here
        attr_plot_go = make_subplots(rows = 2, cols = 2, start_cell="top-left", 
                       subplot_titles = ("Deployment time", "Deployment Depth (m)", "Radial offset (m)", "Tide (m)"))
        attr_plot_go.add_trace(go.Scatter(x = line_df.Point, y = line_df.DeploymentDateTime, mode = "lines+markers", 
                     marker = dict(color = "RebeccaPurple"), name = "<b><i>Time vs point</i></b>", showlegend = False,
                     hovertemplate = '''<br><b>Point: %{x}<br>Deployment time: %{y}</b><extra></extra>'''),row = 1, col =1)
        attr_plot_go.add_trace(go.Scatter(x = line_df.Point, y = line_df.AslaidDepth*-1, mode = "lines+markers",
                     marker = dict(color = "Maroon"), name = "<b><i>Depth vs Point (m)</i></b>", showlegend = False,
                     hovertemplate = '''<br><b>Point: %{x}<br>Depth: %{y} m</b><extra></extra>'''), row = 1, col = 2)
        attr_plot_go.add_trace(go.Scatter(x = line_df.Point, y = line_df.PreplotToAslaidDistance,
                     mode = "lines+markers", name = "<b><i>Offset vs point (m)</i></b>", showlegend = False,
                     customdata = np.stack((line_df.PreplotToAslaidAlongTrack, line_df.PreplotToAslaidCrossTrack),axis = -1),
                     hovertemplate = '''<br><b>Point: %{x}<br><i>Offsets:<br>Radial: %{y} m<br>Xline: %{customdata[1]} m<br>Crossline: %{customdata[0]} m</b><extra></extra>'''), row = 2, col = 1)
        attr_plot_go.add_trace(go.Scatter(x = line_df.Point, y = line_df.AslaidTideOffset, mode = "lines+markers", marker = dict(color = "SlateGray", size = 4),
                     name = "<b><i>Tide vs point</i></b>", showlegend = False,
                     hovertemplate = '''<br><b>Point: %{x}<br>Tide: %{y} m</b><extra></extra>'''), row = 2, col = 2)

        attr_plot_go.update_layout(width = 1000, height = 800, title = f"<b>Line {line_to_choose} attributes</b>", font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"))

        # display plot
        st.plotly_chart(attr_plot_go, theme = None, use_container_width = False)
    
    with col2:
        # plot the line position relative to preplot
        progress_map_go = go.Figure()
        progress_map_go.add_trace(go.Scatter(x =preplot_df.Easting, y = preplot_df.Northing, mode = "markers", marker=dict(color = "silver", symbol = "pentagon", opacity = 0.6, size = 6), hoverinfo = "skip", name = "Other"))
        progress_map_go.add_trace(go.Scatter(x = line_df.AslaidEasting, y = line_df.AslaidNorthing, text = line_df.NodeCode, name = f"{line_to_choose}", mode = "markers", marker = dict(symbol = "pentagon", color = "SpringGreen", size = 8),
                       customdata = np.stack((line_df.Line, line_df.Point, line_df.DeploymentROV,line_df.DeploymentDate, line_df.JulianDay, line_df.Index), axis=-1), legendrank = 900,
                       hovertemplate = '''<b><i>Node info</i></b><br><b>Line: %{customdata[0]} </b><b>Point: %{customdata[1]} Index: %{customdata[5]}</b><br><b>Bumper: %{text}</b><br><b>Deployed by: %{customdata[2]}</b><br><b>Deployed at: %{customdata[3]}, JD: %{customdata[4]}</b><extra></extra>'''))
        progress_map_go.update_layout(title = f"<b>{ttl}</b>", xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", 
                       font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"), legend_title_text = "<i>Lines:</i>", legend={"itemsizing": "constant"}, width = 1000, height = 800)
        
        # display plot
        st.plotly_chart(progress_map_go, theme = None, use_container_width = False)
