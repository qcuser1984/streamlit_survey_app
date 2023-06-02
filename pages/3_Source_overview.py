#standard library imports
import os
from datetime import datetime, timedelta
from math import dist

import warnings
warnings.filterwarnings('ignore')


#fancy modules imports
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots



SPS_S_PREPLOT = r"Q:\06-ARAM\nav\preplot.s01"
ALL_CLEAN_S = r"Q:\06-ARAM\nav\Postplot_S\All_Seq_Clean.s01"
ALL_RAW_S = r"Q:\06-ARAM\nav\Postplot_S\All_Seq_Raw.s01"
TO_ACQUIRE = 538381

def small_function(ist_in):
    if ist_in > 25.0:
        return (12.0)
    return ist_in
#some custom functions here

#theo sps first
@st.cache_data          #cache the dataframe that is not going to change
def th_sps_to_df(path_to_sps):
    '''read theretical S or R sps
       return dataframe or None'''
    if os.path.exists(path_to_sps):
        extension=os.path.splitext(os.path.split(path_to_sps)[1])[1]
        #print(extension)
        if extension not in ['.s01','.S01','.r01','.R01']:
            print(f'Unknown file extension {extension}')
            return None
        else:
            if extension in ['.r01','.R01']:
                df_out = pd.read_csv(path_to_sps,
                                    skiprows = sps_to_frame_skip(path_to_sps,'R'), sep = '\s+',
                                    names = ['code','Line','Point','idx','Easting','Northing','extras'])
                df_out.drop(columns = ['code','extras'], inplace = True)
                return df_out
            elif extension in ['.s01','.S01']:
                df_out= pd.read_csv(path_to_sps,
                                    skiprows = sps_to_frame_skip(path_to_sps,'S'), sep = '\s+',
                                    names = ['code','Line','Point','idx',
                                            'Easting_th','Northing_th','extras'])
                df_out.drop(columns = ['code','extras'], inplace = True)
                return df_out
    else:
        print(f'No such file {path_to_sps}')
        return None

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

def source_sps_to_df(path_to_sps):
    '''return source sps as dataframe'''
    if os.path.exists(path_to_sps) and os.stat(path_to_sps).st_size > 0:
        rows_to_skip= sps_to_frame_skip(path_to_sps,'S') 
        try:
            df_out=pd.read_fwf(path_to_sps,
            skiprows = rows_to_skip,
            colspecs = [(0,1),(2,8),(12,18),(23,24),(30,34),(40,46),(47,55),(56,65),
                        (65,71),(71,74),(74,80),(74,87),(81,87),(88,92),(92,95),(95,97),
                        (97,98),(98,99),(99,100),(100,101),(101,102),(103,108)],
            names = ['code','Line','Point','Index','GunDepth','WaterDepth',
                    'Easting','Northing',
                    'Tide','JulianDay','SpTime','sp_time_ms',
                    'ms_fraction','Sequence','Azimuth','SpYear',
                    'DepthEdit','TimingEdit','PressureEdit',
                    'RepeatabilityFlag','PositioningFlag','Dither']
                    )
            #update df here as well
            df_out['str_time'] = df_out['SpTime'].astype(str)
            df_out['str_fraction'] = df_out['ms_fraction'].astype(str)
            df_out['str_time'] = df_out['str_time'].apply(lambda x: x.zfill(6))
            df_out['str_fraction'] = df_out['str_fraction'].apply(lambda x: x.zfill(6))
            df_out['str_jd'] = df_out['JulianDay'].astype(str)
            df_out['str_jd'] = df_out['str_jd'].apply(lambda x: x.zfill(3))
            df_out["str_datetime"] = df_out["SpYear"].astype(str) + df_out["str_jd"] + df_out["str_time"] + "." + df_out["str_fraction"]
            df_out["SpDateTime"] = df_out["str_datetime"].apply(lambda x: datetime.strptime(x, "%y%j%H%M%S.%f"))
            df_out["SpDateTime"] = pd.to_datetime(df_out.SpDateTime)
            df_out.drop(columns = ['str_time', 'str_jd', 'str_datetime','str_fraction','SpTime','sp_time_ms','ms_fraction'], inplace = True)
            return df_out
        except Exception as exc:
            print(f"Couldn't produce the data frame from {path_to_sps} d/t {exc}")
            return None
    else:
        print(f"File {os.path.split(path_to_sps)[1]} doesn't exist or empty")
        return None

def get_source_stats_df(df_in):
    acquisition_start = pd.datetime(2023,3,10)
    project_timeline = pd.date_range(acquisition_start,datetime.utcnow())
    timeline_df = pd.DataFrame(project_timeline, columns = ["Date"])
    timeline_df.Date = timeline_df.Date.apply(lambda x : x.date())
    timeline_df.Date = pd.to_datetime(timeline_df.Date) ### <<< = really important!
    timeline_df["JulianDay"] = timeline_df['Date'].apply(lambda x: int(datetime.strftime(x, "%j")))
    counts_df = df_in.groupby("JulianDay").agg({"Point" : 'count'})
    counts_df["PointsAcquired"] = counts_df.Point
    counts_df.drop(columns = ["Point"], inplace = True)
    prod_df = pd.merge(timeline_df, counts_df, how = "outer", on = "JulianDay")
    prod_df.fillna(0, inplace=True)
    prod_df["TotalAcquired"] = (prod_df.PointsAcquired.cumsum()).astype(int)
    prod_df["AcquisitionComplete"] = round((prod_df.TotalAcquired/TO_ACQUIRE)*100,2)
    prod_df["IncreaseBy"] = round(prod_df.AcquisitionComplete.diff(),2)
    
    prod_df["rolling_3d_sum"] = prod_df.rolling(window = '3d', on = "Date").PointsAcquired.sum()
    prod_df["rolling_3d_avg"] = round(prod_df.rolling(window = '3d', on = "Date").PointsAcquired.mean())
    prod_df["rolling_3d_min"] = round(prod_df.rolling(window = '3d', on = "Date").PointsAcquired.min(),2)
    prod_df["rolling_3d_max"] = round(prod_df.rolling(window = '3d', on = "Date").PointsAcquired.max(),2)

    prod_df.fillna(0.0,inplace = True, axis = 1)
    return prod_df

#basic application page config
st.set_page_config(
    page_title=f"Source overview",
    page_icon=":flipper:",
    layout="wide",
    menu_items = {'Get Help': "https://docs.streamlit.io",
    "Report a bug": "https://docs.streamlit.io/library/cheatsheet",
    "About":'# Really have *no idea* what that is!'}
    )

" # :green[Source overview]"
(f" ##### :green[Application last updated {datetime.strftime(datetime.utcnow(), '%Y-%m-%d %H:%M')} UTC]")

preplot_df = th_sps_to_df(SPS_S_PREPLOT)
all_clean_df = source_sps_to_df(ALL_CLEAN_S)
all_raw_df = source_sps_to_df(ALL_RAW_S)

prod_df_clean = get_source_stats_df(all_clean_df)
prod_df_raw = get_source_stats_df(all_raw_df)


if st.checkbox("Show raw data for Theoretical"): #<= Too much resources 
    st.text(f"Source: {SPS_S_PREPLOT}")
    st.dataframe(preplot_df)
    #st.dataframe(receivers_df)

if st.checkbox("Show raw data for Source counts"):
    st.text(f"Source file: {ALL_CLEAN_S}") #< = All_clean_S here
    st.dataframe(all_clean_df)
    st.text(f"Source file: {ALL_RAW_S}")    #<= All_raw_S here
    st.dataframe(all_raw_df)

if st.checkbox("Show raw for production stats"):
    st.text(f"Source file: {ALL_RAW_S}")
    st.dataframe(prod_df_raw)
    st.text(f"Source file: {ALL_CLEAN_S}")
    st.dataframe(prod_df_clean)

#ploting block

#Overview tab
#1.progrees map go API

#progress_map_go = go.Figure()
#progress_map_go.add_trace(go.Scatter(x =preplot_df.Easting, y = preplot_df.Northing, mode = "markers", marker=dict(color = "gray", opacity = 0.8, size = 4), hoverinfo = "skip", name = "Preplot"))
#
#progress_map_go.update_layout(title = "<b>Source progress</b>", xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", 
#                font = dict(family="Courier New, monospace", size=14, color="SeaGreen"), width = 1000, height = 800)

progress_map_go = go.Figure()
progress_map_go.add_trace(go.Scatter(x=[509209.3,505946.7, 518677.4, 528549.9, 548760.8, 548549.5, 541422.7, 526233.2, 509209.3], 
                           y=[7150151.7, 7161421.1, 7183438.5, 7185727.2, 7174061.9, 7156351.5, 7144025.4,7140321.7, 7150151.7], 
                           line = dict(color = "gray"), fill="toself", hoverinfo="skip", name = "Source polygon", showlegend = False))
progress_map_go.add_trace(go.Scatter(x = all_clean_df.Easting, y = all_clean_df.Northing, showlegend = False, mode = "markers",
                          marker=dict(size = 2, symbol = "pentagon", color = "Lime"),
                          customdata = np.stack((all_clean_df.Line, all_clean_df.Point, all_clean_df.Sequence, all_clean_df.JulianDay),axis = 1),
                          hovertemplate = '''<b>Point info<br>Line: %{customdata[0]}<br>Point: %{customdata[1]}<br>Sequence: %{customdata[2]}<br>Acquired on JD: %{customdata[3]}</b><extra></extra>'''))
                           
progress_map_go.update_layout(title = "<b>Source progress</b>", xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", 
                font = dict(family="Courier New, monospace", size=14, color="SeaGreen"), width = 1000, height = 800)

#attributes map go API

attrs_map_go = go.Figure()
attrs_map_go.add_trace(go.Scatter(x=[509209.3,505946.7, 518677.4, 528549.9, 548760.8, 548549.5, 541422.7, 526233.2, 509209.3], 
                           y=[7150151.7, 7161421.1, 7183438.5, 7185727.2, 7174061.9, 7156351.5, 7144025.4,7140321.7, 7150151.7], 
                           line = dict(color = "gray"), fill="toself", hoverinfo="skip", showlegend = False))

attrs_map_go.add_trace(go.Scatter(x = all_clean_df.Easting, y = all_clean_df.Northing, mode = "markers",
                marker=dict(size = 3, symbol = "pentagon", color = all_clean_df.WaterDepth, colorscale = "rainbow", showscale = True), 
                legendrank = 900, customdata = np.stack((all_clean_df.Line, all_clean_df.Point, all_clean_df.WaterDepth, all_clean_df.GunDepth,),axis = 1), showlegend = False, 
                hovertemplate = '''<b>Point info<br>Line: %{customdata[0]}<br>Point: %{customdata[1]}<br>Water depth: %{customdata[2]} m<br>Gun depth: %{customdata[3]} m</b><extra></extra>'''))
attrs_map_go.update_layout(title = "<b>Water depth (m)</b>", xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", 
                font = dict(family="Courier New, monospace", size=14, color="SeaGreen"), width = 1000, height = 800)


#Counts tab
#1.Counts bar chart go API
acquired_daily_go = go.Figure()
acquired_daily_go.add_trace(go.Bar(x = prod_df_raw.Date, y = prod_df_raw.PointsAcquired, name = "<b>Raw counts</b>",
                  hovertemplate = '''<br><b>Daily production: %{y} </b><br>'''))
acquired_daily_go.add_trace(go.Bar(x = prod_df_clean.Date, y = prod_df_clean.PointsAcquired, name = "<b>Clean counts</b>",
                  hovertemplate = '''<br><b>Daily production: %{y} </b><br>'''))


acquired_daily_go.add_shape(type = "line", line_color = "green", line_width = 3, opacity = 0.6, x0=prod_df_raw.Date.min(), x1=prod_df_raw.Date.max(), y0 = 6500, y1 = 6500)
acquired_daily_go.add_annotation(text = "<b>Daily production target<br>(6500 shots per day)</b>" , x = datetime(2023, 3, 12), y = 6600, arrowhead = 4, arrowcolor = "green", showarrow = True)

acquired_daily_go.update_layout(hovermode = 'x unified', width = 1000, height = 800, title = "<b>Daily production</b>", hoverdistance = 300,
                                xaxis_title = "<b><i>Date</i></b>", yaxis_title = "<b><i>Production</i></b>", 
                                font = dict(family="Courier New, monospace", size = 14, color="SeaGreen"))


#2.Cumulative sum
cumsum_acquired_go = go.Figure()
cumsum_acquired_go.add_trace(go.Scatter(x = prod_df_raw.Date, y = prod_df_raw.TotalAcquired, mode = "lines+markers", text = prod_df_raw.IncreaseBy, name = "<b><i>Raw acquired</i></b>",
                  marker = dict(color = "Crimson", symbol = "pentagon"),hovertemplate = '''<br><b>Acquired: %{y} (+%{text}%)</b><br>'''))
cumsum_acquired_go.add_trace(go.Scatter(x = prod_df_clean.Date, y = prod_df_clean.TotalAcquired, mode = "lines+markers", text = prod_df_clean.IncreaseBy, name = "<b><i>Clean acquired</i></b>",
                  marker = dict(color = "LimeGreen", symbol = "pentagon"), hovertemplate = '''<br><b>Chargeble: %{y} (+%{text}%)</b><br>'''))

cumsum_acquired_go.update_layout(hovermode = 'x unified', width = 1000, height = 800, title = "<b>Cumulative production</b>", hoverdistance = 300,
                                xaxis_title = "<b><i>Date</i></b>", yaxis_title = "<b><i>Production</i></b>", 
                                font = dict(family="Courier New, monospace", size = 14, color = "SeaGreen"))

#3. days statistics 
#statitical plots go API
stats_plot_go = go.Figure()
stats_plot_go.add_trace(go.Scatter(x = prod_df_clean.Date, y = prod_df_clean.rolling_3d_sum, mode = "lines+markers", name = "<b><i>Rolling sum</i></b>", marker = dict(color = "Crimson", symbol = "pentagon"),
                hovertemplate = '''<br><b>Rolling sum: %{y}</b><extra></extra>'''))
stats_plot_go.add_trace(go.Scatter(x = prod_df_clean.Date, y = prod_df_clean.rolling_3d_avg, mode = "lines+markers", name = "<b><i>Rolling avg</i></b>", marker = dict(color = "DeepSkyBlue"),
                hovertemplate = '''<br><b>Rolling avg: %{y}</b><extra></extra>'''))
stats_plot_go.add_trace(go.Scatter(x = prod_df_clean.Date, y = prod_df_clean.PointsAcquired, mode = "lines+markers", name = "<b><i>Acquisition count</i></b>", marker = dict(color = "LimeGreen"),
                hovertemplate = '''<br><b>Acquired: %{y}</b><extra></extra>'''))
stats_plot_go.update_layout(hovermode = 'x unified', width = 1000, height = 800, title = "<b>Acquistion statistics (3 days window)</b>", xaxis_title = "<b><i>Date</i></b>", hoverdistance = 500,
                             yaxis_title = "<b><i>Counts</i></b>", font = dict(family="Courier New, monospace", size=14, color="SeaGreen"))



#overview_tab, counts_tab, line_attrs = st.tabs(["**Source production Overview**", "**Source Production Counts**","**Line attributes**"])

#with overview_tab:
#    " ## Current source progress"
#    col1, col2 = st.columns(2)
#    with col1:
#        #st.plotly_chart(progress_map_go, theme = None, use_container_width = False)
#        st.text("Some attributes scatter here")
#    with col2:
#        #st.plotly_chart(attrs_map_go, theme = None, use_container_width = False)
#        st.text("Another attributes scatter here")


counts_tab, line_attrs = st.tabs(["**Source Production Counts**","**Line attributes**"])
with counts_tab:
    " # Production values"
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(acquired_daily_go, theme = None, use_container_width = False)
        st.plotly_chart(stats_plot_go, theme = None, use_container_width = False)
       #st.text("Bar chart here")
    with col2:
        st.plotly_chart(cumsum_acquired_go, theme = None, use_container_width = False)
       #st.text("Line comulative chart here")
with line_attrs:
    " ## :green[Line attributes]"
    lines = list(all_clean_df.Line.unique()) #not sorted list, same lines order as in All_clean_file
    line_to_choose = st.selectbox("", lines)
    line_df = all_clean_df.query(f'Line == {line_to_choose}')
    th_line_df = preplot_df.query(f'Line == {line_to_choose}')
    complete = round((len(line_df)/len(th_line_df))*100,2)
    line_df["ist"] = line_df.SpDateTime.diff()
    line_df.ist.fillna(timedelta(seconds = 10.000), inplace = True)
    line_df.ist = line_df.ist.apply(lambda x: x.total_seconds())
    line_df.ist = line_df.ist.apply(lambda x: small_function(x))
    line_df.sort_values(by = ['Point'], inplace = True)
    line_df = line_df.merge(th_line_df, on = 'Point', how = 'left')
    
    prod_coords = list(zip(list(line_df['Easting']),list(line_df['Northing'])))
    theo_coords = list(zip(list(line_df['Easting_th']),list(line_df['Northing_th'])))
    dist_list = [round(dist(prod_coords[i],theo_coords[i]),3) for i in range(len(prod_coords))]
    line_df['DistanceToPreplot'] = dist_list
    line_df.drop(columns = ['Line_y','idx'], inplace = True)
    
    shot, to_shoot = len(line_df), len(th_line_df)
    ratio = round((shot/to_shoot)*100)


    col1, col2 = st.columns(2)
    with col1:
        attr_plot_go = make_subplots(rows=2, cols=2, start_cell="top-left", subplot_titles = ("Water depth (m)", "Mean gun depth (m)", "Intershot Time (sec)", "Radial offset (m)"))
        attr_plot_go.add_trace(go.Scatter( x = line_df.Point, y = line_df.WaterDepth*-1, mode = "lines", marker = dict(color = "Teal"), name = "<i>Water depth (m)</i>",
                    showlegend = False, hovertemplate = '''<br><b>Point: %{x}<br>Water depth: %{y}m</b><extra></extra>'''),row = 1, col =1)
        attr_plot_go.add_trace(go.Scatter(x = line_df.Point, y = line_df.GunDepth, mode = "lines", line = dict(color = "MediumSlateBlue", width = 0.5), name = "<b><i>Gun Depth (m)</i></b>", showlegend = False,
                    hovertemplate = '''<br><b>Point: %{x}<br>Gun_Depth: %{y} m</b><extra></extra>'''), row = 1, col = 2)
        attr_plot_go.add_trace(go.Scatter(x = line_df.Point, y = line_df.ist, mode = "lines", line = dict(color = "Crimson", width = 0.5), name = "<b><i>Gun Depth (m)</i></b>", showlegend = False,
                    hovertemplate = '''<br><b>Point: %{x}<br>Intershotime: %{y} sec</b><extra></extra>'''), row = 2, col = 1)
        
        attr_plot_go.add_trace(go.Scatter(x = line_df.Point, y = line_df.DistanceToPreplot, mode = "lines", line = dict(color = "Magenta", width = 0.5), name = "<b><i>Radial offset (m)</i></b>", showlegend = False,
                    hovertemplate = '''<br><b>Point: %{x}<br>RadialOffset: %{y} m</b><extra></extra>'''), row = 2, col = 2)
        attr_plot_go.add_trace(go.Scatter(x = line_df.Point, y = [10 for i in range(len(line_df))], mode = "lines", line = dict(color = "green", width = 0.5), name = "<b><i>Radial offset (m)</i></b>", showlegend = False,
                    hovertemplate = '''<br><b>Limit: %{y} m</b><extra></extra>'''), row = 2, col = 2)
        attr_plot_go.update_layout(width = 1000, height = 800, title = f"<b>Line {line_to_choose} attributes</b>", font = dict(family="Courier New, monospace", size=14, color="RoyalBlue"))

        st.plotly_chart(attr_plot_go, theme = None, use_container_width = False)

    with col2:
        position_map_go = go.Figure()
        position_map_go.add_trace(go.Scatter(x=[509209.3,505946.7, 518677.4, 528549.9, 548760.8, 548549.5, 541422.7, 526233.2, 509209.3], 
                           y=[7150151.7, 7161421.1, 7183438.5, 7185727.2, 7174061.9, 7156351.5, 7144025.4,7140321.7, 7150151.7], 
                           line = dict(color = "gray"), fill="toself", hoverinfo="skip", name = "Source polygon", showlegend = False))
        position_map_go.add_trace(go.Scatter(x = line_df.Easting, y = line_df.Northing, mode = "markers", marker = dict (symbol = "pentagon", color = "Lime"), name = f"{line_to_choose}",
                          customdata = np.stack((line_df.Line_x, line_df.Point, line_df.Sequence, line_df.JulianDay),axis = 1),
                          hovertemplate = '''<b>Point info<br>Line: %{customdata[0]}<br>Point: %{customdata[1]}<br>Sequence: %{customdata[2]}<br>Acquired on JD: %{customdata[3]}</b><extra></extra>'''))

        position_map_go.update_layout(title = f"<b>Line {line_to_choose} is {complete}% complete</b>", xaxis_title = "<b><i>Easting (m)</i></b>", yaxis_title = "<b><i>Northing (m)</i></b>", 
                          font = dict(family="Courier New, monospace", size = 14, color = "SeaGreen"), width = 1000, height = 800)

        st.plotly_chart(position_map_go, theme = None, use_container_width = False)
        